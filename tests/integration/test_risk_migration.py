"""Integration tests for Alembic migration 0005_intelligence_risk_models upgrade and downgrade."""

import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


def test_migration_0005_upgrade_downgrade_lifecycle(
    disposable_db: dict[str, Any],
) -> None:
    """Verify upgrade to 0005 creates risk tables with constraints, and downgrade drops them cleanly."""
    cfg: Config = disposable_db["alembic_cfg"]
    sync_url = str(disposable_db["sync_url"])
    engine = create_engine(sync_url)

    try:
        # 1. Downgrade to 0004_model_versions
        command.downgrade(cfg, "0004_model_versions")

        with engine.begin() as conn:
            # Verify tables do not exist
            res_tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN ('risk_analyses', 'risk_factors')"
                )
            ).fetchall()
            assert len(res_tables) == 0

        # 2. Upgrade to 0005_intelligence_risk_models
        command.upgrade(cfg, "0005_intelligence_risk_models")

        with engine.begin() as conn:
            # Verify tables exist
            res_tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN ('risk_analyses', 'risk_factors')"
                )
            ).fetchall()
            found_tables = {row[0] for row in res_tables}
            assert found_tables == {"risk_analyses", "risk_factors"}

            # Verify unique constraint on risk_analyses
            res_constraints = conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conname = 'uq_risk_analyses_identity'"
                )
            ).fetchall()
            assert len(res_constraints) == 1

        # 3. Test check constraints on risk_analyses and risk_factors
        with engine.begin() as conn:
            # Insert prerequisite records: account, transaction, model_version
            acc_id = uuid.uuid4()
            tx_id = uuid.uuid4()
            mod_id = uuid.uuid4()

            conn.execute(
                text(
                    "INSERT INTO accounts (id, source_namespace, external_account_id, account_type, status) "
                    "VALUES (:id, 'SYNTHETIC', 'ACC_TEST_001', 'SAVINGS', 'ACTIVE')"
                ),
                {"id": acc_id},
            )
            conn.execute(
                text(
                    "INSERT INTO transactions (id, source_namespace, account_id, external_transaction_id, "
                    "occurred_at, amount, currency, transaction_type, direction) "
                    "VALUES (:id, 'SYNTHETIC', :acc_id, 'TX_TEST_001', now(), 100.00, 'USD', 'PURCHASE', 'DEBIT')"
                ),
                {"id": tx_id, "acc_id": acc_id},
            )
            conn.execute(
                text(
                    "INSERT INTO model_versions (id, name, version, algorithm, status) "
                    "VALUES (:id, 'transaction_anomaly', '1.0.0', 'isolation_forest', 'ACTIVE')"
                ),
                {"id": mod_id},
            )

            # Valid risk analysis insertion
            risk_id = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO risk_analyses (id, transaction_id, model_version_id, config_version, "
                    "feature_vector_hash, score, risk_level, ml_anomaly_score, ml_threshold, "
                    "normalized_ml_score, rule_score, normalization_params) "
                    "VALUES (:id, :tx_id, :mod_id, 'rc_v1.0', 'dummy_hash_64_chars', 45.5, 'MEDIUM', "
                    '0.52, 0.50, 54.0, 30.0, \'{"method":"piecewise_linear"}\')'
                ),
                {"id": risk_id, "tx_id": tx_id, "mod_id": mod_id},
            )

            # Valid risk factor insertion
            factor_id = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO risk_factors (id, risk_analysis_id, factor_code, factor_label, severity, "
                    "description, value_numeric) "
                    "VALUES (:id, :risk_id, 'HIGH_VELOCITY', 'High Velocity', 'CRITICAL', "
                    "'5 transactions in 5m', 5)"
                ),
                {"id": factor_id, "risk_id": risk_id},
            )

        # Check constraint violation: score > 100
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO risk_analyses (id, transaction_id, model_version_id, config_version, "
                    "feature_vector_hash, score, risk_level, ml_anomaly_score, ml_threshold, "
                    "normalized_ml_score, rule_score, normalization_params) "
                    "VALUES (:id, :tx_id, :mod_id, 'rc_v1.0', 'hash2', 105.0, 'CRITICAL', "
                    "0.9, 0.5, 95.0, 100.0, '{}')"
                ),
                {"id": uuid.uuid4(), "tx_id": tx_id, "mod_id": mod_id},
            )

        # Check constraint violation: invalid risk_level
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO risk_analyses (id, transaction_id, model_version_id, config_version, "
                    "feature_vector_hash, score, risk_level, ml_anomaly_score, ml_threshold, "
                    "normalized_ml_score, rule_score, normalization_params) "
                    "VALUES (:id, :tx_id, :mod_id, 'rc_v1.0', 'hash3', 50.0, 'EXTREME', "
                    "0.5, 0.5, 50.0, 50.0, '{}')"
                ),
                {"id": uuid.uuid4(), "tx_id": tx_id, "mod_id": mod_id},
            )

        # Check constraint violation: invalid factor severity
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO risk_factors (id, risk_analysis_id, factor_code, factor_label, severity, description) "
                    "VALUES (:id, :risk_id, 'NEW_DEVICE', 'New Device', 'URGENT', 'desc')"
                ),
                {"id": uuid.uuid4(), "risk_id": risk_id},
            )

        # Unique constraint violation: duplicate identity
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO risk_analyses (id, transaction_id, model_version_id, config_version, "
                    "feature_vector_hash, score, risk_level, ml_anomaly_score, ml_threshold, "
                    "normalized_ml_score, rule_score, normalization_params) "
                    "VALUES (:id, :tx_id, :mod_id, 'rc_v1.0', 'dummy_hash_64_chars', 45.5, 'MEDIUM', "
                    "0.52, 0.50, 54.0, 30.0, '{}')"
                ),
                {"id": uuid.uuid4(), "tx_id": tx_id, "mod_id": mod_id},
            )

        # 4. Downgrade to 0004
        command.downgrade(cfg, "0004_model_versions")

        with engine.begin() as conn:
            res_tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN ('risk_analyses', 'risk_factors')"
                )
            ).fetchall()
            assert len(res_tables) == 0

    finally:
        # Re-upgrade to head for subsequent tests
        command.upgrade(cfg, "head")
