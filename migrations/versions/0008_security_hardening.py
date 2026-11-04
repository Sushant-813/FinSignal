"""Security hardening: counterparty namespace FK and audit events immutability (Phase 11).

Revision ID: 0008_security_hardening
Revises: 0007_ai_models
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_security_hardening"
down_revision: str | None = "0007_ai_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply SEC-04 composite foreign key and SEC-05 audit events immutability trigger."""
    conn = op.get_bind()

    # Preflight check for SEC-04: Ensure no existing cross-namespace counterparty mismatches
    mismatch_row = conn.execute(
        sa.text(
            """
            SELECT t.id, t.source_namespace, t.counterparty_account_id, a.source_namespace AS cp_ns
            FROM transactions t
            JOIN accounts a ON t.counterparty_account_id = a.id
            WHERE t.counterparty_account_id IS NOT NULL
              AND t.source_namespace != a.source_namespace
            LIMIT 1;
            """
        )
    ).first()
    if mismatch_row is not None:
        raise RuntimeError(
            f"Preflight assertion failed for migration 0008: transaction {mismatch_row[0]} "
            f"in namespace '{mismatch_row[1]}' references counterparty account {mismatch_row[2]} "
            f"in namespace '{mismatch_row[3]}'."
        )

    # 1. SEC-04: Replace simple counterparty FK with composite namespace-scoped FK
    op.drop_constraint(
        "fk_transactions_counterparty_account_id_accounts",
        "transactions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_transactions_counterparty_namespace",
        "transactions",
        "accounts",
        ["counterparty_account_id", "source_namespace"],
        ["id", "source_namespace"],
        ondelete="RESTRICT",
    )

    # 2. SEC-05: Enforce audit_events append-only immutability trigger
    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_enforce_audit_events_immutability()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events records are append-only and strictly immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_no_update_delete_audit_events
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION trg_enforce_audit_events_immutability();
        """
    )


def downgrade() -> None:
    """Revert SEC-04 composite counterparty FK and SEC-05 audit events immutability trigger."""
    # 1. Revert SEC-05 audit trigger
    op.execute(
        "DROP TRIGGER IF EXISTS trg_no_update_delete_audit_events ON audit_events;"
    )
    op.execute("DROP FUNCTION IF EXISTS trg_enforce_audit_events_immutability();")

    # 2. Revert SEC-04 composite FK
    op.drop_constraint(
        "fk_transactions_counterparty_namespace",
        "transactions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_transactions_counterparty_account_id_accounts",
        "transactions",
        "accounts",
        ["counterparty_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
