"""Model versions registry and lifecycle schema (Phase 7).

Revision ID: 0004_model_versions
Revises: 0003_account_import_namespace
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_model_versions"
down_revision: str | None = "0003_account_import_namespace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create model_versions table with constraints and active-family partial unique index."""
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("algorithm", sa.String(length=128), nullable=False),
        sa.Column("feature_version", sa.String(length=64), nullable=True),
        sa.Column(
            "dataset_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column("artifact_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="EXPERIMENTAL",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('EXPERIMENTAL', 'VALIDATED', 'ACTIVE', 'RETIRED')",
            name="chk_model_versions_status",
        ),
        sa.UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
    )

    op.create_index("ix_model_versions_name", "model_versions", ["name"])
    op.create_index("ix_model_versions_status", "model_versions", ["status"])
    op.create_index(
        "ix_model_versions_dataset_version_id",
        "model_versions",
        ["dataset_version_id"],
    )
    op.create_index(
        "uq_model_versions_active_family",
        "model_versions",
        ["name"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    """Drop model_versions table and indexes."""
    op.drop_index("uq_model_versions_active_family", table_name="model_versions")
    op.drop_index(
        "ix_model_versions_dataset_version_id",
        table_name="model_versions",
    )
    op.drop_index("ix_model_versions_status", table_name="model_versions")
    op.drop_index("ix_model_versions_name", table_name="model_versions")
    op.drop_table("model_versions")
