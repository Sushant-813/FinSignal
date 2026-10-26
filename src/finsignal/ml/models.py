"""SQLAlchemy declarative model for ML model versions and lifecycle tracking."""

import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class ModelVersion(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Stores metadata, artifact pointers, metrics, and lifecycle status for ML model versions."""

    __tablename__ = "model_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('EXPERIMENTAL', 'VALIDATED', 'ACTIVE', 'RETIRED')",
            name="chk_model_versions_status",
        ),
        UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
        Index(
            "uq_model_versions_active_family",
            "name",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    algorithm: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    feature_version: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    parameters: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    artifact_uri: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    artifact_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="EXPERIMENTAL",
        nullable=False,
        index=True,
    )

    dataset_version = relationship("DatasetVersion")
