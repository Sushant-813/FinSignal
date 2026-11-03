"""Integration tests for migration 0007_ai_models, constraints, partial unique index, and ORM retention."""

import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from finsignal.investigations.models import Investigation


def _seed_prerequisites(conn: Any) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Seed prerequisite user, account, transaction, and investigation records."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    inv_id = uuid.uuid4()

    conn.execute(
        text(
            "INSERT INTO users (id, email, password_hash, role, is_active, created_at, updated_at) "
            "VALUES (:uid, :email, 'dummy_hash', 'INVESTIGATOR', true, NOW(), NOW())"
        ),
        {"uid": user_id, "email": f"investigator_{user_id.hex[:6]}@example.com"},
    )

    conn.execute(
        text(
            "INSERT INTO accounts (id, source_namespace, external_account_id, account_type, status, created_at, updated_at) "
            "VALUES (:aid, 'SYNTHETIC', :ext_id, 'CHECKING', 'ACTIVE', NOW(), NOW())"
        ),
        {"aid": account_id, "ext_id": f"ACC_{account_id.hex[:6]}"},
    )

    conn.execute(
        text(
            "INSERT INTO transactions (id, source_namespace, external_transaction_id, account_id, occurred_at, amount, currency, transaction_type, direction, created_at) "
            "VALUES (:tid, 'SYNTHETIC', :ext_tid, :aid, NOW(), 100.00, 'USD', 'PURCHASE', 'DEBIT', NOW())"
        ),
        {"tid": tx_id, "ext_tid": f"TX_{tx_id.hex[:6]}", "aid": account_id},
    )

    conn.execute(
        text(
            "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
            "VALUES (:iid, :uid, 'UNDER_REVIEW', 'HIGH', NOW(), NOW())"
        ),
        {"iid": inv_id, "uid": user_id},
    )

    return user_id, tx_id, inv_id


def test_migration_0007_upgrade_downgrade_lifecycle(
    disposable_db: dict[str, Any],
) -> None:
    """Verify upgrade to 0007 creates ai_summaries table and constraints, and downgrade drops them cleanly."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        # 1. Downgrade to 0006_investigation_models
        command.downgrade(cfg, "0006_investigation_models")

        with engine.begin() as conn:
            exists = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_summaries'"
                    ")"
                )
            ).scalar()
            assert exists is False

        # 2. Upgrade back to head (0007_ai_models)
        command.upgrade(cfg, "head")

        with engine.begin() as conn:
            exists = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT 1 FROM information_schema.tables WHERE table_name = 'ai_summaries'"
                    ")"
                )
            ).scalar()
            assert exists is True

            # Verify partial unique index
            idx_exists = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT 1 FROM pg_indexes WHERE indexname = 'uq_ai_summaries_one_pending_per_investigation'"
                    ")"
                )
            ).scalar()
            assert idx_exists is True
    finally:
        engine.dispose()


def test_ai_summaries_lifecycle_constraints(
    disposable_db: dict[str, Any],
) -> None:
    """Verify check constraints enforce valid states, nullability rules, and summary presence."""
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    with engine.begin() as conn:
        _, _, inv_id = _seed_prerequisites(conn)

        # 1. Invalid status
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                text(
                    "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, created_at) "
                    "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash1', 'hash2', 'INVALID_STATUS', :tok, NOW(), NOW())"
                ),
                {"id": uuid.uuid4(), "iid": inv_id, "tok": uuid.uuid4()},
            )

        # 2. PENDING with completed_at not NULL
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                text(
                    "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, completed_at, created_at) "
                    "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash1', 'hash2', 'PENDING', :tok, NOW(), NOW(), NOW())"
                ),
                {"id": uuid.uuid4(), "iid": inv_id, "tok": uuid.uuid4()},
            )

        # 3. COMPLETED with summary IS NULL
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                text(
                    "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, completed_at, created_at) "
                    "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash1', 'hash2', 'COMPLETED', :tok, NOW(), NOW(), NOW())"
                ),
                {"id": uuid.uuid4(), "iid": inv_id, "tok": uuid.uuid4()},
            )

        # 4. FAILED with summary IS NOT NULL
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                text(
                    "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, completed_at, error_message, summary, created_at) "
                    "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash1', 'hash2', 'FAILED', :tok, NOW(), NOW(), 'Some error', '{}'::jsonb, NOW())"
                ),
                {"id": uuid.uuid4(), "iid": inv_id, "tok": uuid.uuid4()},
            )

    engine.dispose()


def test_ai_summaries_single_pending_index(
    disposable_db: dict[str, Any],
) -> None:
    """Verify partial unique index permits only one PENDING summary per investigation."""
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    with engine.begin() as conn:
        _, _, inv_id = _seed_prerequisites(conn)

        # First PENDING succeeds
        pending_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, created_at) "
                "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash1', 'hash2', 'PENDING', :tok, NOW(), NOW())"
            ),
            {"id": pending_id, "iid": inv_id, "tok": uuid.uuid4()},
        )

        # Second PENDING for same investigation must violate partial unique index
        with pytest.raises(IntegrityError) as exc, conn.begin_nested():
            conn.execute(
                text(
                    "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, generated_at, created_at) "
                    "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash1', 'hash2', 'PENDING', :tok, NOW(), NOW())"
                ),
                {"id": uuid.uuid4(), "iid": inv_id, "tok": uuid.uuid4()},
            )
        assert "uq_ai_summaries_one_pending_per_investigation" in str(exc.value)

    engine.dispose()


@pytest.mark.asyncio
async def test_ai_summaries_orm_retention_passive_deletes(
    disposable_db: dict[str, Any],
) -> None:
    """Verify database ON DELETE RESTRICT is strictly preserved when loaded and unloaded parent is deleted."""
    async_url = str(disposable_db["settings"].async_database_url)
    async_engine = create_async_engine(async_url)

    sync_url = str(disposable_db["sync_url"])
    sync_engine = create_engine(sync_url)
    with sync_engine.begin() as conn:
        _, _, inv_id = _seed_prerequisites(conn)
        # Create completed summary
        summary_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO ai_summaries (id, investigation_id, provider, model, prompt_version, evidence_hash, context_hash, status, generation_token, summary, generated_at, completed_at, created_at) "
                "VALUES (:id, :iid, 'mock', 'mock-v1', 'pv_1.0', 'hash1', 'hash2', 'COMPLETED', :tok, '{\"executive_summary\": \"OK\"}'::jsonb, NOW(), NOW(), NOW())"
            ),
            {"id": summary_id, "iid": inv_id, "tok": uuid.uuid4()},
        )
    sync_engine.dispose()

    # 1. Attempt to delete investigation via ORM (without loading ai_summaries relationship)
    async with AsyncSession(async_engine) as session:
        inv = await session.get(Investigation, inv_id)
        assert inv is not None
        await session.delete(inv)
        with pytest.raises(IntegrityError):
            await session.commit()

    # 2. Attempt to delete investigation via ORM with loaded ai_summaries relationship
    async with AsyncSession(async_engine) as session:
        inv = await session.get(Investigation, inv_id)
        assert inv is not None
        # Eagerly load relationship
        await session.run_sync(lambda s: inv.ai_summaries)  # type: ignore[misc]
        await session.delete(inv)
        with pytest.raises(IntegrityError):
            await session.commit()

    await async_engine.dispose()
