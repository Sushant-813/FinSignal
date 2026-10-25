"""Integration tests demonstrating temporal leakage prevention, future invariance, and ground-truth isolation."""

import math
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.features.schemas import (
    AccountProfileDTO,
    EvaluatedTransactionDTO,
    FeatureVector,
)
from finsignal.features.service import FeatureService
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
                    "TRUNCATE TABLE transactions, account_devices, accounts, "
                    "merchants, devices, locations CASCADE;"
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_online_future_data_invariance(async_session: AsyncSession) -> None:
    """Verify that adding future transactions never changes the feature vector of an earlier transaction."""
    acc = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id=f"ACC_{uuid.uuid4().hex[:6]}",
        account_type="CHECKING",
        status="ACTIVE",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    async_session.add(acc)
    await async_session.commit()

    t0 = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    # 1. Seed 5 initial transactions
    tx_models: list[Transaction] = []
    for i in range(1, 6):
        tx = Transaction(
            id=uuid.uuid4(),
            source_namespace=acc.source_namespace,
            external_transaction_id=f"TXN_INIT_{i:04d}",
            account_id=acc.id,
            amount=Decimal(str(100.0 * i)),
            direction="DEBIT",
            currency="INR",
            occurred_at=t0 + timedelta(hours=i),
            category="FOOD",
            transaction_type="PURCHASE",
        )
        async_session.add(tx)
        tx_models.append(tx)
    await async_session.commit()

    t5 = tx_models[-1]
    service = FeatureService()

    # 2. Evaluate T5 before future records exist
    res_before = await service.evaluate_transaction(async_session, t5.id)
    vec_before = res_before.features

    # 3. Inject 50 future transactions with massive amounts, bursts, and nocturnal hours
    future_start = t5.occurred_at + timedelta(minutes=5)
    for j in range(1, 51):
        future_tx = Transaction(
            id=uuid.uuid4(),
            source_namespace=acc.source_namespace,
            external_transaction_id=f"TXN_FUT_{j:04d}",
            account_id=acc.id,
            amount=Decimal("999999.00"),  # Massive drain amount
            direction="DEBIT",
            currency="INR",
            occurred_at=future_start + timedelta(seconds=j * 10),  # Rapid burst
            category="LUXURY",
            transaction_type="PURCHASE",
        )
        async_session.add(future_tx)
    await async_session.commit()

    # 4. Re-evaluate T5 after future records exist
    res_after = await service.evaluate_transaction(async_session, t5.id)
    vec_after = res_after.features

    # 5. Assert 100% invariance
    # Categorical & integer features must be bit-identical
    assert vec_before.velocity_5m_count == vec_after.velocity_5m_count
    assert vec_before.velocity_1h_count == vec_after.velocity_1h_count
    assert vec_before.velocity_24h_count == vec_after.velocity_24h_count
    assert vec_before.has_direction_baseline == vec_after.has_direction_baseline
    assert vec_before.has_zero_variance_baseline == vec_after.has_zero_variance_baseline
    assert vec_before.is_cold_start == vec_after.is_cold_start
    assert vec_before.is_new_device == vec_after.is_new_device
    assert vec_before.is_new_merchant == vec_after.is_new_merchant
    assert vec_before.is_new_location == vec_after.is_new_location
    assert vec_before.is_new_category == vec_after.is_new_category
    assert vec_before.hour_of_day == vec_after.hour_of_day
    assert vec_before.day_of_week == vec_after.day_of_week
    assert vec_before.is_weekend == vec_after.is_weekend
    assert vec_before.is_unusual_hour == vec_after.is_unusual_hour

    # Continuous floating-point features must match within numerical tolerance
    assert math.isclose(vec_before.amount, vec_after.amount, rel_tol=1e-5)
    assert math.isclose(vec_before.amount_log, vec_after.amount_log, rel_tol=1e-5)
    assert math.isclose(
        vec_before.account_age_days, vec_after.account_age_days, rel_tol=1e-5
    )
    assert math.isclose(
        vec_before.velocity_5m_amount, vec_after.velocity_5m_amount, rel_tol=1e-5
    )
    assert math.isclose(
        vec_before.velocity_1h_amount, vec_after.velocity_1h_amount, rel_tol=1e-5
    )
    assert math.isclose(
        vec_before.velocity_24h_amount, vec_after.velocity_24h_amount, rel_tol=1e-5
    )
    assert math.isclose(
        vec_before.amount_vs_mean_ratio, vec_after.amount_vs_mean_ratio, rel_tol=1e-5
    )
    assert math.isclose(
        vec_before.amount_vs_median_ratio,
        vec_after.amount_vs_median_ratio,
        rel_tol=1e-5,
    )
    assert math.isclose(
        vec_before.amount_zscore, vec_after.amount_zscore, rel_tol=1e-5, abs_tol=1e-5
    )
    assert math.isclose(
        vec_before.location_frequency, vec_after.location_frequency, rel_tol=1e-5
    )
    assert math.isclose(
        vec_before.category_spend_share_30d,
        vec_after.category_spend_share_30d,
        rel_tol=1e-5,
    )


def test_batch_future_data_invariance() -> None:
    """Verify that batch extraction also guarantees future-data invariance for earlier transactions."""
    acc_id = uuid.uuid4()
    acc = AccountProfileDTO(
        id=acc_id,
        source_namespace="SYNTHETIC",
        home_location_id=uuid.uuid4(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    t0 = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    # Initial 5 transactions
    base_txs = [
        EvaluatedTransactionDTO(
            id=uuid.uuid4(),
            account_id=acc_id,
            occurred_at=t0 + timedelta(hours=i),
            amount=Decimal(str(100.0 * i)),
            currency="INR",
            direction="DEBIT",
            transaction_type="PURCHASE",
        )
        for i in range(1, 6)
    ]

    service = FeatureService()
    # Batch run 1: only base_txs
    results_base = service.extract_batch(base_txs, {acc_id: acc})
    vec_t5_base = results_base[4].features

    # Future 50 transactions
    future_start = base_txs[-1].occurred_at + timedelta(minutes=1)
    future_txs = [
        EvaluatedTransactionDTO(
            id=uuid.uuid4(),
            account_id=acc_id,
            occurred_at=future_start + timedelta(minutes=j),
            amount=Decimal("50000.00"),
            currency="INR",
            direction="DEBIT",
            transaction_type="PURCHASE",
        )
        for j in range(1, 51)
    ]

    # Batch run 2: base_txs + future_txs
    combined = list(base_txs) + future_txs
    results_combined = service.extract_batch(combined, {acc_id: acc})
    vec_t5_combined = results_combined[4].features

    # Assert that features for T5 in the combined batch exactly match the baseline batch
    assert vec_t5_base == vec_t5_combined


def test_ground_truth_isolation() -> None:
    """Verify that synthetic ground-truth attributes cannot be consumed by FeatureVector."""
    # Ensure no scenario columns exist on FeatureVector
    fields = FeatureVector.model_fields
    assert "is_fraud" not in fields
    assert "fraud_scenario" not in fields
    assert "scenario_instance_id" not in fields
