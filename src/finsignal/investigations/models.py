"""SQLAlchemy declarative persistence models for Phase 9 Investigation & Evidence."""

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import CreatedAtMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class Investigation(Base, UUIDPrimaryKeyMixin, UpdatedAtMixin):
    """Core investigative case management workflow entity."""

    __tablename__ = "investigations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED')",
            name="chk_investigations_status",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_investigations_priority",
        ),
        CheckConstraint(
            "resolution IS NULL OR resolution IN ('LEGITIMATE', 'SUSPICIOUS', 'CONFIRMED_FRAUD', 'INCONCLUSIVE')",
            name="chk_investigations_resolution",
        ),
        CheckConstraint(
            "(status = 'RESOLVED' AND resolution IS NOT NULL AND resolution_notes IS NOT NULL AND length(regexp_replace(resolution_notes, '[[:space:]]', '', 'g')) > 0) "
            "OR (status != 'RESOLVED' AND resolution IS NULL AND resolution_notes IS NULL)",
            name="chk_investigations_resolution_state",
        ),
        Index("ix_investigations_status_priority", "status", "priority"),
        Index("ix_investigations_assigned_status", "assigned_to", "status"),
        Index("ix_investigations_created_at", text("created_at DESC")),
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="OPEN",
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(16),
        default="MEDIUM",
        nullable=False,
    )
    resolution: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assigned_user = relationship("User", foreign_keys=[assigned_to])
    transaction_associations = relationship(
        "InvestigationTransaction",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    primary_association = relationship(
        "InvestigationTransaction",
        primaryjoin="and_(Investigation.id == InvestigationTransaction.investigation_id, InvestigationTransaction.relationship_type == 'PRIMARY')",
        uselist=False,
        viewonly=True,
    )
    evidence = relationship(
        "InvestigationEvidence",
        back_populates="investigation",
        cascade="all, delete-orphan",
        order_by="[InvestigationEvidence.created_at.asc(), InvestigationEvidence.id.asc()]",
    )


class InvestigationTransaction(Base, CreatedAtMixin):
    """Junction entity associating financial transactions to an investigation case."""

    __tablename__ = "investigation_transactions"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('PRIMARY', 'RELATED')",
            name="chk_inv_tx_rel_type",
        ),
        Index(
            "uq_investigation_single_primary",
            "investigation_id",
            unique=True,
            postgresql_where=text("relationship_type = 'PRIMARY'"),
        ),
        Index("ix_inv_tx_transaction_id", "transaction_id"),
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    investigation = relationship(
        "Investigation",
        back_populates="transaction_associations",
    )
    transaction = relationship("Transaction")


class InvestigationEvidence(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Append-only factual and contextual evidence supporting an investigation."""

    __tablename__ = "investigation_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('TRANSACTION_FACT', 'RISK_SCORE', 'RISK_FACTOR', 'ACCOUNT_PROFILE', 'DEVICE_PROFILE', 'USER_NOTE')",
            name="chk_inv_evidence_type",
        ),
        CheckConstraint(
            "source_type IN ('TRANSACTION', 'RISK_ANALYSIS', 'RISK_FACTOR', 'ACCOUNT', 'DEVICE', 'USER_NOTE')",
            name="chk_inv_source_type",
        ),
        CheckConstraint(
            "(evidence_type = 'TRANSACTION_FACT' AND source_type = 'TRANSACTION') OR "
            "(evidence_type = 'RISK_SCORE' AND source_type = 'RISK_ANALYSIS') OR "
            "(evidence_type = 'RISK_FACTOR' AND source_type = 'RISK_FACTOR') OR "
            "(evidence_type = 'ACCOUNT_PROFILE' AND source_type = 'ACCOUNT') OR "
            "(evidence_type = 'DEVICE_PROFILE' AND source_type = 'DEVICE') OR "
            "(evidence_type = 'USER_NOTE' AND source_type = 'USER_NOTE')",
            name="chk_inv_evidence_type_source_pair",
        ),
        CheckConstraint(
            "(source_type = 'USER_NOTE' AND source_id IS NULL) OR "
            "(source_type != 'USER_NOTE' AND source_id IS NOT NULL)",
            name="chk_inv_evidence_source_consistency",
        ),
        Index(
            "ix_inv_evidence_investigation_created",
            "investigation_id",
            text("created_at ASC"),
            text("id ASC"),
        ),
        Index("ix_inv_evidence_source", "source_type", "source_id"),
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    investigation = relationship(
        "Investigation",
        back_populates="evidence",
    )
