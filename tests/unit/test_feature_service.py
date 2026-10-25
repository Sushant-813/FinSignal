"""Unit tests for FeatureService: batch extraction, equivalence, and state isolation."""

import math
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from finsignal.features.engine import compute_feature_vector
from finsignal.features.schemas import (
    AccountProfileDTO,
    EvaluatedTransactionDTO,
    EvaluationContext,
    HistoricalTransactionDTO,
)
from finsignal.features.service import FeatureService


def test_batch_extraction_does_not_mutate_input_and_preserves_order() -> None:
    """Verify that batch extraction does not mutate input collection and preserves input ordering."""
    acc_id = uuid.uuid4()
    acc = AccountProfileDTO(
        id=acc_id,
        source_namespace="SYNTHETIC",
        home_location_id=uuid.uuid4(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    t0 = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    # Deliberately out of chronological order
    tx3 = EvaluatedTransactionDTO(
        id=uuid.uuid4(),
        account_id=acc_id,
        occurred_at=t0 + timedelta(hours=3),
        amount=Decimal("300.00"),
        currency="INR",
        direction="DEBIT",
        transaction_type="PURCHASE",
    )
    tx1 = EvaluatedTransactionDTO(
        id=uuid.uuid4(),
        account_id=acc_id,
        occurred_at=t0 + timedelta(hours=1),
        amount=Decimal("100.00"),
        currency="INR",
        direction="DEBIT",
        transaction_type="PURCHASE",
    )
    tx2 = EvaluatedTransactionDTO(
        id=uuid.uuid4(),
        account_id=acc_id,
        occurred_at=t0 + timedelta(hours=2),
        amount=Decimal("200.00"),
        currency="INR",
        direction="DEBIT",
        transaction_type="PURCHASE",
    )

    input_list = [tx3, tx1, tx2]
    original_copy = list(input_list)

    service = FeatureService()
    results = service.extract_batch(input_list, {acc_id: acc})

    # Assert input list was NOT mutated
    assert input_list == original_copy

    # Assert results match the original input list order
    assert len(results) == 3
    assert results[0].metadata.transaction_id == tx3.id
    assert results[1].metadata.transaction_id == tx1.id
    assert results[2].metadata.transaction_id == tx2.id

    # Check point-in-time correctness for tx1 (evaluated first chronologically)
    res_tx1 = results[1]
    assert res_tx1.features.is_cold_start == 1  # 0 prior txs
    assert res_tx1.features.velocity_1h_count == 0

    # Check tx2 (has tx1 in history)
    res_tx2 = results[2]
    assert res_tx2.features.velocity_1h_count == 1
    assert res_tx2.features.velocity_1h_amount == 100.0

    # Check tx3 (has tx1 and tx2 in history)
    res_tx3 = results[0]
    assert res_tx3.features.velocity_24h_count == 2
    assert res_tx3.features.velocity_24h_amount == 300.0  # 100 + 200


def test_batch_versus_pure_engine_numerical_equivalence() -> None:
    """Verify that batch extraction produces numerical agreement within tolerance to pure engine evaluations."""
    acc_id = uuid.uuid4()
    loc_home = uuid.uuid4()
    merch1 = uuid.uuid4()
    dev1 = uuid.uuid4()

    acc = AccountProfileDTO(
        id=acc_id,
        source_namespace="SYNTHETIC",
        home_location_id=loc_home,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    t0 = datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC)
    amounts = [
        Decimal("100.00"),
        Decimal("250.00"),
        Decimal("500.00"),
        Decimal("150.00"),
        Decimal("800.00"),
        Decimal("300.00"),
        Decimal("1200.00"),
        Decimal("450.00"),
    ]

    transactions: list[EvaluatedTransactionDTO] = []
    for i, amt in enumerate(amounts):
        tx = EvaluatedTransactionDTO(
            id=uuid.uuid4(),
            account_id=acc_id,
            occurred_at=t0 + timedelta(days=i),
            amount=amt,
            currency="INR",
            direction="DEBIT",
            transaction_type="PURCHASE",
            merchant_id=merch1,
            device_id=dev1,
            location_id=loc_home,
            category="RETAIL",
        )
        transactions.append(tx)

    # 1. Extract via batch service
    service = FeatureService()
    batch_results = service.extract_batch(transactions, {acc_id: acc})

    # 2. Extract each transaction individually using pure engine on full historical slice
    for i, eval_tx in enumerate(transactions):
        prior_history = [
            HistoricalTransactionDTO(
                id=tx.id,
                occurred_at=tx.occurred_at,
                amount=tx.amount,
                currency=tx.currency,
                direction=tx.direction,
                transaction_type=tx.transaction_type,
                merchant_id=tx.merchant_id,
                device_id=tx.device_id,
                location_id=tx.location_id,
                category=tx.category,
            )
            for tx in transactions[:i]
        ]

        pure_ctx = EvaluationContext(
            evaluated_transaction=eval_tx,
            account_profile=acc,
            bounded_transactions=prior_history,
        )
        pure_vector = compute_feature_vector(pure_ctx)
        batch_vector = batch_results[i].features

        # Assert exact equality for all integer and binary flags
        assert pure_vector.has_direction_baseline == batch_vector.has_direction_baseline
        assert (
            pure_vector.has_zero_variance_baseline
            == batch_vector.has_zero_variance_baseline
        )
        assert pure_vector.is_cold_start == batch_vector.is_cold_start
        assert (
            pure_vector.is_amount_different_from_constant_baseline
            == batch_vector.is_amount_different_from_constant_baseline
        )
        assert pure_vector.velocity_5m_count == batch_vector.velocity_5m_count
        assert pure_vector.velocity_1h_count == batch_vector.velocity_1h_count
        assert pure_vector.velocity_24h_count == batch_vector.velocity_24h_count
        assert pure_vector.has_device == batch_vector.has_device
        assert pure_vector.is_new_device == batch_vector.is_new_device
        assert pure_vector.device_tx_count == batch_vector.device_tx_count
        assert pure_vector.has_merchant == batch_vector.has_merchant
        assert pure_vector.is_new_merchant == batch_vector.is_new_merchant
        assert pure_vector.merchant_tx_count == batch_vector.merchant_tx_count
        assert pure_vector.has_location == batch_vector.has_location
        assert pure_vector.is_home_location == batch_vector.is_home_location
        assert pure_vector.is_new_location == batch_vector.is_new_location
        assert pure_vector.location_tx_count == batch_vector.location_tx_count
        assert pure_vector.has_category == batch_vector.has_category
        assert pure_vector.is_new_category == batch_vector.is_new_category
        assert pure_vector.hour_of_day == batch_vector.hour_of_day
        assert pure_vector.day_of_week == batch_vector.day_of_week
        assert pure_vector.is_weekend == batch_vector.is_weekend
        assert pure_vector.is_unusual_hour == batch_vector.is_unusual_hour

        # Assert justified numerical tolerance (1e-5) for floating-point outputs
        assert math.isclose(pure_vector.amount, batch_vector.amount, rel_tol=1e-5)
        assert math.isclose(
            pure_vector.amount_log, batch_vector.amount_log, rel_tol=1e-5
        )
        assert math.isclose(
            pure_vector.account_age_days, batch_vector.account_age_days, rel_tol=1e-5
        )
        assert math.isclose(
            pure_vector.amount_vs_mean_ratio,
            batch_vector.amount_vs_mean_ratio,
            rel_tol=1e-5,
        )
        assert math.isclose(
            pure_vector.amount_vs_median_ratio,
            batch_vector.amount_vs_median_ratio,
            rel_tol=1e-5,
        )
        assert math.isclose(
            pure_vector.amount_zscore,
            batch_vector.amount_zscore,
            rel_tol=1e-5,
            abs_tol=1e-5,
        )
        assert math.isclose(
            pure_vector.velocity_5m_amount,
            batch_vector.velocity_5m_amount,
            rel_tol=1e-5,
        )
        assert math.isclose(
            pure_vector.velocity_1h_amount,
            batch_vector.velocity_1h_amount,
            rel_tol=1e-5,
        )
        assert math.isclose(
            pure_vector.velocity_24h_amount,
            batch_vector.velocity_24h_amount,
            rel_tol=1e-5,
        )
        assert math.isclose(
            pure_vector.location_frequency,
            batch_vector.location_frequency,
            rel_tol=1e-5,
        )
        assert math.isclose(
            pure_vector.category_spend_share_30d,
            batch_vector.category_spend_share_30d,
            rel_tol=1e-5,
        )


def test_batch_extraction_independent_state_across_accounts() -> None:
    """Verify that multiple accounts processed in an interleaved batch maintain completely isolated state."""
    acc1_id = uuid.uuid4()
    acc2_id = uuid.uuid4()

    acc1 = AccountProfileDTO(
        id=acc1_id,
        source_namespace="SYNTHETIC",
        home_location_id=uuid.uuid4(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    acc2 = AccountProfileDTO(
        id=acc2_id,
        source_namespace="SYNTHETIC",
        home_location_id=uuid.uuid4(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    t0 = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

    # Interleaved transactions between Account 1 and Account 2
    # Account 1 transacts small amounts (₹100)
    # Account 2 transacts large amounts (₹50,000)
    txs = [
        EvaluatedTransactionDTO(
            id=uuid.uuid4(),
            account_id=acc1_id,
            occurred_at=t0 + timedelta(minutes=1),
            amount=Decimal("100.00"),
            currency="INR",
            direction="DEBIT",
            transaction_type="PURCHASE",
        ),
        EvaluatedTransactionDTO(
            id=uuid.uuid4(),
            account_id=acc2_id,
            occurred_at=t0 + timedelta(minutes=2),
            amount=Decimal("50000.00"),
            currency="INR",
            direction="DEBIT",
            transaction_type="PURCHASE",
        ),
        EvaluatedTransactionDTO(
            id=uuid.uuid4(),
            account_id=acc1_id,
            occurred_at=t0 + timedelta(minutes=3),
            amount=Decimal("100.00"),
            currency="INR",
            direction="DEBIT",
            transaction_type="PURCHASE",
        ),
        EvaluatedTransactionDTO(
            id=uuid.uuid4(),
            account_id=acc2_id,
            occurred_at=t0 + timedelta(minutes=4),
            amount=Decimal("50000.00"),
            currency="INR",
            direction="DEBIT",
            transaction_type="PURCHASE",
        ),
    ]

    service = FeatureService()
    results = service.extract_batch(txs, {acc1_id: acc1, acc2_id: acc2})

    # txs[2] is Account 1's 2nd transaction. It should have velocity count = 1 and amount = 100.0 (NOT 50100.0!)
    res_acc1_tx2 = results[2]
    assert res_acc1_tx2.features.velocity_5m_count == 1
    assert res_acc1_tx2.features.velocity_5m_amount == 100.0

    # txs[3] is Account 2's 2nd transaction. It should have velocity count = 1 and amount = 50000.0 (NOT 50100.0!)
    res_acc2_tx2 = results[3]
    assert res_acc2_tx2.features.velocity_5m_count == 1
    assert res_acc2_tx2.features.velocity_5m_amount == 50000.0
