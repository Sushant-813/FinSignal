"""Integration tests for expired PENDING recovery and generation token lease fencing."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from finsignal.ai.models import AISummary
from finsignal.ai.repository import AISummaryRepository
from finsignal.ai.schemas import AISummaryGenerateRequest
from finsignal.ai.service import AISummaryService
from finsignal.audit.models import AuditEvent
from finsignal.core.config import Settings
from finsignal.users.models import User


def _seed_recovery_fixtures(sync_url: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Seed user, account, transaction, and investigation; return (admin_id, tx_id, inv_id)."""
    engine = create_engine(sync_url)
    admin_id = uuid.uuid4()
    account_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    inv_id = uuid.uuid4()

    with engine.begin() as conn:
        admin_email = f"admin_{admin_id.hex[:6]}@example.com"
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, is_active, created_at, updated_at) "
                "VALUES (:id, :email, 'hash', 'ADMIN', true, NOW(), NOW())"
            ),
            {"id": admin_id, "email": admin_email},
        )
        conn.execute(
            text(
                "INSERT INTO accounts (id, source_namespace, external_account_id, account_type, status, created_at, updated_at) "
                "VALUES (:aid, 'SYNTHETIC', :ext_aid, 'CHECKING', 'ACTIVE', NOW(), NOW())"
            ),
            {"aid": account_id, "ext_aid": f"ACC_{account_id.hex[:8]}"},
        )
        conn.execute(
            text(
                "INSERT INTO transactions (id, source_namespace, external_transaction_id, account_id, occurred_at, amount, currency, transaction_type, direction, created_at) "
                "VALUES (:tid, 'SYNTHETIC', :ext_tid, :aid, NOW(), 500.00, 'USD', 'PURCHASE', 'DEBIT', NOW())"
            ),
            {"tid": tx_id, "aid": account_id, "ext_tid": f"TX_{tx_id.hex[:8]}"},
        )
        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
                "VALUES (:iid, :uid, 'UNDER_REVIEW', 'HIGH', NOW(), NOW())"
            ),
            {"iid": inv_id, "uid": admin_id},
        )
        conn.execute(
            text(
                "INSERT INTO investigation_transactions (investigation_id, transaction_id, relationship_type, created_at) "
                "VALUES (:iid, :tid, 'PRIMARY', NOW())"
            ),
            {"iid": inv_id, "tid": tx_id},
        )
    engine.dispose()
    return admin_id, tx_id, inv_id


@pytest.mark.asyncio
async def test_expired_pending_recovery_and_new_generation(
    disposable_db: dict[str, Any],
) -> None:
    """An expired PENDING record is transitioned to FAILED and a new generation succeeds."""
    sync_url = str(disposable_db["sync_url"])
    admin_id, tx_id, inv_id = _seed_recovery_fixtures(sync_url)

    # Insert orphaned expired PENDING record (generated_at = 120 seconds ago)
    expired_summary_id = uuid.uuid4()
    expired_token = uuid.uuid4()
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, created_at) "
                "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash_old', 'ctx_old', 'PENDING', :tok, NOW() - INTERVAL '120 seconds', NOW() - INTERVAL '120 seconds')"
            ),
            {"id": expired_summary_id, "iid": inv_id, "tok": expired_token},
        )
    engine.dispose()

    async_url = str(disposable_db["settings"].async_database_url)
    async_engine = create_async_engine(async_url)
    session_maker = async_sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )

    settings = Settings(
        ai_provider="mock",
        ai_model="mock-v1",
        ai_timeout_seconds=5.0,
        ai_max_evidence_items=50,
        ai_max_context_bytes=65536,
        ai_pending_timeout_seconds=60,  # 60s cutoff
    )

    service = AISummaryService(
        engine=async_engine, session_maker=session_maker, settings=settings
    )
    admin_user = User(
        id=admin_id,
        email=f"admin_{admin_id.hex[:6]}@example.com",
        password_hash="hash",
        role="ADMIN",
        is_active=True,
    )

    # Trigger generation
    resp = await service.generate_summary(
        investigation_id=inv_id,
        request=AISummaryGenerateRequest(force_refresh=True),
        current_user=admin_user,
    )

    assert resp.status.value == "COMPLETED"
    assert resp.id != expired_summary_id

    # Verify expired summary transitioned to FAILED in database and AuditEvent was logged
    async with session_maker() as session:
        repo = AISummaryRepository()
        old_summary = await repo.get_by_id(session, expired_summary_id)
        assert old_summary is not None
        assert old_summary.status == "FAILED"
        assert old_summary.error_message is not None
        assert "timed out and was recovered" in old_summary.error_message
        assert old_summary.generation_token != expired_token  # Token rotated

        # Verify AuditEvent persisted atomically for recovered expired summary
        stmt = select(AuditEvent).where(
            AuditEvent.entity_type == "investigation",
            AuditEvent.entity_id == inv_id,
            AuditEvent.action == "AI_SUMMARY_FAILED",
        )
        events = list((await session.execute(stmt)).scalars().all())
        assert len(events) == 1
        assert events[0].metadata_ is not None
        assert events[0].metadata_["summary_id"] == str(expired_summary_id)
        assert events[0].metadata_["recovery"] is True

    await async_engine.dispose()


@pytest.mark.asyncio
async def test_generation_token_fencing_rejects_stale_cas(
    disposable_db: dict[str, Any],
) -> None:
    """Attempting terminal CAS write with outdated generation token is rejected."""
    sync_url = str(disposable_db["sync_url"])
    admin_id, tx_id, inv_id = _seed_recovery_fixtures(sync_url)

    async_url = str(disposable_db["settings"].async_database_url)
    async_engine = create_async_engine(async_url)
    session_maker = async_sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )

    repo = AISummaryRepository()
    active_token = uuid.uuid4()
    stale_token = uuid.uuid4()
    summary_id = uuid.uuid4()

    async with session_maker() as session:
        # Create active pending record
        pending = AISummary(
            id=summary_id,
            investigation_id=inv_id,
            provider="mock",
            model="mock-v1",
            prompt_version="pv_1.0",
            evidence_hash="ehash",
            context_hash="chash",
            status="PENDING",
            generation_token=active_token,
            generated_at=datetime.now(UTC),
        )
        await repo.create_pending(session, pending)
        await session.commit()

    # Worker attempts CAS update using STALE generation token
    async with session_maker() as session:
        cas_success = await repo.update_terminal_cas(
            session=session,
            summary_id=summary_id,
            status="COMPLETED",
            generation_token=stale_token,  # Stale!
            completed_at=datetime.now(UTC),
            summary_payload={"executive_summary": "Should be rejected"},
        )
        assert cas_success is False
        await session.rollback()

    # Record should still be PENDING with active_token intact
    async with session_maker() as session:
        rec = await repo.get_by_id(session, summary_id)
        assert rec is not None
        assert rec.status == "PENDING"
        assert rec.generation_token == active_token

    await async_engine.dispose()


@pytest.mark.asyncio
async def test_recovery_losing_race_does_not_create_duplicate_audit_event(
    disposable_db: dict[str, Any],
) -> None:
    """When a worker loses the recovery CAS race, rowcount is 0 and no extra audit event is created."""
    sync_url = str(disposable_db["sync_url"])
    admin_id, tx_id, inv_id = _seed_recovery_fixtures(sync_url)

    # Insert expired PENDING summary
    expired_summary_id = uuid.uuid4()
    expired_token = uuid.uuid4()
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, created_at) "
                "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash_old', 'ctx_old', 'PENDING', :tok, NOW() - INTERVAL '120 seconds', NOW() - INTERVAL '120 seconds')"
            ),
            {"id": expired_summary_id, "iid": inv_id, "tok": expired_token},
        )
    engine.dispose()

    async_url = str(disposable_db["settings"].async_database_url)
    async_engine = create_async_engine(async_url)
    session_maker = async_sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )

    repo = AISummaryRepository()
    cutoff = datetime.now(UTC)

    # Worker 1 recovers the expired pending record
    async with session_maker() as session1, session1.begin():
        recovered1 = await repo.recover_expired_pending(
            session=session1,
            investigation_id=inv_id,
            cutoff_time=cutoff,
            actor_user_id=admin_id,
        )
        assert recovered1 is not None
        assert recovered1.status == "FAILED"

    # Worker 2 attempts to recover right after Worker 1 committed (race lost)
    async with session_maker() as session2, session2.begin():
        recovered2 = await repo.recover_expired_pending(
            session=session2,
            investigation_id=inv_id,
            cutoff_time=cutoff,
            actor_user_id=admin_id,
        )
        assert recovered2 is None

    # Assert exactly ONE audit event exists in total (no duplicates)
    async with session_maker() as session:
        stmt = select(AuditEvent).where(
            AuditEvent.entity_type == "investigation",
            AuditEvent.entity_id == inv_id,
            AuditEvent.action == "AI_SUMMARY_FAILED",
        )
        events = list((await session.execute(stmt)).scalars().all())
        assert len(events) == 1
        assert events[0].metadata_ is not None
        assert events[0].metadata_["summary_id"] == str(expired_summary_id)

    await async_engine.dispose()


@pytest.mark.asyncio
async def test_recovery_rollback_atomicity(
    disposable_db: dict[str, Any],
) -> None:
    """If the transaction rolls back after recover_expired_pending, both status and audit event roll back."""
    sync_url = str(disposable_db["sync_url"])
    admin_id, tx_id, inv_id = _seed_recovery_fixtures(sync_url)

    # Insert expired PENDING summary
    expired_summary_id = uuid.uuid4()
    expired_token = uuid.uuid4()
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, created_at) "
                "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash_old', 'ctx_old', 'PENDING', :tok, NOW() - INTERVAL '120 seconds', NOW() - INTERVAL '120 seconds')"
            ),
            {"id": expired_summary_id, "iid": inv_id, "tok": expired_token},
        )
    engine.dispose()

    async_url = str(disposable_db["settings"].async_database_url)
    async_engine = create_async_engine(async_url)
    session_maker = async_sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )

    repo = AISummaryRepository()
    cutoff = datetime.now(UTC)

    # Simulate an error causing transaction rollback after recovery
    with pytest.raises(RuntimeError):
        async with session_maker() as session, session.begin():
            recovered = await repo.recover_expired_pending(
                session=session,
                investigation_id=inv_id,
                cutoff_time=cutoff,
                actor_user_id=admin_id,
            )
            assert recovered is not None
            raise RuntimeError("Simulated transaction failure")

    # Verify atomic rollback: summary remains PENDING and NO audit event exists
    async with session_maker() as session:
        rec = await repo.get_by_id(session, expired_summary_id)
        assert rec is not None
        assert rec.status == "PENDING"
        assert rec.generation_token == expired_token

        stmt = select(AuditEvent).where(
            AuditEvent.entity_type == "investigation",
            AuditEvent.entity_id == inv_id,
            AuditEvent.action == "AI_SUMMARY_FAILED",
        )
        events = list((await session.execute(stmt)).scalars().all())
        assert len(events) == 0

    await async_engine.dispose()
