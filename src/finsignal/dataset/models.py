"""Dataset versioning and ingestion models."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class DatasetVersion(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Logical version and reproducibility metadata for a dataset."""

    __tablename__ = "dataset_versions"

    version: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    generator_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    seed: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    transaction_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    fraud_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 5),
        nullable=True,
    )
    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class DatasetImport(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Physical ingestion attempt record."""

    __tablename__ = "dataset_imports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="chk_dataset_imports_status",
        ),
        Index(
            "uq_dataset_imports_active_hash",
            "file_hash",
            unique=True,
            postgresql_where=text(
                "status IN ('PENDING', 'PROCESSING') AND file_hash IS NOT NULL"
            ),
        ),
    )

    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    file_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
        index=True,
    )
    total_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    valid_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    invalid_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    dataset_version = relationship("DatasetVersion")
    initiator = relationship("User")


class DatasetImportError(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Validation or job-level error associated with an import."""

    __tablename__ = "dataset_import_errors"

    dataset_import_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_imports.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    field_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    error_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    dataset_import = relationship("DatasetImport")
