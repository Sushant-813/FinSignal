"""Integration tests for migration 0006_investigation_models, constraints, indexes, and triggers."""

import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from finsignal.investigations.schemas import InvestigationCreateRequest


def _seed_base_prerequisites(conn: Any) -> tuple[uuid.UUID, uuid.UUID]:
    """Seed prerequisite user, account, and transaction records for constraint testing."""
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    tx_id = uuid.uuid4()

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

    return user_id, tx_id


def test_migration_0006_upgrade_downgrade_lifecycle(
    disposable_db: dict[str, Any],
) -> None:
    """Verify upgrade to 0006 creates tables, constraints, trigger, and downgrade drops them cleanly."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        # 1. Downgrade to 0005_intelligence_risk_models
        command.downgrade(cfg, "0005_intelligence_risk_models")

        with engine.begin() as conn:
            res_tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('investigations', 'investigation_transactions', 'investigation_evidence')"
                )
            ).fetchall()
            assert len(res_tables) == 0

            # Verify trigger function is dropped
            res_funcs = conn.execute(
                text(
                    "SELECT proname FROM pg_proc WHERE proname = 'trg_enforce_evidence_immutability'"
                )
            ).fetchall()
            assert len(res_funcs) == 0

        # 2. Upgrade to 0006_investigation_models
        command.upgrade(cfg, "0006_investigation_models")

        with engine.begin() as conn:
            # Verify tables exist
            res_tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('investigations', 'investigation_transactions', 'investigation_evidence')"
                )
            ).fetchall()
            found_tables = {row[0] for row in res_tables}
            assert found_tables == {
                "investigations",
                "investigation_transactions",
                "investigation_evidence",
            }

            # Verify partial unique index on investigation_transactions
            res_indexes = conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'investigation_transactions' AND indexname = 'uq_investigation_single_primary'"
                )
            ).fetchall()
            assert len(res_indexes) == 1

            # Verify trigger exists on investigation_evidence
            res_triggers = conn.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgname = 'trg_no_update_delete_evidence'"
                )
            ).fetchall()
            assert len(res_triggers) == 1

    finally:
        # Ensure database is left at head
        command.upgrade(cfg, "head")
        engine.dispose()


def test_primary_transaction_partial_unique_index(
    disposable_db: dict[str, Any],
) -> None:
    """Verify that PostgreSQL partial unique index prevents more than one PRIMARY transaction per investigation."""
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    with engine.begin() as conn:
        user_id, tx1_id = _seed_base_prerequisites(conn)
        tx2_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO transactions (id, source_namespace, external_transaction_id, account_id, occurred_at, amount, currency, transaction_type, direction, created_at) "
                "SELECT :tid, 'SYNTHETIC', :ext_tid, account_id, NOW(), 200.00, 'USD', 'PURCHASE', 'DEBIT', NOW() "
                "FROM transactions WHERE id = :ref_tid"
            ),
            {"tid": tx2_id, "ext_tid": f"TX_{tx2_id.hex[:6]}", "ref_tid": tx1_id},
        )

        inv_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
                "VALUES (:iid, :uid, 'OPEN', 'MEDIUM', NOW(), NOW())"
            ),
            {"iid": inv_id, "uid": user_id},
        )

        # First primary insert succeeds
        conn.execute(
            text(
                "INSERT INTO investigation_transactions (investigation_id, transaction_id, relationship_type, created_at) "
                "VALUES (:iid, :tid, 'PRIMARY', NOW())"
            ),
            {"iid": inv_id, "tid": tx1_id},
        )

    # Second primary insert on same investigation must fail with unique violation
    with engine.begin() as conn:
        with pytest.raises(IntegrityError) as exc_info:
            conn.execute(
                text(
                    "INSERT INTO investigation_transactions (investigation_id, transaction_id, relationship_type, created_at) "
                    "VALUES (:iid, :tid, 'PRIMARY', NOW())"
                ),
                {"iid": inv_id, "tid": tx2_id},
            )
        assert "uq_investigation_single_primary" in str(exc_info.value)

    engine.dispose()


def test_evidence_immutability_trigger(
    disposable_db: dict[str, Any],
) -> None:
    """Verify that PostgreSQL trigger rejects UPDATE and DELETE on investigation_evidence."""
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    with engine.begin() as conn:
        user_id, tx_id = _seed_base_prerequisites(conn)
        inv_id = uuid.uuid4()
        ev_id = uuid.uuid4()

        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
                "VALUES (:iid, :uid, 'OPEN', 'MEDIUM', NOW(), NOW())"
            ),
            {"iid": inv_id, "uid": user_id},
        )

        conn.execute(
            text(
                "INSERT INTO investigation_evidence (id, investigation_id, evidence_type, source_type, source_id, title, payload, created_at) "
                "VALUES (:eid, :iid, 'TRANSACTION_FACT', 'TRANSACTION', :tid, 'Primary Tx Fact', '{\"amount\": 100}', NOW())"
            ),
            {"eid": ev_id, "iid": inv_id, "tid": tx_id},
        )

    # Test UPDATE is blocked by trigger
    with engine.begin() as conn:
        with pytest.raises(DBAPIError) as exc_info:
            conn.execute(
                text(
                    "UPDATE investigation_evidence SET title = 'Altered' WHERE id = :eid"
                ),
                {"eid": ev_id},
            )
        assert "append-only and strictly immutable" in str(exc_info.value)

    # Test DELETE is blocked by trigger
    with engine.begin() as conn:
        with pytest.raises(DBAPIError) as exc_info:
            conn.execute(
                text("DELETE FROM investigation_evidence WHERE id = :eid"),
                {"eid": ev_id},
            )
        assert "append-only and strictly immutable" in str(exc_info.value)

    engine.dispose()


def test_investigation_resolution_check_constraint(
    disposable_db: dict[str, Any],
) -> None:
    """Verify chk_investigations_resolution_state rejects whitespace-only notes and non-resolved outcomes."""
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    with engine.begin() as conn:
        user_id, _ = _seed_base_prerequisites(conn)
        inv_id = uuid.uuid4()

        # 1. Non-resolved with resolution set must fail
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                text(
                    "INSERT INTO investigations (id, assigned_to, status, priority, resolution, created_at, updated_at) "
                    "VALUES (:iid, :uid, 'OPEN', 'MEDIUM', 'LEGITIMATE', NOW(), NOW())"
                ),
                {"iid": inv_id, "uid": user_id},
            )

        # 2. RESOLVED with whitespace-only notes must fail
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                text(
                    "INSERT INTO investigations (id, assigned_to, status, priority, resolution, resolution_notes, created_at, updated_at) "
                    "VALUES (:iid, :uid, 'RESOLVED', 'MEDIUM', 'LEGITIMATE', '  \t\n  ', NOW(), NOW())"
                ),
                {"iid": inv_id, "uid": user_id},
            )

        # 3. Valid RESOLVED succeeds
        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, resolution, resolution_notes, created_at, updated_at) "
                "VALUES (:iid, :uid, 'RESOLVED', 'MEDIUM', 'LEGITIMATE', 'Proper resolution notes.', NOW(), NOW())"
            ),
            {"iid": inv_id, "uid": user_id},
        )

    engine.dispose()


def test_evidence_source_pair_and_consistency_constraints(
    disposable_db: dict[str, Any],
) -> None:
    """Verify pairing and source_id consistency CHECK constraints on investigation_evidence."""
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    with engine.begin() as conn:
        user_id, tx_id = _seed_base_prerequisites(conn)
        inv_id = uuid.uuid4()

        conn.execute(
            text(
                "INSERT INTO investigations (id, assigned_to, status, priority, created_at, updated_at) "
                "VALUES (:iid, :uid, 'OPEN', 'MEDIUM', NOW(), NOW())"
            ),
            {"iid": inv_id, "uid": user_id},
        )

        # 1. Mismatched pair (TRANSACTION_FACT with DEVICE) must fail
        with (
            pytest.raises(IntegrityError) as exc_info,
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "INSERT INTO investigation_evidence (id, investigation_id, evidence_type, source_type, source_id, title, created_at) "
                    "VALUES (:eid, :iid, 'TRANSACTION_FACT', 'DEVICE', :tid, 'Mismatch', NOW())"
                ),
                {"eid": uuid.uuid4(), "iid": inv_id, "tid": tx_id},
            )
        assert "chk_inv_evidence_type_source_pair" in str(exc_info.value)

        # 2. USER_NOTE with non-null source_id must fail
        with (
            pytest.raises(IntegrityError) as exc_info,
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "INSERT INTO investigation_evidence (id, investigation_id, evidence_type, source_type, source_id, title, created_at) "
                    "VALUES (:eid, :iid, 'USER_NOTE', 'USER_NOTE', :tid, 'User note with id', NOW())"
                ),
                {"eid": uuid.uuid4(), "iid": inv_id, "tid": tx_id},
            )
        assert "chk_inv_evidence_source_consistency" in str(exc_info.value)

        # 3. Non-USER_NOTE with null source_id must fail
        with (
            pytest.raises(IntegrityError) as exc_info,
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "INSERT INTO investigation_evidence (id, investigation_id, evidence_type, source_type, source_id, title, created_at) "
                    "VALUES (:eid, :iid, 'TRANSACTION_FACT', 'TRANSACTION', NULL, 'Missing tx id', NOW())"
                ),
                {"eid": uuid.uuid4(), "iid": inv_id},
            )
        assert "chk_inv_evidence_source_consistency" in str(exc_info.value)

        # 4. Valid USER_NOTE with null source_id succeeds
        conn.execute(
            text(
                "INSERT INTO investigation_evidence (id, investigation_id, evidence_type, source_type, source_id, title, created_at) "
                "VALUES (:eid, :iid, 'USER_NOTE', 'USER_NOTE', NULL, 'Valid note', NOW())"
            ),
            {"eid": uuid.uuid4(), "iid": inv_id},
        )

    engine.dispose()


@pytest.mark.asyncio
async def test_investigation_creation_atomic_rollback_on_audit_failure(
    disposable_db: dict[str, Any],
) -> None:
    """Verify failure injection during audit event creation rolls back investigation and primary link."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from finsignal.investigations.service import InvestigationService
    from finsignal.users.models import User

    async_url = str(disposable_db["settings"].async_database_url)
    async_engine = create_async_engine(async_url)

    sync_url = str(disposable_db["sync_url"])
    sync_engine = create_engine(sync_url)
    with sync_engine.begin() as conn:
        user_id, tx_id = _seed_base_prerequisites(conn)
        base_inv_count = conn.execute(
            text("SELECT count(*) FROM investigations")
        ).scalar()
    sync_engine.dispose()

    async with AsyncSession(async_engine) as session:
        user = User()
        user.id = user_id
        user.role = "ADMIN"
        user.email = "admin@example.com"
        user.is_active = True

        service = InvestigationService()
        req = InvestigationCreateRequest(transaction_id=tx_id)

        # Inject failure by making session.flush raise an error on the second call (during audit flush)
        real_flush = session.flush
        flush_count = 0

        async def faulty_flush(*args: Any, **kwargs: Any) -> None:
            nonlocal flush_count
            flush_count += 1
            if flush_count >= 2:
                raise RuntimeError("Simulated transient audit logging crash!")
            await real_flush(*args, **kwargs)

        session.flush = faulty_flush  # type: ignore[method-assign]

        with pytest.raises(
            RuntimeError, match="Simulated transient audit logging crash!"
        ):
            await service.create_investigation(session, req, user)
        await session.rollback()

    # Verify no orphan investigation or primary link exists in the database
    with sync_engine.begin() as conn:
        inv_count = conn.execute(text("SELECT count(*) FROM investigations")).scalar()
        link_count = conn.execute(
            text(
                "SELECT count(*) FROM investigation_transactions WHERE transaction_id = :tid"
            ),
            {"tid": tx_id},
        ).scalar()
        assert inv_count == base_inv_count, (
            f"Expected {base_inv_count} investigations, found {inv_count}"
        )
        assert link_count == 0, (
            f"Expected 0 links for target transaction, found {link_count}"
        )
    sync_engine.dispose()
    await async_engine.dispose()
