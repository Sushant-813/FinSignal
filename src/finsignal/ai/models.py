"""SQLAlchemy declarative persistence models for Phase 10 AI Investigation Assistant."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class AISummary(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """AI-generated investigation summary entity with lifecycle and provenance tracking."""

    __tablename__ = "ai_summaries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name="chk_ai_summaries_status",
        ),
        CheckConstraint(
            "(status = 'PENDING' AND completed_at IS NULL AND summary IS NULL AND error_message IS NULL) "
            "OR (status = 'COMPLETED' AND completed_at IS NOT NULL AND summary IS NOT NULL AND error_message IS NULL) "
            "OR (status = 'FAILED' AND completed_at IS NOT NULL AND summary IS NULL AND error_message IS NOT NULL)",
            name="chk_ai_summaries_lifecycle_state",
        ),
        Index(
            "uq_ai_summaries_one_pending_per_investigation",
            "investigation_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index(
            "ix_ai_summaries_investigation_created",
            "investigation_id",
            text("created_at DESC"),
            "id",
        ),
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    prompt_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    evidence_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    context_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    generation_token: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
    )
    summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    investigation = relationship(
        "Investigation",
        back_populates="ai_summaries",
    )
