"""Transaction domain persistence models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class Transaction(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Central financial transaction fact."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "source_namespace",
            "account_id",
            "external_transaction_id",
            name="uq_transactions_canonical_id",
        ),
        ForeignKeyConstraint(
            ["account_id", "source_namespace"],
            ["accounts.id", "accounts.source_namespace"],
            name="fk_transactions_account_namespace",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "amount > 0",
            name="chk_transactions_amount_positive",
        ),
        CheckConstraint(
            "direction IN ('DEBIT', 'CREDIT')",
            name="chk_transactions_direction",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="chk_transactions_currency_format",
        ),
        CheckConstraint(
            "counterparty_account_id IS NULL OR account_id != counterparty_account_id",
            name="chk_transfers_counterparty_distinct",
        ),
        CheckConstraint(
            "transaction_type != 'TRANSFER' OR counterparty_account_id IS NOT NULL",
            name="chk_transfers_counterparty_required",
        ),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_occurred_at", "occurred_at"),
        Index("ix_transactions_account_occurred", "account_id", "occurred_at"),
        Index("ix_transactions_first_seen_import_id", "first_seen_import_id"),
    )

    source_namespace: Mapped[str] = mapped_column(
        String(64),
        default="SYNTHETIC",
        nullable=False,
    )
    external_transaction_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    first_seen_import_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_imports.id", ondelete="RESTRICT"),
        nullable=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    counterparty_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    transaction_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    payment_method: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    channel: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    account = relationship("Account", foreign_keys=[account_id])
    counterparty_account = relationship(
        "Account", foreign_keys=[counterparty_account_id]
    )
    merchant = relationship("Merchant")
    device = relationship("Device")
    location = relationship("Location")
    first_seen_import = relationship("DatasetImport")


class TransactionImportRecord(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Observation and provenance record linking a source CSV row to a transaction."""

    __tablename__ = "transaction_import_records"
    __table_args__ = (
        UniqueConstraint(
            "dataset_import_id",
            "source_row_number",
            name="uq_import_records_row",
        ),
        CheckConstraint(
            "outcome IN ('INSERTED', 'MATCHED_EXISTING', 'DUPLICATE_IN_IMPORT', 'QUARANTINED', 'REJECTED')",
            name="chk_import_records_outcome",
        ),
        Index("ix_import_records_transaction_id", "transaction_id"),
        Index("ix_import_records_import_id", "dataset_import_id"),
    )

    dataset_import_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_imports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    row_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    outcome: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    dataset_import = relationship("DatasetImport")
    transaction = relationship("Transaction")
