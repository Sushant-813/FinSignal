"""Integration tests for Checkpoint P4.0 namespace migration, preflight checks, and safe reconciliation."""

import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def _clean_tables(engine: Any) -> None:
    """Helper to wipe test tables between migration test runs."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE transaction_import_records CASCADE"))
        conn.execute(text("TRUNCATE TABLE transactions CASCADE"))
        conn.execute(text("TRUNCATE TABLE dataset_import_errors CASCADE"))
        conn.execute(text("TRUNCATE TABLE dataset_imports CASCADE"))
        conn.execute(text("TRUNCATE TABLE dataset_versions CASCADE"))
        conn.execute(text("TRUNCATE TABLE account_devices CASCADE"))
        conn.execute(text("TRUNCATE TABLE accounts CASCADE"))


def test_migration_reconciliation_unambiguous_ledger(
    disposable_db: dict[str, Any],
) -> None:
    """Verify safe reconciliation of existing accounts and imports from unambiguous transaction ledgers."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        # 1. Downgrade to 0002_core_operational_schema
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        # 2. Insert historical records directly in 0002 schema (which lacks source_namespace on accounts/imports)
        acc_id = uuid.uuid4()
        imp_id = uuid.uuid4()
        ver_id = uuid.uuid4()
        txn_id = uuid.uuid4()

        with engine.begin() as conn:
            # Create dataset version
            conn.execute(
                text(
                    """
                    INSERT INTO dataset_versions (id, version, source_type)
                    VALUES (:id, 'v1.0.0', 'SYNTHETIC')
                    """
                ),
                {"id": ver_id},
            )
            # Create dataset import without source_namespace
            conn.execute(
                text(
                    """
                    INSERT INTO dataset_imports (id, dataset_version_id, source_type, status, total_rows, valid_rows, invalid_rows)
                    VALUES (:id, :ver_id, 'SYNTHETIC', 'COMPLETED', 1, 1, 0)
                    """
                ),
                {"id": imp_id, "ver_id": ver_id},
            )
            # Create account without source_namespace
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (id, external_account_id, account_type, status)
                    VALUES (:id, 'ACC_RECON_001', 'CHECKING', 'ACTIVE')
                    """
                ),
                {"id": acc_id},
            )
            # Create transaction with source_namespace='SYNTHETIC'
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        id, source_namespace, external_transaction_id, first_seen_import_id,
                        account_id, occurred_at, amount, currency, transaction_type, direction
                    )
                    VALUES (
                        :id, 'SYNTHETIC', 'TX_RECON_001', :imp_id,
                        :acc_id, now(), 50.00, 'USD', 'PURCHASE', 'DEBIT'
                    )
                    """
                ),
                {"id": txn_id, "imp_id": imp_id, "acc_id": acc_id},
            )

        # 3. Upgrade to head (applies 0003)
        command.upgrade(cfg, "head")

        # 4. Verify accounts and dataset_imports reconciled to 'SYNTHETIC'
        with engine.connect() as conn:
            acc_ns = conn.execute(
                text("SELECT source_namespace FROM accounts WHERE id = :id"),
                {"id": acc_id},
            ).scalar()
            assert acc_ns == "SYNTHETIC"

            imp_ns = conn.execute(
                text("SELECT source_namespace FROM dataset_imports WHERE id = :id"),
                {"id": imp_id},
            ).scalar()
            assert imp_ns == "SYNTHETIC"
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()


def test_migration_refuses_active_imports(
    disposable_db: dict[str, Any],
) -> None:
    """Verify migration halts if active imports exist (status PENDING/PROCESSING)."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        imp_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO dataset_imports (id, source_type, status, total_rows, valid_rows, invalid_rows)
                    VALUES (:id, 'CSV', 'PROCESSING', 0, 0, 0)
                    """
                ),
                {"id": imp_id},
            )

        with pytest.raises(Exception, match=r"active import\(s\) detected"):
            command.upgrade(cfg, "head")
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()


def test_migration_refuses_contaminated_accounts(
    disposable_db: dict[str, Any],
) -> None:
    """Verify migration halts if an account has transactions across multiple namespaces."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        acc_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (id, external_account_id, account_type, status)
                    VALUES (:id, 'ACC_CONTAM_001', 'CHECKING', 'ACTIVE')
                    """
                ),
                {"id": acc_id},
            )
            # Transaction 1: SYNTHETIC
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        id, source_namespace, external_transaction_id,
                        account_id, occurred_at, amount, currency, transaction_type, direction
                    )
                    VALUES (
                        :id, 'SYNTHETIC', 'TX_CONTAM_001',
                        :acc_id, now(), 10.00, 'USD', 'PURCHASE', 'DEBIT'
                    )
                    """
                ),
                {"id": uuid.uuid4(), "acc_id": acc_id},
            )
            # Transaction 2: PARTNER_X (contamination!)
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        id, source_namespace, external_transaction_id,
                        account_id, occurred_at, amount, currency, transaction_type, direction
                    )
                    VALUES (
                        :id, 'PARTNER_X', 'TX_CONTAM_002',
                        :acc_id, now(), 20.00, 'USD', 'PURCHASE', 'DEBIT'
                    )
                    """
                ),
                {"id": uuid.uuid4(), "acc_id": acc_id},
            )

        with pytest.raises(Exception, match="Contaminated accounts detected"):
            command.upgrade(cfg, "head")
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()


def test_migration_refuses_ambiguous_external_accounts(
    disposable_db: dict[str, Any],
) -> None:
    """Verify migration halts if an external account has no transaction provenance."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        acc_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (id, external_account_id, account_type, status)
                    VALUES (:id, 'ACC_AMBIG_001', 'CHECKING', 'ACTIVE')
                    """
                ),
                {"id": acc_id},
            )

        with pytest.raises(
            Exception, match="Ambiguous legacy external accounts detected"
        ):
            command.upgrade(cfg, "head")
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()


def test_migration_refuses_duplicate_account_identities(
    disposable_db: dict[str, Any],
) -> None:
    """Verify migration halts if reconciling creates duplicate (source_namespace, external_account_id) pairs."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        acc1_id = uuid.uuid4()
        acc2_id = uuid.uuid4()
        with engine.begin() as conn:
            # Two distinct accounts with identical external_account_id
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (id, external_account_id, account_type, status)
                    VALUES (:id, 'ACC_COLLIDE_001', 'CHECKING', 'ACTIVE')
                    """
                ),
                {"id": acc1_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (id, external_account_id, account_type, status)
                    VALUES (:id, 'ACC_COLLIDE_001', 'SAVINGS', 'ACTIVE')
                    """
                ),
                {"id": acc2_id},
            )
            # Both linked to SYNTHETIC transactions
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        id, source_namespace, external_transaction_id,
                        account_id, occurred_at, amount, currency, transaction_type, direction
                    )
                    VALUES (
                        :id, 'SYNTHETIC', 'TX_COL_1',
                        :acc_id, now(), 10.00, 'USD', 'PURCHASE', 'DEBIT'
                    )
                    """
                ),
                {"id": uuid.uuid4(), "acc_id": acc1_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        id, source_namespace, external_transaction_id,
                        account_id, occurred_at, amount, currency, transaction_type, direction
                    )
                    VALUES (
                        :id, 'SYNTHETIC', 'TX_COL_2',
                        :acc_id, now(), 20.00, 'USD', 'PURCHASE', 'DEBIT'
                    )
                    """
                ),
                {"id": uuid.uuid4(), "acc_id": acc2_id},
            )

        with pytest.raises(
            Exception,
            match="Duplicate \\(source_namespace, external_account_id\\) pairs detected",
        ):
            command.upgrade(cfg, "head")
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()


def test_migration_refuses_contaminated_imports(
    disposable_db: dict[str, Any],
) -> None:
    """Verify migration halts if an import's transactions span multiple namespaces."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        imp_id = uuid.uuid4()
        acc1_id = uuid.uuid4()
        acc2_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO dataset_imports (id, source_type, status, total_rows, valid_rows, invalid_rows)
                    VALUES (:id, 'CSV', 'COMPLETED', 2, 2, 0)
                    """
                ),
                {"id": imp_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (id, external_account_id, account_type, status)
                    VALUES (:id, 'ACC_IMP_1', 'CHECKING', 'ACTIVE'),
                           (:id2, 'ACC_IMP_2', 'CHECKING', 'ACTIVE')
                    """
                ),
                {"id": acc1_id, "id2": acc2_id},
            )
            # Transaction 1: SYNTHETIC
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        id, source_namespace, external_transaction_id, first_seen_import_id,
                        account_id, occurred_at, amount, currency, transaction_type, direction
                    )
                    VALUES (
                        :id, 'SYNTHETIC', 'TX_IMP_1', :imp_id,
                        :acc_id, now(), 10.00, 'USD', 'PURCHASE', 'DEBIT'
                    )
                    """
                ),
                {"id": uuid.uuid4(), "imp_id": imp_id, "acc_id": acc1_id},
            )
            # Transaction 2: PARTNER_A (same import, different namespace -> contamination!)
            conn.execute(
                text(
                    """
                    INSERT INTO transactions (
                        id, source_namespace, external_transaction_id, first_seen_import_id,
                        account_id, occurred_at, amount, currency, transaction_type, direction
                    )
                    VALUES (
                        :id, 'PARTNER_A', 'TX_IMP_2', :imp_id,
                        :acc_id, now(), 20.00, 'USD', 'PURCHASE', 'DEBIT'
                    )
                    """
                ),
                {"id": uuid.uuid4(), "imp_id": imp_id, "acc_id": acc2_id},
            )

        with pytest.raises(Exception, match="Contaminated dataset imports detected"):
            command.upgrade(cfg, "head")
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()


def test_migration_refuses_unlinked_external_imports(
    disposable_db: dict[str, Any],
) -> None:
    """Verify migration halts if an import has no transactions and no version metadata."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        imp_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO dataset_imports (id, source_type, status, total_rows, valid_rows, invalid_rows)
                    VALUES (:id, 'CSV', 'COMPLETED', 0, 0, 0)
                    """
                ),
                {"id": imp_id},
            )

        with pytest.raises(
            Exception, match="Unlinked dataset imports without transaction provenance"
        ):
            command.upgrade(cfg, "head")
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()


def test_migration_reconciles_system_accounts(
    disposable_db: dict[str, Any],
) -> None:
    """Verify accounts with external_account_id IS NULL and no transactions are assigned SYNTHETIC."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        command.downgrade(cfg, "0002_core_operational_schema")
        _clean_tables(engine)

        acc_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO accounts (id, external_account_id, account_type, status)
                    VALUES (:id, NULL, 'INTERNAL', 'ACTIVE')
                    """
                ),
                {"id": acc_id},
            )

        command.upgrade(cfg, "head")

        with engine.connect() as conn:
            ns = conn.execute(
                text("SELECT source_namespace FROM accounts WHERE id = :id"),
                {"id": acc_id},
            ).scalar()
            assert ns == "SYNTHETIC"
    finally:
        _clean_tables(engine)
        command.upgrade(cfg, "head")
        engine.dispose()
