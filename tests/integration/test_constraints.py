"""Integration tests for database constraints, canonical identity, and migrations on disposable DB."""

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from finsignal.accounts.models import Account
from finsignal.core.config import Settings
from finsignal.dataset.models import DatasetImport
from finsignal.transactions.models import Transaction, TransactionImportRecord


def get_admin_connection_params() -> dict[str, str | int]:
    """Return administrative PostgreSQL connection parameters from settings or environment."""
    from dotenv import dotenv_values

    env_vals = dotenv_values(".env") if os.path.exists(".env") else {}
    host = (
        os.environ.get("POSTGRES_HOST") or env_vals.get("POSTGRES_HOST") or "localhost"
    )
    port = int(os.environ.get("POSTGRES_PORT") or env_vals.get("POSTGRES_PORT") or 5432)
    user = (
        os.environ.get("POSTGRES_USER") or env_vals.get("POSTGRES_USER") or "postgres"
    )

    # If env var is set to conftest default 'test_password', prioritize .env if present
    pw = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("DATABASE_PASSWORD")
    if (not pw or pw == "test_password") and env_vals.get("POSTGRES_PASSWORD"):
        pw = env_vals["POSTGRES_PASSWORD"]
    elif not pw:
        pw = "test_password"

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": pw,
    }


def is_live_postgres_available() -> bool:
    """Check if PostgreSQL server is reachable with admin credentials."""
    params = get_admin_connection_params()
    try:
        conn = psycopg.connect(
            host=params["host"],
            port=params["port"],
            user=params["user"],
            password=params["password"],
            dbname="postgres",
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


_PROVISIONED_DISPOSABLE_DATABASES: set[str] = set()


@pytest.fixture(scope="module")
def disposable_db() -> Generator[dict[str, Any], None, None]:
    """Provision a dedicated, disposable PostgreSQL test database for constraint validation.

    Enforces strict safety preconditions:
    1. Verifies database name has disposable prefix 'finsignal_test_ephem_'.
    2. Verifies environment is 'testing'.
    3. Runs Alembic migrations to head.
    4. Drops the ephemeral database completely on teardown.
    """
    if not is_live_postgres_available():
        pytest.skip("PostgreSQL is not reachable with configured credentials.")

    active_env = os.environ.get("ENVIRONMENT", "")
    if active_env != "testing":
        raise RuntimeError(
            f"Safety abort: Refusing to create disposable test DB in non-testing environment: {active_env!r}"
        )

    params = get_admin_connection_params()
    ephemeral_db_name = f"finsignal_test_ephem_{uuid.uuid4().hex[:8]}"

    # Precondition assertion
    assert ephemeral_db_name.startswith("finsignal_test_ephem_")
    _PROVISIONED_DISPOSABLE_DATABASES.add(ephemeral_db_name)

    admin_conn = psycopg.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname="postgres",
        autocommit=True,
    )

    try:
        admin_conn.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(ephemeral_db_name))
        )

        ephemeral_settings = Settings(
            app_name="FinSignalDisposableTest",
            environment="testing",
            database_host=str(params["host"]),
            database_port=int(params["port"]),
            database_name=ephemeral_db_name,
            database_user=str(params["user"]),
            database_password=SecretStr(str(params["password"])),
            _env_file=None,
        )

        # Run Alembic migrations on the disposable database
        alembic_cfg = Config("alembic.ini")
        escaped_url = ephemeral_settings.sync_database_url.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", escaped_url)
        command.upgrade(alembic_cfg, "head")

        yield {
            "db_name": ephemeral_db_name,
            "settings": ephemeral_settings,
            "sync_url": ephemeral_settings.sync_database_url,
            "alembic_cfg": alembic_cfg,
        }

    finally:
        _PROVISIONED_DISPOSABLE_DATABASES.discard(ephemeral_db_name)
        # Terminate any remaining client connections to allow drop
        try:
            admin_conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid();
                """,
                (ephemeral_db_name,),
            )
            admin_conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(ephemeral_db_name)
                )
            )
        except Exception:
            pass
        finally:
            admin_conn.close()


@pytest.fixture
def db_session(
    disposable_db: dict[str, Any],
) -> Generator[Session, None, None]:
    """Provide a clean SQLAlchemy session bound to the disposable test database."""
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_migration_downgrade_roundtrip_safety(
    disposable_db: dict[str, Any],
) -> None:
    """Verify that Alembic downgrade to base and upgrade to head run cleanly on disposable DB."""
    db_name = str(disposable_db["db_name"])
    settings: Settings = disposable_db["settings"]
    cfg: Config = disposable_db["alembic_cfg"]
    cfg_url = cfg.get_main_option("sqlalchemy.url") or ""

    # Multi-layered fail-closed safety checks before executing destructive downgrade:
    # 1. Active process environment must be explicitly 'testing'
    if os.environ.get("ENVIRONMENT") != "testing":
        raise RuntimeError("Safety abort: ENVIRONMENT is not 'testing'")

    # 2. Settings instance must declare 'testing' environment
    if settings.environment != "testing":
        raise RuntimeError(
            f"Safety abort: Settings environment is {settings.environment!r}"
        )

    # 3. Database name must match strict ephemeral test naming pattern
    if not db_name.startswith("finsignal_test_ephem_"):
        raise RuntimeError(f"Safety abort: Non-ephemeral database name: {db_name}")

    # 4. Database must be actively registered in test-harness provisioned set
    if db_name not in _PROVISIONED_DISPOSABLE_DATABASES:
        raise RuntimeError(
            f"Safety abort: Database {db_name} was not created by this test harness"
        )

    # 5. Alembic configuration target URL must explicitly target this ephemeral database
    if db_name not in cfg_url:
        raise RuntimeError(
            f"Safety abort: Alembic URL does not match ephemeral database: {cfg_url}"
        )

    # 6. Alembic configuration must NEVER target development or production databases
    forbidden_names = ("finsignal_dev", "finsignal_prod", "finsignal_stage")
    if any(forbidden in cfg_url.lower() for forbidden in forbidden_names):
        raise RuntimeError(
            f"Safety abort: Alembic URL targets protected database: {cfg_url}"
        )

    # Downgrade to base
    command.downgrade(cfg, "base")

    # Re-upgrade to head
    command.upgrade(cfg, "head")


def test_transaction_amount_positive_check(db_session: Session) -> None:
    """Verify amount > 0 check constraint (chk_transactions_amount_positive)."""
    acc = Account(account_type="SAVINGS", status="ACTIVE")
    db_session.add(acc)
    db_session.commit()

    now = datetime.now(UTC)

    # Valid positive amount
    t_valid = Transaction(
        account_id=acc.id,
        external_transaction_id="TX_POS_1",
        amount=Decimal("10.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_valid)
    db_session.commit()

    # Zero amount must fail
    t_zero = Transaction(
        account_id=acc.id,
        external_transaction_id="TX_ZERO_1",
        amount=Decimal("0.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_zero)
    with pytest.raises(IntegrityError, match="chk_transactions_amount_positive"):
        db_session.commit()
    db_session.rollback()

    # Negative amount must fail
    t_neg = Transaction(
        account_id=acc.id,
        external_transaction_id="TX_NEG_1",
        amount=Decimal("-5.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_neg)
    with pytest.raises(IntegrityError, match="chk_transactions_amount_positive"):
        db_session.commit()
    db_session.rollback()


def test_transaction_direction_check(db_session: Session) -> None:
    """Verify direction IN ('DEBIT', 'CREDIT') check constraint."""
    acc = Account(account_type="CHECKING", status="ACTIVE")
    db_session.add(acc)
    db_session.commit()
    now = datetime.now(UTC)

    # Invalid direction
    t_invalid = Transaction(
        account_id=acc.id,
        external_transaction_id="TX_DIR_BAD",
        amount=Decimal("50.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="OUTBOUND",
        occurred_at=now,
    )
    db_session.add(t_invalid)
    with pytest.raises(IntegrityError, match="chk_transactions_direction"):
        db_session.commit()
    db_session.rollback()


def test_transaction_currency_format_check(db_session: Session) -> None:
    """Verify currency uppercase 3-letter format constraint."""
    acc = Account(account_type="CHECKING", status="ACTIVE")
    db_session.add(acc)
    db_session.commit()
    now = datetime.now(UTC)

    for bad_curr in ["US", "us", "USDD"]:
        t_bad = Transaction(
            account_id=acc.id,
            external_transaction_id=f"TX_CURR_{bad_curr}",
            amount=Decimal("50.00"),
            currency=bad_curr,
            transaction_type="PURCHASE",
            direction="DEBIT",
            occurred_at=now,
        )
        db_session.add(t_bad)
        with pytest.raises((IntegrityError, DBAPIError)):
            db_session.commit()
        db_session.rollback()


def test_transfer_counterparty_rules(db_session: Session) -> None:
    """Verify transfer counterparty rules and constraints."""
    acc1 = Account(account_type="SAVINGS", status="ACTIVE")
    acc2 = Account(account_type="CHECKING", status="ACTIVE")
    db_session.add_all([acc1, acc2])
    db_session.commit()
    now = datetime.now(UTC)

    # 1. Valid transfer between distinct accounts -> SUCCESS
    t_transfer_valid = Transaction(
        account_id=acc1.id,
        counterparty_account_id=acc2.id,
        external_transaction_id="TX_TRANSFER_OK",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="TRANSFER",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_transfer_valid)
    db_session.commit()

    # 2. Transfer with same source and counterparty account -> REJECTED (chk_transfers_counterparty_distinct)
    t_transfer_self = Transaction(
        account_id=acc1.id,
        counterparty_account_id=acc1.id,
        external_transaction_id="TX_TRANSFER_SELF",
        amount=Decimal("50.00"),
        currency="USD",
        transaction_type="TRANSFER",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_transfer_self)
    with pytest.raises(IntegrityError, match="chk_transfers_counterparty_distinct"):
        db_session.commit()
    db_session.rollback()

    # 3. Transfer without counterparty -> REJECTED (chk_transfers_counterparty_required)
    t_transfer_missing = Transaction(
        account_id=acc1.id,
        counterparty_account_id=None,
        external_transaction_id="TX_TRANSFER_NO_CP",
        amount=Decimal("50.00"),
        currency="USD",
        transaction_type="TRANSFER",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_transfer_missing)
    with pytest.raises(IntegrityError, match="chk_transfers_counterparty_required"):
        db_session.commit()
    db_session.rollback()

    # 4. Purchase without counterparty -> SUCCESS
    t_purchase_ok = Transaction(
        account_id=acc1.id,
        counterparty_account_id=None,
        external_transaction_id="TX_PURCHASE_OK",
        amount=Decimal("25.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_purchase_ok)
    db_session.commit()

    # 5. Purchase with different counterparty -> Permitted at DB constraint level under current rules
    t_purchase_cp = Transaction(
        account_id=acc1.id,
        counterparty_account_id=acc2.id,
        external_transaction_id="TX_PURCHASE_CP",
        amount=Decimal("30.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_purchase_cp)
    db_session.commit()
    assert t_purchase_cp.id is not None


def test_canonical_transaction_uniqueness(db_session: Session) -> None:
    """Verify uq_transactions_canonical_id across source_namespace, account_id, external_transaction_id."""
    acc1 = Account(account_type="SAVINGS", status="ACTIVE")
    acc2 = Account(account_type="SAVINGS", status="ACTIVE")
    db_session.add_all([acc1, acc2])
    db_session.commit()
    now = datetime.now(UTC)

    # First transaction
    t1 = Transaction(
        source_namespace="SYNTHETIC",
        account_id=acc1.id,
        external_transaction_id="TX_UNIQUE_1",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t1)
    db_session.commit()

    # Duplicate under same namespace, account, and external_id must FAIL
    t1_dup = Transaction(
        source_namespace="SYNTHETIC",
        account_id=acc1.id,
        external_transaction_id="TX_UNIQUE_1",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t1_dup)
    with pytest.raises(IntegrityError, match="uq_transactions_canonical_id"):
        db_session.commit()
    db_session.rollback()

    # Same external_transaction_id under DIFFERENT account -> SUCCESS
    t_diff_acc = Transaction(
        source_namespace="SYNTHETIC",
        account_id=acc2.id,
        external_transaction_id="TX_UNIQUE_1",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_diff_acc)
    db_session.commit()

    # Same account and external_id under DIFFERENT source_namespace -> SUCCESS
    t_diff_ns = Transaction(
        source_namespace="CORE_BANKING",
        account_id=acc1.id,
        external_transaction_id="TX_UNIQUE_1",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(t_diff_ns)
    db_session.commit()


def test_dataset_imports_active_hash_partial_unique_index(db_session: Session) -> None:
    """Verify uq_dataset_imports_active_hash partial unique index on PENDING/PROCESSING."""
    hash_val = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"

    # Active import 1: PENDING
    imp1 = DatasetImport(
        file_hash=hash_val,
        source_type="CSV",
        status="PENDING",
    )
    db_session.add(imp1)
    db_session.commit()

    # Active import 2: PROCESSING with same hash -> must FAIL
    imp2 = DatasetImport(
        file_hash=hash_val,
        source_type="CSV",
        status="PROCESSING",
    )
    db_session.add(imp2)
    with pytest.raises(IntegrityError, match="uq_dataset_imports_active_hash"):
        db_session.commit()
    db_session.rollback()

    # Transition imp1 to COMPLETED
    imp1_fresh = db_session.get(DatasetImport, imp1.id)
    assert imp1_fresh is not None
    imp1_fresh.status = "COMPLETED"
    db_session.commit()

    # Now a new PENDING import with same hash is permitted (imp1 is COMPLETED, exits index predicate)
    imp3 = DatasetImport(
        file_hash=hash_val,
        source_type="CSV",
        status="PENDING",
    )
    db_session.add(imp3)
    db_session.commit()
    assert imp3.id is not None

    # Null file_hash: multiple active imports permitted
    imp_null1 = DatasetImport(file_hash=None, source_type="CSV", status="PENDING")
    imp_null2 = DatasetImport(file_hash=None, source_type="CSV", status="PENDING")
    db_session.add_all([imp_null1, imp_null2])
    db_session.commit()


def test_transaction_import_records_row_uniqueness(db_session: Session) -> None:
    """Verify uq_import_records_row constraint on (dataset_import_id, source_row_number)."""
    imp = DatasetImport(source_type="CSV", status="PROCESSING")
    db_session.add(imp)
    db_session.commit()

    rec1 = TransactionImportRecord(
        dataset_import_id=imp.id,
        source_row_number=1,
        outcome="INSERTED",
    )
    db_session.add(rec1)
    db_session.commit()

    # Duplicate row ordinal within same import must FAIL
    rec1_dup = TransactionImportRecord(
        dataset_import_id=imp.id,
        source_row_number=1,
        outcome="MATCHED_EXISTING",
    )
    db_session.add(rec1_dup)
    with pytest.raises(IntegrityError, match="uq_import_records_row"):
        db_session.commit()
    db_session.rollback()


def test_transaction_import_records_outcome_check(db_session: Session) -> None:
    """Verify chk_import_records_outcome allows all 5 outcomes and rejects invalid ones."""
    imp = DatasetImport(source_type="CSV", status="PROCESSING")
    db_session.add(imp)
    db_session.commit()

    valid_outcomes = [
        "INSERTED",
        "MATCHED_EXISTING",
        "DUPLICATE_IN_IMPORT",
        "QUARANTINED",
        "REJECTED",
    ]
    for idx, outcome in enumerate(valid_outcomes, start=10):
        rec = TransactionImportRecord(
            dataset_import_id=imp.id,
            source_row_number=idx,
            outcome=outcome,
        )
        db_session.add(rec)
    db_session.commit()

    # Invalid outcome must FAIL
    rec_bad = TransactionImportRecord(
        dataset_import_id=imp.id,
        source_row_number=999,
        outcome="INVALID_OUTCOME",
    )
    db_session.add(rec_bad)
    with pytest.raises(IntegrityError, match="chk_import_records_outcome"):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_delete_restrict(db_session: Session) -> None:
    """Verify ON DELETE RESTRICT prevents deleting an Account with associated Transactions."""
    acc = Account(account_type="SAVINGS", status="ACTIVE")
    db_session.add(acc)
    db_session.commit()

    txn = Transaction(
        account_id=acc.id,
        external_transaction_id="TX_RESTRICT_1",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=datetime.now(UTC),
    )
    db_session.add(txn)
    db_session.commit()

    # Deleting account must fail due to foreign key restriction
    db_session.delete(acc)
    with pytest.raises(IntegrityError, match="foreign key|violates foreign key"):
        db_session.commit()
    db_session.rollback()


def test_transaction_and_provenance_persistence_atomicity(db_session: Session) -> None:
    """Verify that a batch inserting a transaction and provenance record rolls back atomically on failure."""
    acc = Account(account_type="SAVINGS", status="ACTIVE")
    imp = DatasetImport(source_type="CSV", status="PROCESSING")
    db_session.add_all([acc, imp])
    db_session.commit()

    # Pre-seed row 1 in import records
    pre_rec = TransactionImportRecord(
        dataset_import_id=imp.id,
        source_row_number=1,
        outcome="INSERTED",
    )
    db_session.add(pre_rec)
    db_session.commit()

    # Attempt to insert a transaction and a duplicate row 1 provenance record in the same transaction
    txn = Transaction(
        account_id=acc.id,
        external_transaction_id="TX_ATOMIC_1",
        amount=Decimal("75.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=datetime.now(UTC),
    )
    dup_rec = TransactionImportRecord(
        dataset_import_id=imp.id,
        source_row_number=1,  # Duplicate!
        outcome="INSERTED",
    )

    db_session.add(txn)
    db_session.add(dup_rec)
    with pytest.raises(IntegrityError, match="uq_import_records_row"):
        db_session.commit()
    db_session.rollback()

    # Verify that txn was NOT inserted (rolled back atomically)
    found_txn = db_session.execute(
        select(Transaction).where(Transaction.external_transaction_id == "TX_ATOMIC_1")
    ).scalar_one_or_none()
    assert found_txn is None
