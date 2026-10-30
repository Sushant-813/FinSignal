"""PostgreSQL integration tests for risk analysis and factor persistence, atomicity, and constraints."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.ml.models import ModelVersion
from finsignal.risk.models import RiskAnalysis, RiskFactor
from finsignal.risk.repository import RiskRepository, is_risk_identity_conflict
from finsignal.transactions.models import Transaction


@pytest.fixture
async def async_session(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound to the disposable test database."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        yield session
        try:
            await session.rollback()
            await session.execute(
                text(
                    "TRUNCATE TABLE risk_factors, risk_analyses, audit_events, transactions, accounts, model_versions CASCADE;"
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


async def _seed_prerequisites(
    session: AsyncSession,
) -> tuple[Account, Transaction, ModelVersion]:
    """Seed prerequisite account, transaction, and model_version records."""
    acc = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id=f"ACC_{uuid.uuid4().hex[:8]}",
        account_type="SAVINGS",
        status="ACTIVE",
    )
    session.add(acc)
    await session.flush()

    tx = Transaction(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        account_id=acc.id,
        external_transaction_id=f"TX_{uuid.uuid4().hex[:8]}",
        occurred_at=datetime.now(UTC),
        amount=Decimal("150.00"),
        currency="USD",
        transaction_type="PURCHASE",
        direction="DEBIT",
    )
    session.add(tx)

    model = ModelVersion(
        id=uuid.uuid4(),
        name="transaction_anomaly",
        version="1.0.0",
        algorithm="isolation_forest",
        feature_version="v1.0",
        parameters={"n_estimators": 100},
        metrics={"alert_rate": 0.045},
        artifact_uri="models/model_v1.0.joblib",
        artifact_hash="a" * 64,
        status="ACTIVE",
    )
    session.add(model)
    await session.flush()

    return acc, tx, model


@pytest.mark.asyncio
async def test_risk_analysis_and_factors_persistence_atomic(
    async_session: AsyncSession,
) -> None:
    """Verify atomic persistence of RiskAnalysis and associated RiskFactors."""
    _, tx, model = await _seed_prerequisites(async_session)
    repo = RiskRepository()

    analysis_id = uuid.uuid4()
    analysis = RiskAnalysis(
        id=analysis_id,
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="f" * 64,
        score=Decimal("62.50"),
        risk_level="HIGH",
        ml_anomaly_score=0.18,
        ml_threshold=0.12,
        normalized_ml_score=55.0,
        rule_score=40.0,
        normalization_params={"method": "piecewise_linear"},
    )

    factors = [
        RiskFactor(
            id=uuid.uuid4(),
            risk_analysis_id=analysis_id,
            factor_code="HIGH_VELOCITY",
            factor_label="High Velocity",
            severity="HIGH",
            description="3 transactions within 5m",
            value_numeric=Decimal("3.0"),
            evidence={"window_m": 5, "count": 3},
        ),
        RiskFactor(
            id=uuid.uuid4(),
            risk_analysis_id=analysis_id,
            factor_code="NEW_DEVICE",
            factor_label="New Device",
            severity="MEDIUM",
            description="First transaction from device dev_001",
            value_text="dev_001",
            evidence={"device_id": "dev_001"},
        ),
    ]

    saved = await repo.save_atomic(
        session=async_session,
        analysis=analysis,
        factors=factors,
    )
    await async_session.commit()

    assert saved.id == analysis_id
    assert saved.score == Decimal("62.50")
    assert saved.risk_level == "HIGH"

    # Verify retrieval
    retrieved = await repo.get_by_id(async_session, analysis_id)
    assert retrieved is not None
    assert retrieved.transaction_id == tx.id
    assert retrieved.model_version_id == model.id
    assert len(retrieved.factors) == 2
    # Verify factors ordered by severity desc
    assert retrieved.factors[0].factor_code == "HIGH_VELOCITY"
    assert retrieved.factors[0].severity == "HIGH"
    assert retrieved.factors[1].factor_code == "NEW_DEVICE"
    assert retrieved.factors[1].severity == "MEDIUM"


@pytest.mark.asyncio
async def test_risk_persistence_atomicity_on_factor_failure(
    async_session: AsyncSession,
) -> None:
    """Verify that if a factor violates constraints, the entire risk analysis rolls back."""
    _, tx, model = await _seed_prerequisites(async_session)
    repo = RiskRepository()

    analysis_id = uuid.uuid4()
    analysis = RiskAnalysis(
        id=analysis_id,
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="1" * 64,
        score=Decimal("50.00"),
        risk_level="HIGH",
        ml_anomaly_score=0.10,
        ml_threshold=0.10,
        normalized_ml_score=50.0,
        rule_score=50.0,
        normalization_params={"method": "piecewise_linear"},
    )

    # Factor with invalid severity violating chk_risk_factors_severity
    factor = RiskFactor(
        id=uuid.uuid4(),
        risk_analysis_id=analysis_id,
        factor_code="INVALID_CODE",
        factor_label="Invalid",
        severity="SUPER_CRITICAL",  # Violates check constraint
        description="Invalid severity factor",
    )

    with pytest.raises(IntegrityError) as excinfo:
        await repo.save_atomic(
            session=async_session,
            analysis=analysis,
            factors=[factor],
        )

    # Factor check constraint violation must NOT be classified as an identity collision
    assert is_risk_identity_conflict(excinfo.value) is False

    await async_session.rollback()

    # Verify parent analysis was NOT persisted
    res = await async_session.execute(
        text("SELECT COUNT(*) FROM risk_analyses WHERE id = :id"),
        {"id": analysis_id},
    )
    assert res.scalar() == 0


@pytest.mark.asyncio
async def test_risk_repository_save_atomic_idempotent_duplicate_handling(
    async_session: AsyncSession,
) -> None:
    """Verify unique collision on identity raises IntegrityError and savepoint rolls back safely."""
    _, tx, model = await _seed_prerequisites(async_session)
    repo = RiskRepository()

    # First save
    analysis_1 = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="a" * 64,
        score=Decimal("40.00"),
        risk_level="MEDIUM",
        ml_anomaly_score=0.10,
        ml_threshold=0.12,
        normalized_ml_score=40.0,
        rule_score=40.0,
        normalization_params={"method": "piecewise_linear"},
    )
    await repo.save_atomic(
        session=async_session,
        analysis=analysis_1,
        factors=[],
    )
    await async_session.commit()

    # Second save with exact identical 4-tuple identity raises IntegrityError in savepoint
    analysis_2 = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="a" * 64,
        score=Decimal("40.00"),
        risk_level="MEDIUM",
        ml_anomaly_score=0.10,
        ml_threshold=0.12,
        normalized_ml_score=40.0,
        rule_score=40.0,
        normalization_params={"method": "piecewise_linear"},
    )
    with pytest.raises(IntegrityError) as excinfo:
        await repo.save_atomic(
            session=async_session,
            analysis=analysis_2,
            factors=[],
        )

    # Verify that the IntegrityError is specifically classified as an identity uniqueness conflict
    assert is_risk_identity_conflict(excinfo.value) is True

    # Verify session is still valid (savepoint rolled back) and can query
    existing = await repo.get_by_identity(
        session=async_session,
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="a" * 64,
    )
    assert existing is not None
    assert existing.id == analysis_1.id


@pytest.mark.asyncio
async def test_risk_repository_get_latest_ordering(
    async_session: AsyncSession,
) -> None:
    """Verify get_latest_for_transaction returns newest record by created_at DESC, id DESC."""
    _, tx, model = await _seed_prerequisites(async_session)
    repo = RiskRepository()

    # Analysis 1: v1.0
    a1 = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="1" * 64,
        score=Decimal("30.00"),
        risk_level="MEDIUM",
        ml_anomaly_score=0.05,
        ml_threshold=0.12,
        normalized_ml_score=30.0,
        rule_score=30.0,
        normalization_params={"method": "piecewise_linear"},
    )
    await repo.save_atomic(
        session=async_session,
        analysis=a1,
        factors=[],
    )
    await async_session.commit()

    # Analysis 2: v2.0 (later)
    a2 = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v2.0",
        feature_vector_hash="2" * 64,
        score=Decimal("80.00"),
        risk_level="CRITICAL",
        ml_anomaly_score=0.55,
        ml_threshold=0.12,
        normalized_ml_score=80.0,
        rule_score=80.0,
        normalization_params={"method": "piecewise_linear"},
    )
    await repo.save_atomic(
        session=async_session,
        analysis=a2,
        factors=[],
    )
    await async_session.commit()

    latest = await repo.get_latest_for_transaction(async_session, tx.id)
    assert latest is not None
    assert latest.id == a2.id
    assert latest.config_version == "risk_v2.0"
    assert latest.risk_level == "CRITICAL"


@pytest.mark.asyncio
async def test_historical_analysis_retrievable_when_model_retired(
    async_session: AsyncSession,
) -> None:
    """Verify an existing risk analysis remains retrievable even if its model is RETIRED."""
    _, tx, model = await _seed_prerequisites(async_session)
    repo = RiskRepository()

    analysis = RiskAnalysis(
        id=uuid.uuid4(),
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="3" * 64,
        score=Decimal("20.00"),
        risk_level="LOW",
        ml_anomaly_score=-0.10,
        ml_threshold=0.12,
        normalized_ml_score=20.0,
        rule_score=20.0,
        normalization_params={"method": "piecewise_linear"},
    )
    await repo.save_atomic(
        session=async_session,
        analysis=analysis,
        factors=[],
    )
    await async_session.commit()

    # Retire model
    model.status = "RETIRED"
    await async_session.flush()
    await async_session.commit()

    # Fetch latest risk analysis
    retrieved = await repo.get_latest_for_transaction(async_session, tx.id)
    assert retrieved is not None
    assert retrieved.id == analysis.id
    assert retrieved.model_version.status == "RETIRED"


@pytest.mark.asyncio
async def test_foreign_key_delete_semantics(
    async_session: AsyncSession,
) -> None:
    """Verify FK constraints: cannot delete model (RESTRICT), deleting analysis cascades to factors."""
    _, tx, model = await _seed_prerequisites(async_session)
    repo = RiskRepository()

    analysis_id = uuid.uuid4()
    analysis = RiskAnalysis(
        id=analysis_id,
        transaction_id=tx.id,
        model_version_id=model.id,
        config_version="risk_v1.0",
        feature_vector_hash="4" * 64,
        score=Decimal("50.00"),
        risk_level="HIGH",
        ml_anomaly_score=0.12,
        ml_threshold=0.12,
        normalized_ml_score=50.0,
        rule_score=50.0,
        normalization_params={"method": "piecewise_linear"},
    )
    factor = RiskFactor(
        id=uuid.uuid4(),
        risk_analysis_id=analysis_id,
        factor_code="UNUSUAL_TIME",
        factor_label="Unusual Time",
        severity="LOW",
        description="Off-peak transaction",
    )
    await repo.save_atomic(
        session=async_session,
        analysis=analysis,
        factors=[factor],
    )
    await async_session.commit()

    # Attempt to delete referenced ModelVersion should fail due to RESTRICT
    with pytest.raises(IntegrityError) as fk_exc:
        await async_session.delete(model)
        await async_session.flush()
    assert is_risk_identity_conflict(fk_exc.value) is False
    await async_session.rollback()

    # Deleting risk analysis cascades and removes its factors
    analysis_to_delete = await repo.get_by_id(async_session, analysis_id)
    assert analysis_to_delete is not None
    await async_session.delete(analysis_to_delete)
    await async_session.commit()

    # Verify factors are cascaded away
    res = await async_session.execute(
        text("SELECT COUNT(*) FROM risk_factors WHERE risk_analysis_id = :id"),
        {"id": analysis_id},
    )
    assert res.scalar() == 0


def test_is_risk_identity_conflict_driver_metadata_unit() -> None:
    """Unit test for is_risk_identity_conflict across various driver exception shapes."""

    class MockAsyncpgOrig(Exception):
        sqlstate: str | None = "23505"
        constraint_name: str | None = "uq_risk_analyses_identity"

    class MockDBAPIWrappedUnique(Exception):
        sqlstate: str | None = "23505"
        constraint_name: str | None = None
        orig: Exception = MockAsyncpgOrig()

    class MockOtherUniqueOrig(Exception):
        sqlstate: str | None = "23505"
        constraint_name: str | None = "uq_other_table_unique"

    class MockCheckViolationOrig(Exception):
        sqlstate: str | None = "23514"
        constraint_name: str | None = "chk_risk_analyses_score"

    class MockFKViolationOrig(Exception):
        sqlstate: str | None = "23503"
        constraint_name: str | None = "fk_transactions_id"

    class MockIncompleteOrig(Exception):
        sqlstate: str | None = None
        constraint_name: str | None = None

    class MockConstraintOnlyNoSQLState(Exception):
        sqlstate: str | None = None
        constraint_name: str | None = "uq_risk_analyses_identity"

    # 1. Matching direct asyncpg unique violation -> True
    e_match = IntegrityError("stmt", "params", MockAsyncpgOrig())
    assert is_risk_identity_conflict(e_match) is True

    # 2. Matching DBAPI-wrapped asyncpg unique violation (nested orig) -> True
    e_nested_match = IntegrityError("stmt", "params", MockDBAPIWrappedUnique())
    assert is_risk_identity_conflict(e_nested_match) is True

    # 3. Constraint name present but SQLSTATE missing -> False (fails closed)
    e_no_sqlstate = IntegrityError("stmt", "params", MockConstraintOnlyNoSQLState())
    assert is_risk_identity_conflict(e_no_sqlstate) is False

    # 4. Other unique constraint violation -> False
    e_other_uq = IntegrityError("stmt", "params", MockOtherUniqueOrig())
    assert is_risk_identity_conflict(e_other_uq) is False

    # 5. Check constraint violation -> False
    e_check = IntegrityError("stmt", "params", MockCheckViolationOrig())
    assert is_risk_identity_conflict(e_check) is False

    # 6. Foreign key violation -> False
    e_fk = IntegrityError("stmt", "params", MockFKViolationOrig())
    assert is_risk_identity_conflict(e_fk) is False

    # 7. Incomplete driver metadata -> False (fails closed)
    e_incomplete = IntegrityError("stmt", "params", MockIncompleteOrig())
    assert is_risk_identity_conflict(e_incomplete) is False

    # 8. Missing orig altogether -> False (fails closed)
    e_no_orig = IntegrityError("uq_risk_analyses_identity 23505", "params", Exception())
    e_no_orig.orig = None
    assert is_risk_identity_conflict(e_no_orig) is False
