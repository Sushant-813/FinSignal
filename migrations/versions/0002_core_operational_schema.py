"""Core operational schema (12 tables per Phase 2 Option C).

Revision ID: 0002_core_operational_schema
Revises: 0001_initial_baseline
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_core_operational_schema"
down_revision: str | None = "0001_initial_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the 12 operational tables, constraints, foreign keys, and indexes."""
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(
            "role IN ('ADMIN', 'ANALYST', 'INVESTIGATOR')",
            name="chk_users_role",
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. locations
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_locations"),
    )

    # 3. merchants
    op.create_table(
        "merchants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_merchant_id", sa.String(length=128), nullable=True),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("merchant_category", sa.String(length=64), nullable=False),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_merchants_location_id_locations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_merchants"),
    )
    op.create_index(
        "ix_merchants_external_merchant_id", "merchants", ["external_merchant_id"]
    )
    op.create_index("ix_merchants_location_id", "merchants", ["location_id"])

    # 4. devices
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_device_id", sa.String(length=128), nullable=True),
        sa.Column("device_type", sa.String(length=32), nullable=True),
        sa.Column("operating_system", sa.String(length=64), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_devices"),
    )
    op.create_index("ix_devices_external_device_id", "devices", ["external_device_id"])

    # 5. accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_account_id", sa.String(length=128), nullable=True),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("customer_age", sa.SmallInteger(), nullable=True),
        sa.Column("home_location_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["home_location_id"],
            ["locations.id"],
            name="fk_accounts_home_location_id_locations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accounts"),
    )
    op.create_index(
        "ix_accounts_external_account_id", "accounts", ["external_account_id"]
    )
    op.create_index("ix_accounts_home_location_id", "accounts", ["home_location_id"])

    # 6. account_devices
    op.create_table(
        "account_devices",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_account_devices_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_account_devices_device_id_devices",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("account_id", "device_id", name="pk_account_devices"),
    )

    # 7. dataset_versions
    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("generator_version", sa.String(length=64), nullable=True),
        sa.Column("seed", sa.BigInteger(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("transaction_count", sa.Integer(), nullable=True),
        sa.Column("fraud_rate", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_versions"),
        sa.UniqueConstraint("version", name="uq_dataset_versions_version"),
    )

    # 8. dataset_imports
    op.create_table(
        "dataset_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=True),
        sa.Column("initiated_by", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column(
            "status", sa.String(length=32), server_default="PENDING", nullable=False
        ),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invalid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["dataset_versions.id"],
            name="fk_dataset_imports_dataset_version_id_dataset_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by"],
            ["users.id"],
            name="fk_dataset_imports_initiated_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_imports"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="chk_dataset_imports_status",
        ),
    )
    op.create_index(
        "uq_dataset_imports_active_hash",
        "dataset_imports",
        ["file_hash"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('PENDING', 'PROCESSING') AND file_hash IS NOT NULL"
        ),
    )
    op.create_index(
        "ix_dataset_imports_dataset_version_id",
        "dataset_imports",
        ["dataset_version_id"],
    )
    op.create_index("ix_dataset_imports_status", "dataset_imports", ["status"])

    # 9. dataset_import_errors
    op.create_table(
        "dataset_import_errors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_import_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_import_id"],
            ["dataset_imports.id"],
            name="fk_dataset_import_errors_dataset_import_id_dataset_imports",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dataset_import_errors"),
    )
    op.create_index(
        "ix_dataset_import_errors_dataset_import_id",
        "dataset_import_errors",
        ["dataset_import_id"],
    )

    # 10. transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_namespace",
            sa.String(length=64),
            server_default="SYNTHETIC",
            nullable=False,
        ),
        sa.Column("external_transaction_id", sa.String(length=128), nullable=False),
        sa.Column("first_seen_import_id", sa.Uuid(), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("counterparty_account_id", sa.Uuid(), nullable=True),
        sa.Column("merchant_id", sa.Uuid(), nullable=True),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("payment_method", sa.String(length=32), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_transactions_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["counterparty_account_id"],
            ["accounts.id"],
            name="fk_transactions_counterparty_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_transactions_device_id_devices",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["first_seen_import_id"],
            ["dataset_imports.id"],
            name="fk_transactions_first_seen_import_id_dataset_imports",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_transactions_location_id_locations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name="fk_transactions_merchant_id_merchants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        sa.UniqueConstraint(
            "source_namespace",
            "account_id",
            "external_transaction_id",
            name="uq_transactions_canonical_id",
        ),
        sa.CheckConstraint("amount > 0", name="chk_transactions_amount_positive"),
        sa.CheckConstraint(
            "direction IN ('DEBIT', 'CREDIT')", name="chk_transactions_direction"
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name="chk_transactions_currency_format"
        ),
        sa.CheckConstraint(
            "counterparty_account_id IS NULL OR account_id != counterparty_account_id",
            name="chk_transfers_counterparty_distinct",
        ),
        sa.CheckConstraint(
            "transaction_type != 'TRANSFER' OR counterparty_account_id IS NOT NULL",
            name="chk_transfers_counterparty_required",
        ),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_occurred_at", "transactions", ["occurred_at"])
    op.create_index(
        "ix_transactions_account_occurred",
        "transactions",
        ["account_id", "occurred_at"],
    )
    op.create_index(
        "ix_transactions_first_seen_import_id", "transactions", ["first_seen_import_id"]
    )
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_device_id", "transactions", ["device_id"])
    op.create_index("ix_transactions_location_id", "transactions", ["location_id"])

    # 11. transaction_import_records
    op.create_table(
        "transaction_import_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_import_id", sa.Uuid(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("row_hash", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_import_id"],
            ["dataset_imports.id"],
            name="fk_transaction_import_records_dataset_import_id_dataset_imports",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name="fk_transaction_import_records_transaction_id_transactions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transaction_import_records"),
        sa.UniqueConstraint(
            "dataset_import_id",
            "source_row_number",
            name="uq_import_records_row",
        ),
        sa.CheckConstraint(
            "outcome IN ('INSERTED', 'MATCHED_EXISTING', 'DUPLICATE_IN_IMPORT', 'QUARANTINED', 'REJECTED')",
            name="chk_import_records_outcome",
        ),
    )
    op.create_index(
        "ix_import_records_dataset_import_id",
        "transaction_import_records",
        ["dataset_import_id"],
    )
    op.create_index(
        "ix_import_records_transaction_id",
        "transaction_import_records",
        ["transaction_id"],
    )

    # 12. audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_audit_events_actor_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index(
        "ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"]
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])


def downgrade() -> None:
    """Drop the 12 operational tables in reverse dependency order."""
    op.drop_table("audit_events")
    op.drop_table("transaction_import_records")
    op.drop_table("transactions")
    op.drop_table("dataset_import_errors")
    op.drop_table("dataset_imports")
    op.drop_table("dataset_versions")
    op.drop_table("account_devices")
    op.drop_table("accounts")
    op.drop_table("devices")
    op.drop_table("merchants")
    op.drop_table("locations")
    op.drop_table("users")
