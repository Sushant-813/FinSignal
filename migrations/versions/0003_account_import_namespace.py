"""Account and dataset import namespace migration (Checkpoint P4.0 per ADR-065 Decision D).

Revision ID: 0003_account_import_namespace
Revises: 0002_core_operational_schema
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_account_import_namespace"
down_revision: str | None = "0002_core_operational_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply staged namespace migration to accounts and dataset_imports with safe reconciliation."""
    conn = op.get_bind()

    # Preflight Check I5: Active Import Safeguard
    # Migrations must be executed during an authorized maintenance window where zero imports have status PENDING or PROCESSING.
    active_imports_res = conn.execute(
        sa.text(
            "SELECT count(*) FROM dataset_imports WHERE status IN ('PENDING', 'PROCESSING')"
        )
    ).scalar()
    if active_imports_res and active_imports_res > 0:
        raise RuntimeError(
            f"Migration halted: {active_imports_res} active import(s) detected with status PENDING or PROCESSING. "
            "Migrations must be executed during an authorized maintenance window."
        )

    # -------------------------------------------------------------
    # Stage 1: Add columns as nullable
    # -------------------------------------------------------------
    op.add_column(
        "accounts",
        sa.Column("source_namespace", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "dataset_imports",
        sa.Column("source_namespace", sa.String(length=64), nullable=True),
    )

    # -------------------------------------------------------------
    # Stage 2: Account Reconciliation & Preflight Safeguards
    # -------------------------------------------------------------
    # Case 2: Contaminated accounts linked to transactions spanning multiple namespaces
    contaminated_accounts = conn.execute(
        sa.text(
            """
            SELECT account_id, count(DISTINCT source_namespace) AS ns_count, array_agg(DISTINCT source_namespace) AS namespaces
            FROM transactions
            GROUP BY account_id
            HAVING count(DISTINCT source_namespace) > 1
            """
        )
    ).fetchall()
    if contaminated_accounts:
        details = ", ".join(
            f"account_id={row[0]} namespaces={row[2]}" for row in contaminated_accounts
        )
        raise RuntimeError(
            f"Migration halted: Contaminated accounts detected spanning multiple transaction namespaces: {details}. "
            "Manual operator remediation required; refusing to guess."
        )

    # Case 4: Ambiguous legacy external accounts (no transactions, populated external_account_id)
    ambiguous_accounts = conn.execute(
        sa.text(
            """
            SELECT a.id, a.external_account_id
            FROM accounts a
            LEFT JOIN transactions t ON a.id = t.account_id
            WHERE a.external_account_id IS NOT NULL AND t.id IS NULL
            """
        )
    ).fetchall()
    if ambiguous_accounts:
        details = ", ".join(
            f"id={row[0]} external_id={row[1]}" for row in ambiguous_accounts
        )
        raise RuntimeError(
            f"Migration halted: Ambiguous legacy external accounts detected without transaction provenance: {details}. "
            "Operator confirmation or explicit quarantine assignment required; refusing to guess."
        )

    # Case 1: Unambiguous ledger reconciliation from transactions
    conn.execute(
        sa.text(
            """
            WITH account_namespaces AS (
                SELECT account_id, min(source_namespace) AS resolved_namespace
                FROM transactions
                GROUP BY account_id
                HAVING count(DISTINCT source_namespace) = 1
            )
            UPDATE accounts a
            SET source_namespace = an.resolved_namespace
            FROM account_namespaces an
            WHERE a.id = an.account_id AND a.source_namespace IS NULL
            """
        )
    )

    # Case 3: System / internal accounts (no transactions, external_account_id IS NULL)
    conn.execute(
        sa.text(
            """
            UPDATE accounts a
            SET source_namespace = 'SYNTHETIC'
            WHERE a.source_namespace IS NULL
              AND a.external_account_id IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM transactions t WHERE t.account_id = a.id
              )
            """
        )
    )

    # Preflight Check: Assert no unreconciled accounts remain NULL
    unreconciled_accounts = conn.execute(
        sa.text("SELECT count(*) FROM accounts WHERE source_namespace IS NULL")
    ).scalar()
    if unreconciled_accounts and unreconciled_accounts > 0:
        raise RuntimeError(
            f"Migration halted: {unreconciled_accounts} account(s) remain with unresolvable source_namespace."
        )

    # Case 5: Assert zero duplicate (source_namespace, external_account_id) pairs
    duplicate_accounts = conn.execute(
        sa.text(
            """
            SELECT source_namespace, external_account_id, count(*)
            FROM accounts
            WHERE external_account_id IS NOT NULL AND source_namespace IS NOT NULL
            GROUP BY source_namespace, external_account_id
            HAVING count(*) > 1
            """
        )
    ).fetchall()
    if duplicate_accounts:
        details = ", ".join(
            f"ns={row[0]} ext_id={row[1]} count={row[2]}" for row in duplicate_accounts
        )
        raise RuntimeError(
            f"Migration halted: Duplicate (source_namespace, external_account_id) pairs detected: {details}."
        )

    # -------------------------------------------------------------
    # Stage 3: Dataset Import Reconciliation & Safeguards
    # -------------------------------------------------------------
    # Case I2: Contaminated imports (linked transactions span multiple distinct namespaces)
    contaminated_imports = conn.execute(
        sa.text(
            """
            SELECT first_seen_import_id, count(DISTINCT source_namespace) AS ns_count, array_agg(DISTINCT source_namespace) AS namespaces
            FROM transactions
            WHERE first_seen_import_id IS NOT NULL
            GROUP BY first_seen_import_id
            HAVING count(DISTINCT source_namespace) > 1
            """
        )
    ).fetchall()
    if contaminated_imports:
        details = ", ".join(
            f"import_id={row[0]} namespaces={row[2]}" for row in contaminated_imports
        )
        raise RuntimeError(
            f"Migration halted: Contaminated dataset imports detected spanning multiple transaction namespaces: {details}. "
            "Manual operator remediation required; refusing to guess."
        )

    # Case I1: Unambiguous ledger reconciliation from transactions
    conn.execute(
        sa.text(
            """
            WITH import_namespaces AS (
                SELECT first_seen_import_id AS import_id, min(source_namespace) AS resolved_namespace
                FROM transactions
                WHERE first_seen_import_id IS NOT NULL
                GROUP BY first_seen_import_id
                HAVING count(DISTINCT source_namespace) = 1
            )
            UPDATE dataset_imports di
            SET source_namespace = in_ns.resolved_namespace
            FROM import_namespaces in_ns
            WHERE di.id = in_ns.import_id AND di.source_namespace IS NULL
            """
        )
    )

    # Case I3: Synthetic version metadata reconciliation
    conn.execute(
        sa.text(
            """
            UPDATE dataset_imports di
            SET source_namespace = 'SYNTHETIC'
            FROM dataset_versions dv
            WHERE di.dataset_version_id = dv.id
              AND dv.source_type = 'SYNTHETIC'
              AND di.source_namespace IS NULL
            """
        )
    )

    # Case I4: Check for unlinked / external imports without provenance
    unlinked_imports = conn.execute(
        sa.text("SELECT id FROM dataset_imports WHERE source_namespace IS NULL")
    ).fetchall()
    if unlinked_imports:
        details = ", ".join(str(row[0]) for row in unlinked_imports)
        raise RuntimeError(
            f"Migration halted: Unlinked dataset imports without transaction provenance or version metadata: {details}. "
            "Operator confirmation required; refusing to guess."
        )

    # -------------------------------------------------------------
    # Stage 4: Constraint Transition & Indexing
    # -------------------------------------------------------------
    op.alter_column(
        "accounts",
        "source_namespace",
        existing_type=sa.String(length=64),
        nullable=False,
        server_default=sa.text("'SYNTHETIC'"),
    )
    op.alter_column(
        "dataset_imports",
        "source_namespace",
        existing_type=sa.String(length=64),
        nullable=False,
        server_default=sa.text("'SYNTHETIC'"),
    )

    # Partial unique index on accounts (source_namespace, external_account_id)
    op.create_index(
        "uq_accounts_namespace_external_id",
        "accounts",
        ["source_namespace", "external_account_id"],
        unique=True,
        postgresql_where=sa.text("external_account_id IS NOT NULL"),
    )

    # Update uq_dataset_imports_active_hash to include source_namespace
    op.drop_index("uq_dataset_imports_active_hash", table_name="dataset_imports")
    op.create_index(
        "uq_dataset_imports_active_hash",
        "dataset_imports",
        ["source_namespace", "file_hash"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('PENDING', 'PROCESSING') AND file_hash IS NOT NULL"
        ),
    )

    # Unique constraint on accounts(id, source_namespace) for composite FK backstop
    op.create_unique_constraint(
        "uq_accounts_id_source_namespace",
        "accounts",
        ["id", "source_namespace"],
    )

    # Layered Enforcement (Option C3): Composite foreign key on transactions
    op.create_foreign_key(
        "fk_transactions_account_namespace",
        "transactions",
        "accounts",
        ["account_id", "source_namespace"],
        ["id", "source_namespace"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Revert Checkpoint P4.0 namespace additions and constraints."""
    op.drop_constraint(
        "fk_transactions_account_namespace",
        "transactions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_accounts_id_source_namespace",
        "accounts",
        type_="unique",
    )
    op.drop_index(
        "uq_accounts_namespace_external_id",
        table_name="accounts",
    )
    op.drop_index(
        "uq_dataset_imports_active_hash",
        table_name="dataset_imports",
    )
    op.create_index(
        "uq_dataset_imports_active_hash",
        "dataset_imports",
        ["file_hash"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('PENDING', 'PROCESSING') AND file_hash IS NOT NULL"
        ),
    )
    op.drop_column("dataset_imports", "source_namespace")
    op.drop_column("accounts", "source_namespace")
