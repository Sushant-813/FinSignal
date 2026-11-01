"""Investigation cases, transaction links, and evidence schema (Phase 9).

Revision ID: 0006_investigation_models
Revises: 0005_intelligence_risk_models
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_investigation_models"
down_revision: str | None = "0005_intelligence_risk_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create investigations, investigation_transactions, and investigation_evidence tables with triggers and indexes."""
    # 1. Table: investigations
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "assigned_to",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.String(length=16),
            server_default="MEDIUM",
            nullable=False,
        ),
        sa.Column("resolution", sa.String(length=32), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED')",
            name="chk_investigations_status",
        ),
        sa.CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_investigations_priority",
        ),
        sa.CheckConstraint(
            "resolution IS NULL OR resolution IN ('LEGITIMATE', 'SUSPICIOUS', 'CONFIRMED_FRAUD', 'INCONCLUSIVE')",
            name="chk_investigations_resolution",
        ),
        sa.CheckConstraint(
            "(status = 'RESOLVED' AND resolution IS NOT NULL AND resolution_notes IS NOT NULL AND length(regexp_replace(resolution_notes, '[[:space:]]', '', 'g')) > 0) "
            "OR (status != 'RESOLVED' AND resolution IS NULL AND resolution_notes IS NULL)",
            name="chk_investigations_resolution_state",
        ),
    )
    op.create_index(
        "ix_investigations_status_priority",
        "investigations",
        ["status", "priority"],
    )
    op.create_index(
        "ix_investigations_assigned_status",
        "investigations",
        ["assigned_to", "status"],
    )
    op.create_index(
        "ix_investigations_created_at",
        "investigations",
        [sa.text("created_at DESC")],
    )

    # 2. Table: investigation_transactions
    op.create_table(
        "investigation_transactions",
        sa.Column(
            "investigation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="RESTRICT"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relationship_type IN ('PRIMARY', 'RELATED')",
            name="chk_inv_tx_rel_type",
        ),
    )
    op.create_index(
        "uq_investigation_single_primary",
        "investigation_transactions",
        ["investigation_id"],
        unique=True,
        postgresql_where=sa.text("relationship_type = 'PRIMARY'"),
    )
    op.create_index(
        "ix_inv_tx_transaction_id",
        "investigation_transactions",
        ["transaction_id"],
    )

    # 3. Table: investigation_evidence
    op.create_table(
        "investigation_evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "investigation_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("investigations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evidence_type IN ('TRANSACTION_FACT', 'RISK_SCORE', 'RISK_FACTOR', 'ACCOUNT_PROFILE', 'DEVICE_PROFILE', 'USER_NOTE')",
            name="chk_inv_evidence_type",
        ),
        sa.CheckConstraint(
            "source_type IN ('TRANSACTION', 'RISK_ANALYSIS', 'RISK_FACTOR', 'ACCOUNT', 'DEVICE', 'USER_NOTE')",
            name="chk_inv_source_type",
        ),
        sa.CheckConstraint(
            "(evidence_type = 'TRANSACTION_FACT' AND source_type = 'TRANSACTION') OR "
            "(evidence_type = 'RISK_SCORE' AND source_type = 'RISK_ANALYSIS') OR "
            "(evidence_type = 'RISK_FACTOR' AND source_type = 'RISK_FACTOR') OR "
            "(evidence_type = 'ACCOUNT_PROFILE' AND source_type = 'ACCOUNT') OR "
            "(evidence_type = 'DEVICE_PROFILE' AND source_type = 'DEVICE') OR "
            "(evidence_type = 'USER_NOTE' AND source_type = 'USER_NOTE')",
            name="chk_inv_evidence_type_source_pair",
        ),
        sa.CheckConstraint(
            "(source_type = 'USER_NOTE' AND source_id IS NULL) OR "
            "(source_type != 'USER_NOTE' AND source_id IS NOT NULL)",
            name="chk_inv_evidence_source_consistency",
        ),
    )
    op.create_index(
        "ix_inv_evidence_investigation_created",
        "investigation_evidence",
        ["investigation_id", sa.text("created_at ASC"), sa.text("id ASC")],
    )
    op.create_index(
        "ix_inv_evidence_source",
        "investigation_evidence",
        ["source_type", "source_id"],
    )

    # 4. Trigger for evidence immutability
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_enforce_evidence_immutability()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'investigation_evidence records are append-only and strictly immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_no_update_delete_evidence
        BEFORE UPDATE OR DELETE ON investigation_evidence
        FOR EACH ROW EXECUTE FUNCTION trg_enforce_evidence_immutability();
        """
    )


def downgrade() -> None:
    """Drop investigation triggers and tables in reverse order."""
    op.execute(
        "DROP TRIGGER IF EXISTS trg_no_update_delete_evidence ON investigation_evidence;"
    )
    op.execute("DROP FUNCTION IF EXISTS trg_enforce_evidence_immutability();")
    op.drop_table("investigation_evidence")
    op.drop_table("investigation_transactions")
    op.drop_table("investigations")
