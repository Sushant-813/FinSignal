"""Unit tests for SQLAlchemy 2.0 domain model definitions, mixins, and metadata."""

from sqlalchemy import CheckConstraint, UniqueConstraint

# Import all models to ensure Base.metadata is self-contained when running test in isolation
import finsignal.accounts.models  # noqa: F401
import finsignal.audit.models  # noqa: F401
import finsignal.dataset.models  # noqa: F401
import finsignal.devices.models  # noqa: F401
import finsignal.locations.models  # noqa: F401
import finsignal.merchants.models  # noqa: F401
import finsignal.transactions.models  # noqa: F401
import finsignal.users.models  # noqa: F401
from finsignal.core.database import Base


def test_metadata_contains_all_12_operational_tables() -> None:
    """Verify that Base.metadata contains exactly the 12 Phase 2 operational tables."""
    expected_tables = {
        "users",
        "accounts",
        "merchants",
        "devices",
        "account_devices",
        "locations",
        "transactions",
        "dataset_versions",
        "dataset_imports",
        "dataset_import_errors",
        "transaction_import_records",
        "audit_events",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert actual_tables == expected_tables


def test_account_devices_composite_primary_key() -> None:
    """Verify that account_devices has composite PK (account_id, device_id) and no synthetic ID."""
    table = Base.metadata.tables["account_devices"]
    pk_cols = [c.name for c in table.primary_key.columns]
    assert sorted(pk_cols) == ["account_id", "device_id"]
    assert "id" not in table.columns
    assert "created_at" not in table.columns
    assert "updated_at" not in table.columns
    assert "first_seen_at" in table.columns
    assert "last_seen_at" in table.columns
    assert "is_primary" in table.columns


def test_mutable_tables_have_updated_at() -> None:
    """Verify that only the 4 mutable entity tables define updated_at."""
    mutable_tables = {"users", "accounts", "merchants", "devices"}
    for table_name in mutable_tables:
        table = Base.metadata.tables[table_name]
        assert "created_at" in table.columns
        assert "updated_at" in table.columns
        assert not table.columns["created_at"].nullable
        assert not table.columns["updated_at"].nullable


def test_immutable_tables_do_not_have_updated_at() -> None:
    """Verify that immutable facts and ledgers do not define updated_at."""
    immutable_tables = {
        "locations",
        "transactions",
        "dataset_versions",
        "dataset_imports",
        "dataset_import_errors",
        "transaction_import_records",
        "audit_events",
    }
    for table_name in immutable_tables:
        table = Base.metadata.tables[table_name]
        assert "created_at" in table.columns
        assert "updated_at" not in table.columns, (
            f"Table {table_name} must not have updated_at"
        )


def test_dataset_imports_no_undocumented_columns() -> None:
    """Verify dataset_imports does not contain failure_reason or updated_at."""
    table = Base.metadata.tables["dataset_imports"]
    assert "failure_reason" not in table.columns
    assert "updated_at" not in table.columns
    assert "completed_at" in table.columns
    assert table.columns["completed_at"].nullable
    assert "started_at" in table.columns
    assert not table.columns["started_at"].nullable


def test_dataset_versions_no_is_synthetic() -> None:
    """Verify dataset_versions uses source_type and does not define is_synthetic."""
    table = Base.metadata.tables["dataset_versions"]
    assert "source_type" in table.columns
    assert not table.columns["source_type"].nullable
    assert "is_synthetic" not in table.columns
    assert "version" in table.columns
    assert table.columns["version"].unique


def test_transactions_canonical_identity_columns_not_null() -> None:
    """Verify that source_namespace, account_id, external_transaction_id are strictly NOT NULL."""
    table = Base.metadata.tables["transactions"]
    assert not table.columns["source_namespace"].nullable
    assert not table.columns["account_id"].nullable
    assert not table.columns["external_transaction_id"].nullable
    assert table.columns["first_seen_import_id"].nullable

    # Verify composite unique constraint
    uq_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}
    assert "uq_transactions_canonical_id" in uq_names
    uq = next(c for c in table.constraints if c.name == "uq_transactions_canonical_id")
    assert isinstance(uq, UniqueConstraint)
    assert [col.name for col in uq.columns] == [
        "source_namespace",
        "account_id",
        "external_transaction_id",
    ]


def test_transactions_check_constraints() -> None:
    """Verify transactions has all documented check constraints."""
    table = Base.metadata.tables["transactions"]
    chk_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    expected_chks = {
        "chk_transactions_amount_positive",
        "chk_transactions_direction",
        "chk_transactions_currency_format",
        "chk_transfers_counterparty_distinct",
        "chk_transfers_counterparty_required",
    }
    assert expected_chks.issubset(chk_names)


def test_transaction_import_records_constraints() -> None:
    """Verify transaction_import_records has unique row ordinal and outcome constraints."""
    table = Base.metadata.tables["transaction_import_records"]
    uq = next(c for c in table.constraints if c.name == "uq_import_records_row")
    assert isinstance(uq, UniqueConstraint)
    assert [col.name for col in uq.columns] == [
        "dataset_import_id",
        "source_row_number",
    ]

    chk = next(c for c in table.constraints if c.name == "chk_import_records_outcome")
    assert chk is not None


def test_audit_events_schema() -> None:
    """Verify audit_events has actor_user_id and metadata JSONB without updated_at."""
    table = Base.metadata.tables["audit_events"]
    assert "actor_user_id" in table.columns
    assert table.columns["actor_user_id"].nullable
    assert "metadata" in table.columns
    assert table.columns["metadata"].nullable
    assert "action" in table.columns
    assert "entity_type" in table.columns
    assert "entity_id" in table.columns
    assert "created_at" in table.columns
    assert "updated_at" not in table.columns
