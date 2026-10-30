"""SQLAlchemy declarative persistence models for Phase 8 Risk Intelligence."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class RiskAnalysis(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Immutable record storing transaction risk prioritization results and model lineage."""

    __tablename__ = "risk_analyses"
    __table_args__ = (
        CheckConstraint(
            "score >= 0.0 AND score <= 100.0",
            name="chk_risk_analyses_score",
        ),
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_risk_analyses_risk_level",
        ),
        UniqueConstraint(
            "transaction_id",
            "model_version_id",
            "config_version",
            "feature_vector_hash",
            name="uq_risk_analyses_identity",
        ),
        Index("ix_risk_analyses_model_score", "model_version_id", "score"),
        Index("ix_risk_analyses_level_created", "risk_level", "created_at"),
        Index("ix_risk_analyses_tx_created", "transaction_id", "created_at"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    config_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    feature_vector_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(
        Numeric(8, 3),
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    ml_anomaly_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    ml_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    normalized_ml_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    rule_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    normalization_params: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    transaction = relationship("Transaction")
    model_version = relationship("ModelVersion")
    factors = relationship(
        "RiskFactor",
        back_populates="risk_analysis",
        cascade="all, delete-orphan",
        order_by="RiskFactor.created_at.asc()",
    )


class RiskFactor(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Structured, verifiable reason supporting a parent risk analysis."""

    __tablename__ = "risk_factors"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_risk_factors_severity",
        ),
        Index("ix_risk_factors_analysis_id", "risk_analysis_id"),
        Index("ix_risk_factors_code", "factor_code"),
    )

    risk_analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("risk_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    factor_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    factor_label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    value_numeric: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6),
        nullable=True,
    )
    value_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    evidence: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    risk_analysis = relationship("RiskAnalysis", back_populates="factors")
