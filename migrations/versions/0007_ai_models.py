"""AI Investigation Assistant summaries schema (Phase 10).

Revision ID: 0007_ai_models
Revises: 0006_investigation_models
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_ai_models"
down_revision: str | None = "0006_investigation_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ai_summaries table with lifecycle constraints, unique pending index, and retrieval indexes."""
    op.create_table(
        "ai_summaries",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "investigation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("generation_token", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text(), none_as_null=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED')",
            name="chk_ai_summaries_status",
        ),
        sa.CheckConstraint(
            "(status = 'PENDING' AND completed_at IS NULL AND summary IS NULL AND error_message IS NULL) "
            "OR (status = 'COMPLETED' AND completed_at IS NOT NULL AND summary IS NOT NULL AND error_message IS NULL) "
            "OR (status = 'FAILED' AND completed_at IS NOT NULL AND summary IS NULL AND error_message IS NOT NULL)",
            name="chk_ai_summaries_lifecycle_state",
        ),
    )

    # Partial unique index: At most ONE pending generation attempt per investigation
    op.create_index(
        "uq_ai_summaries_one_pending_per_investigation",
        "ai_summaries",
        ["investigation_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    # Retrieval index for latest summaries by investigation
    op.create_index(
        "ix_ai_summaries_investigation_created",
        "ai_summaries",
        ["investigation_id", sa.text("created_at DESC"), "id"],
    )


def downgrade() -> None:
    """Drop ai_summaries table and indexes in reverse order."""
    op.drop_index(
        "ix_ai_summaries_investigation_created",
        table_name="ai_summaries",
    )
    op.drop_index(
        "uq_ai_summaries_one_pending_per_investigation",
        table_name="ai_summaries",
    )
    op.drop_table("ai_summaries")
