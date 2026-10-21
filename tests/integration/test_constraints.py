"""Integration tests for database constraints, canonical identity, and migrations on disposable DB."""

import os
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from finsignal.accounts.models import Account
from finsignal.common.exceptions import NamespaceMismatchError
from finsignal.core.config import Settings
from finsignal.dataset.models import DatasetImport
from finsignal.transactions.models import Transaction, TransactionImportRecord
from finsignal.transactions.validation import validate_transaction_account_namespace
from tests.integration.conftest import (
    _PROVISIONED_DISPOSABLE_DATABASES,
    get_admin_connection_params,
    is_live_postgres_available,
)

__all__ = [
    "get_admin_connection_params",
    "is_live_postgres_available",
]


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

    # Under a DIFFERENT source_namespace, an account in that namespace with same external_id -> SUCCESS
    acc_cb = Account(
        source_namespace="CORE_BANKING",
        account_type="SAVINGS",
        status="ACTIVE",
    )
    db_session.add(acc_cb)
    db_session.commit()

    t_diff_ns = Transaction(
        source_namespace="CORE_BANKING",
        account_id=acc_cb.id,
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


def test_account_namespace_external_id_partial_unique_index(
    db_session: Session,
) -> None:
    """Verify uq_accounts_namespace_external_id partial unique index."""
    # 1. First account in SYNTHETIC with external_id
    acc1 = Account(
        source_namespace="SYNTHETIC",
        external_account_id="ACC_EXT_001",
        account_type="CHECKING",
        status="ACTIVE",
    )
    db_session.add(acc1)
    db_session.commit()

    # 2. Duplicate (source_namespace, external_account_id) -> MUST FAIL
    acc1_dup = Account(
        source_namespace="SYNTHETIC",
        external_account_id="ACC_EXT_001",
        account_type="SAVINGS",
        status="ACTIVE",
    )
    db_session.add(acc1_dup)
    with pytest.raises(IntegrityError, match="uq_accounts_namespace_external_id"):
        db_session.commit()
    db_session.rollback()

    # 3. Same external_account_id under DIFFERENT namespace -> SUCCESS
    acc_diff_ns = Account(
        source_namespace="PARTNER_BANK",
        external_account_id="ACC_EXT_001",
        account_type="CHECKING",
        status="ACTIVE",
    )
    db_session.add(acc_diff_ns)
    db_session.commit()
    assert acc_diff_ns.id is not None

    # 4. Multiple accounts with external_account_id IS NULL in same namespace -> SUCCESS
    acc_null1 = Account(
        source_namespace="SYNTHETIC",
        external_account_id=None,
        account_type="CHECKING",
        status="ACTIVE",
    )
    acc_null2 = Account(
        source_namespace="SYNTHETIC",
        external_account_id=None,
        account_type="CHECKING",
        status="ACTIVE",
    )
    db_session.add_all([acc_null1, acc_null2])
    db_session.commit()
    assert acc_null1.id != acc_null2.id


def test_dataset_imports_active_hash_namespace_isolation(
    db_session: Session,
) -> None:
    """Verify uq_dataset_imports_active_hash is namespace-scoped (ADR-065 Decision C)."""
    hash_val = "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff"

    # Active import in SYNTHETIC
    imp1 = DatasetImport(
        source_namespace="SYNTHETIC",
        file_hash=hash_val,
        source_type="CSV",
        status="PENDING",
    )
    db_session.add(imp1)
    db_session.commit()

    # Duplicate active import in SAME namespace -> MUST FAIL
    imp1_dup = DatasetImport(
        source_namespace="SYNTHETIC",
        file_hash=hash_val,
        source_type="CSV",
        status="PROCESSING",
    )
    db_session.add(imp1_dup)
    with pytest.raises(IntegrityError, match="uq_dataset_imports_active_hash"):
        db_session.commit()
    db_session.rollback()

    # Same file_hash in DIFFERENT namespace while imp1 is still active -> SUCCESS
    imp_diff_ns = DatasetImport(
        source_namespace="PUBLIC_DATASET_A",
        file_hash=hash_val,
        source_type="CSV",
        status="PENDING",
    )
    db_session.add(imp_diff_ns)
    db_session.commit()
    assert imp_diff_ns.id is not None


def test_transaction_account_namespace_composite_foreign_key_enforcement(
    db_session: Session,
) -> None:
    """Verify Option C2/C3 composite FK fk_transactions_account_namespace structurally blocks mismatch."""
    acc_synth = Account(
        source_namespace="SYNTHETIC",
        account_type="CHECKING",
        status="ACTIVE",
    )
    db_session.add(acc_synth)
    db_session.commit()

    now = datetime.now(UTC)

    # 1. Matching namespace -> SUCCESS
    txn_ok = Transaction(
        source_namespace="SYNTHETIC",
        account_id=acc_synth.id,
        external_transaction_id="TX_NS_MATCH_1",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(txn_ok)
    db_session.commit()
    assert txn_ok.id is not None

    # 2. Mismatched namespace referencing acc_synth -> REJECTED by database composite FK
    txn_mismatch = Transaction(
        source_namespace="CORE_BANKING",  # Mismatch! Account is SYNTHETIC
        account_id=acc_synth.id,
        external_transaction_id="TX_NS_MISMATCH_1",
        amount=Decimal("100.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
        occurred_at=now,
    )
    db_session.add(txn_mismatch)
    with pytest.raises(IntegrityError, match="fk_transactions_account_namespace"):
        db_session.commit()
    db_session.rollback()


def test_transaction_account_namespace_layered_enforcement(
    db_session: Session,
) -> None:
    """Verify Option C3 Layered Enforcement: application validation catches mismatch before insert."""
    acc = Account(
        source_namespace="SYNTHETIC",
        account_type="CHECKING",
        status="ACTIVE",
    )
    db_session.add(acc)
    db_session.commit()

    # Application-level validation provides rich diagnostic error before hitting DB
    with pytest.raises(NamespaceMismatchError) as exc_info:
        validate_transaction_account_namespace(
            account_namespace=acc.source_namespace,
            transaction_namespace="CORE_BANKING",
        )
    assert exc_info.value.code == "NAMESPACE_MISMATCH"
    assert exc_info.value.status_code == 422
