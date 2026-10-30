"""Risk analyses and risk factors schema (Phase 8).

Revision ID: 0005_intelligence_risk_models
Revises: 0004_model_versions
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_intelligence_risk_models"
down_revision: str | None = "0004_model_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create risk_analyses and risk_factors tables with constraints and indexes."""
    op.create_table(
        "risk_analyses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "transaction_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("config_version", sa.String(length=32), nullable=False),
        sa.Column("feature_vector_hash", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("ml_anomaly_score", sa.Float(), nullable=False),
        sa.Column("ml_threshold", sa.Float(), nullable=False),
        sa.Column("normalized_ml_score", sa.Float(), nullable=False),
        sa.Column("rule_score", sa.Float(), nullable=False),
        sa.Column(
            "normalization_params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score >= 0.0 AND score <= 100.0",
            name="chk_risk_analyses_score",
        ),
        sa.CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_risk_analyses_risk_level",
        ),
        sa.UniqueConstraint(
            "transaction_id",
            "model_version_id",
            "config_version",
            "feature_vector_hash",
            name="uq_risk_analyses_identity",
        ),
    )

    op.create_index(
        "ix_risk_analyses_transaction_id", "risk_analyses", ["transaction_id"]
    )
    op.create_index(
        "ix_risk_analyses_model_score",
        "risk_analyses",
        ["model_version_id", "score"],
    )
    op.create_index(
        "ix_risk_analyses_level_created",
        "risk_analyses",
        ["risk_level", "created_at"],
    )
    op.create_index(
        "ix_risk_analyses_tx_created",
        "risk_analyses",
        ["transaction_id", "created_at"],
    )

    op.create_table(
        "risk_factors",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "risk_analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("risk_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("factor_code", sa.String(length=64), nullable=False),
        sa.Column("factor_label", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value_numeric", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_risk_factors_severity",
        ),
    )

    op.create_index("ix_risk_factors_analysis_id", "risk_factors", ["risk_analysis_id"])
    op.create_index("ix_risk_factors_code", "risk_factors", ["factor_code"])


def downgrade() -> None:
    """Drop risk_factors and risk_analyses tables and associated indexes."""
    op.drop_index("ix_risk_factors_code", table_name="risk_factors")
    op.drop_index("ix_risk_factors_analysis_id", table_name="risk_factors")
    op.drop_table("risk_factors")

    op.drop_index("ix_risk_analyses_tx_created", table_name="risk_analyses")
    op.drop_index("ix_risk_analyses_level_created", table_name="risk_analyses")
    op.drop_index("ix_risk_analyses_model_score", table_name="risk_analyses")
    op.drop_index("ix_risk_analyses_transaction_id", table_name="risk_analyses")
    op.drop_table("risk_analyses")
