"""Integration tests for AI summary concurrent reservation and single-winner guarantees."""

import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from finsignal.ai.exceptions import AISummaryInProgressError
from finsignal.ai.schemas import AISummaryGenerateRequest
from finsignal.ai.service import AISummaryService
from finsignal.common.exceptions import ConflictError
from finsignal.core.config import Settings
from finsignal.users.models import User


def _seed_concurrency_fixtures(sync_url: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
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
async def test_concurrent_generation_single_winner(
    disposable_db: dict[str, Any],
) -> None:
    """Two concurrent requests to generate AI summary result in one success and one 409 Conflict."""
    sync_url = str(disposable_db["sync_url"])
    admin_id, tx_id, inv_id = _seed_concurrency_fixtures(sync_url)

    async_url = str(disposable_db["settings"].async_database_url)
    engine_1 = create_async_engine(async_url, pool_size=5)
    engine_2 = create_async_engine(async_url, pool_size=5)

    session_maker_1 = async_sessionmaker(
        engine_1, expire_on_commit=False, class_=AsyncSession
    )
    session_maker_2 = async_sessionmaker(
        engine_2, expire_on_commit=False, class_=AsyncSession
    )

    settings = Settings(
        ai_provider="mock",
        ai_model="mock-v1",
        ai_timeout_seconds=5.0,
        ai_max_evidence_items=50,
        ai_max_context_bytes=65536,
        ai_pending_timeout_seconds=60,
    )

    service_1 = AISummaryService(
        engine=engine_1, session_maker=session_maker_1, settings=settings
    )
    service_2 = AISummaryService(
        engine=engine_2, session_maker=session_maker_2, settings=settings
    )

    # Inject slight provider delay to simulate realistic in-flight generation window
    from finsignal.ai.providers.mock import MockLLMProvider

    service_1.provider = MockLLMProvider(simulate_delay=0.25)
    service_2.provider = MockLLMProvider(simulate_delay=0.25)

    admin_user = User(
        id=admin_id,
        email=f"admin_{admin_id.hex[:6]}@example.com",
        password_hash="hash",
        role="ADMIN",
        is_active=True,
    )

    req = AISummaryGenerateRequest(force_refresh=True)

    results = await asyncio.gather(
        service_1.generate_summary(inv_id, req, admin_user),
        service_2.generate_summary(inv_id, req, admin_user),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"Expected 1 winner, got {len(successes)}: {results}"
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}: {results}"
    assert isinstance(errors[0], (ConflictError, AISummaryInProgressError))
    assert errors[0].status_code == 409

    await engine_1.dispose()
    await engine_2.dispose()
