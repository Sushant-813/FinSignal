"""Independent-connection PostgreSQL concurrency tests for Phase 9 row locking and race conditions."""

import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from finsignal.common.exceptions import (
    AuthorizationError,
    ConflictError,
)
from finsignal.investigations.schemas import (
    InvestigationPatchRequest,
    InvestigationResolution,
    InvestigationResolveRequest,
)
from finsignal.investigations.service import InvestigationService
from finsignal.users.models import User


def _seed_concurrency_fixtures(
    sync_url: str,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Seed prerequisite users, account, transaction, and return (admin_id, inv1_id, inv2_id, tx_id)."""
    engine = create_engine(sync_url)
    admin_id = uuid.uuid4()
    inv1_id = uuid.uuid4()
    inv2_id = uuid.uuid4()
    account_id = uuid.uuid4()
    tx_id = uuid.uuid4()

    with engine.begin() as conn:
        # Seed users
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, is_active, created_at, updated_at) "
                "VALUES (:id, :email, 'hash', :role, true, NOW(), NOW())"
            ),
            [
                {
                    "id": admin_id,
                    "email": f"admin_{admin_id.hex[:6]}@example.com",
                    "role": "ADMIN",
                },
                {
                    "id": inv1_id,
                    "email": f"inv1_{inv1_id.hex[:6]}@example.com",
                    "role": "INVESTIGATOR",
                },
                {
                    "id": inv2_id,
                    "email": f"inv2_{inv2_id.hex[:6]}@example.com",
                    "role": "INVESTIGATOR",
                },
            ],
        )

        # Seed account & transaction
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
                "VALUES (:tid, 'SYNTHETIC', :ext_tid, :aid, NOW(), 150.00, 'USD', 'PURCHASE', 'DEBIT', NOW())"
            ),
            {"tid": tx_id, "ext_tid": f"TX_{tx_id.hex[:6]}", "aid": account_id},
        )

    engine.dispose()
    return admin_id, inv1_id, inv2_id, tx_id


@pytest.mark.asyncio
async def test_concurrent_self_assignment_race(
    disposable_db: dict[str, Any],
) -> None:
    """Verify that when two investigators concurrently self-assign an unassigned investigation,
    PostgreSQL SELECT ... FOR UPDATE ensures exactly one succeeds and the other receives 409 CASE_ALREADY_ASSIGNED.
    """
    sync_url = str(disposable_db["sync_url"])
    async_url = str(disposable_db["settings"].async_database_url)

    admin_id, inv1_id, inv2_id, tx_id = _seed_concurrency_fixtures(sync_url)
    engine = create_engine(sync_url)

    # Seed unassigned investigation in OPEN state
    investigation_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
                "VALUES (:iid, NULL, 'OPEN', 'MEDIUM', NOW(), NOW())"
            ),
            {"iid": investigation_id},
        )
        conn.execute(
            text(
                "INSERT INTO investigation_transactions (investigation_id, transaction_id, relationship_type, created_at) "
                "VALUES (:iid, :tid, 'PRIMARY', NOW())"
            ),
            {"iid": investigation_id, "tid": tx_id},
        )
    engine.dispose()

    async_engine_1 = create_async_engine(async_url, pool_size=1)
    async_engine_2 = create_async_engine(async_url, pool_size=1)

    user1 = User()
    user1.id = inv1_id
    user1.role = "INVESTIGATOR"
    user1.is_active = True

    user2 = User()
    user2.id = inv2_id
    user2.role = "INVESTIGATOR"
    user2.is_active = True

    service1 = InvestigationService()
    service2 = InvestigationService()

    results: list[Any] = []
    errors: list[Exception] = []

    async def attempt_assign(
        engine_inst: Any,
        service: InvestigationService,
        user: User,
    ) -> None:
        async with AsyncSession(engine_inst) as session:
            try:
                res = await service.patch_investigation(
                    session=session,
                    investigation_id=investigation_id,
                    patch=InvestigationPatchRequest(assigned_to=user.id),
                    current_user=user,
                )
                await session.commit()
                results.append((user.id, res))
            except Exception as e:
                await session.rollback()
                errors.append(e)

    # Execute concurrent assignments across independent PostgreSQL connections
    await asyncio.gather(
        attempt_assign(async_engine_1, service1, user1),
        attempt_assign(async_engine_2, service2, user2),
    )

    await async_engine_1.dispose()
    await async_engine_2.dispose()

    # Invariants: Exactly one winner, exactly one 409 ConflictError
    assert len(results) == 1, f"Expected 1 winner, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"

    error = errors[0]
    assert isinstance(error, (ConflictError, AuthorizationError)), (
        f"Expected ConflictError or AuthorizationError on race loser, got {type(error)}"
    )
    if isinstance(error, ConflictError):
        assert error.code == "CASE_ALREADY_ASSIGNED"
        assert error.status_code == 409
    else:
        assert error.code == "FORBIDDEN"
        assert error.status_code == 403

    # Verify database state has winner assigned
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        assigned_user = conn.execute(
            text("SELECT assigned_to FROM investigations WHERE id = :iid"),
            {"iid": investigation_id},
        ).scalar()
        winner_id = results[0][0]
        assert assigned_user == winner_id, f"Expected {winner_id}, got {assigned_user}"

        audit_count = conn.execute(
            text(
                "SELECT count(*) FROM audit_events "
                "WHERE entity_id = :iid AND action = 'INVESTIGATION_ASSIGNED'"
            ),
            {"iid": investigation_id},
        ).scalar()
        assert audit_count == 1, f"Expected 1 audit event, got {audit_count}"
    engine.dispose()


@pytest.mark.asyncio
async def test_investigator_taking_already_assigned_case_forbidden(
    disposable_db: dict[str, Any],
) -> None:
    """Verify an investigator attempting to take an investigation already assigned to another
    investigator receives 403 FORBIDDEN.
    """
    sync_url = str(disposable_db["sync_url"])
    async_url = str(disposable_db["settings"].async_database_url)

    admin_id, inv1_id, inv2_id, tx_id = _seed_concurrency_fixtures(sync_url)
    engine = create_engine(sync_url)

    investigation_id = uuid.uuid4()
    with engine.begin() as conn:
        # Pre-assign to Investigator 1
        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
                "VALUES (:iid, :uid, 'OPEN', 'MEDIUM', NOW(), NOW())"
            ),
            {"iid": investigation_id, "uid": inv1_id},
        )
        conn.execute(
            text(
                "INSERT INTO investigation_transactions (investigation_id, transaction_id, relationship_type, created_at) "
                "VALUES (:iid, :tid, 'PRIMARY', NOW())"
            ),
            {"iid": investigation_id, "tid": tx_id},
        )
    engine.dispose()

    async_engine = create_async_engine(async_url)
    user2 = User()
    user2.id = inv2_id
    user2.role = "INVESTIGATOR"
    user2.is_active = True

    service = InvestigationService()

    async with AsyncSession(async_engine) as session:
        with pytest.raises(AuthorizationError) as exc_info:
            await service.patch_investigation(
                session=session,
                investigation_id=investigation_id,
                patch=InvestigationPatchRequest(assigned_to=user2.id),
                current_user=user2,
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "FORBIDDEN"

    await async_engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_resolution_race(
    disposable_db: dict[str, Any],
) -> None:
    """Verify that concurrent resolution attempts are serialized by row-level locking,
    resulting in exactly one successful resolution and one 409 conflict.
    """
    sync_url = str(disposable_db["sync_url"])
    async_url = str(disposable_db["settings"].async_database_url)

    admin_id, inv1_id, inv2_id, tx_id = _seed_concurrency_fixtures(sync_url)
    engine = create_engine(sync_url)

    investigation_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
                "VALUES (:iid, :uid, 'UNDER_REVIEW', 'HIGH', NOW(), NOW())"
            ),
            {"iid": investigation_id, "uid": inv1_id},
        )
        conn.execute(
            text(
                "INSERT INTO investigation_transactions (investigation_id, transaction_id, relationship_type, created_at) "
                "VALUES (:iid, :tid, 'PRIMARY', NOW())"
            ),
            {"iid": investigation_id, "tid": tx_id},
        )
    engine.dispose()

    async_engine_1 = create_async_engine(async_url, pool_size=1)
    async_engine_2 = create_async_engine(async_url, pool_size=1)

    investigator = User()
    investigator.id = inv1_id
    investigator.role = "INVESTIGATOR"
    investigator.is_active = True

    service1 = InvestigationService()
    service2 = InvestigationService()

    results: list[Any] = []
    errors: list[Exception] = []

    async def attempt_resolve(
        engine_inst: Any,
        service: InvestigationService,
        outcome: InvestigationResolution,
    ) -> None:
        async with AsyncSession(engine_inst) as session:
            try:
                res = await service.resolve_investigation(
                    session=session,
                    investigation_id=investigation_id,
                    request=InvestigationResolveRequest(
                        resolution=outcome,
                        resolution_notes=f"Resolved as {outcome.value}",
                    ),
                    current_user=investigator,
                )
                await session.commit()
                results.append((outcome, res))
            except Exception as e:
                await session.rollback()
                errors.append(e)

    # Execute concurrent resolution across independent connections
    await asyncio.gather(
        attempt_resolve(
            async_engine_1, service1, InvestigationResolution.CONFIRMED_FRAUD
        ),
        attempt_resolve(async_engine_2, service2, InvestigationResolution.LEGITIMATE),
    )

    await async_engine_1.dispose()
    await async_engine_2.dispose()

    # Invariants: Exactly one resolution succeeded
    assert len(results) == 1, f"Expected 1 resolution success, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"

    error = errors[0]
    assert isinstance(error, ConflictError)
    assert error.status_code == 409
    assert error.code == "INVESTIGATION_ALREADY_RESOLVED"

    # Database verification
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        status, resolution = conn.execute(
            text("SELECT status, resolution FROM investigations WHERE id = :iid"),
            {"iid": investigation_id},
        ).one()
        assert status == "RESOLVED"
        assert resolution in ("CONFIRMED_FRAUD", "LEGITIMATE")

        audit_count = conn.execute(
            text(
                "SELECT count(*) FROM audit_events "
                "WHERE entity_id = :iid AND action = 'INVESTIGATION_RESOLVED'"
            ),
            {"iid": investigation_id},
        ).scalar()
        assert audit_count == 1, (
            f"Expected exactly 1 resolution audit event, got {audit_count}"
        )
    engine.dispose()
