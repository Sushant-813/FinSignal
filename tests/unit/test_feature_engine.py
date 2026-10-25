"""Unit tests for Phase 6 pure feature computation engine and mathematical invariants."""

import math
import statistics
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from finsignal.features.constants import (
    VELOCITY_WINDOW_5M_SECONDS,
)
from finsignal.features.engine import build_feature_metadata, compute_feature_vector
from finsignal.features.schemas import (
    AccountProfileDTO,
    EvaluatedTransactionDTO,
    EvaluationContext,
    HistoricalTransactionDTO,
)


def _make_account(
    account_id: uuid.UUID | None = None,
    home_location_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> AccountProfileDTO:
    return AccountProfileDTO(
        id=account_id or uuid.uuid4(),
        source_namespace="SYNTHETIC",
        home_location_id=home_location_id or uuid.uuid4(),
        created_at=created_at or datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )


def _make_eval_tx(
    account_id: uuid.UUID,
    occurred_at: datetime | None = None,
    amount: Decimal = Decimal("500.00"),
    currency: str = "INR",
    direction: str = "DEBIT",
    tx_id: uuid.UUID | None = None,
    merchant_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    category: str | None = "GROCERIES",
) -> EvaluatedTransactionDTO:
    return EvaluatedTransactionDTO(
        id=tx_id or uuid.uuid4(),
        account_id=account_id,
        occurred_at=occurred_at or datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
        amount=amount,
        currency=currency,
        direction=direction,
        transaction_type="PURCHASE",
        source_namespace="SYNTHETIC",
        merchant_id=merchant_id,
        device_id=device_id,
        location_id=location_id,
        category=category,
    )


def _make_hist_tx(
    occurred_at: datetime,
    amount: Decimal,
    currency: str = "INR",
    direction: str = "DEBIT",
    tx_id: uuid.UUID | None = None,
    merchant_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    category: str | None = "GROCERIES",
) -> HistoricalTransactionDTO:
    return HistoricalTransactionDTO(
        id=tx_id or uuid.uuid4(),
        occurred_at=occurred_at,
        amount=amount,
        currency=currency,
        direction=direction,
        transaction_type="PURCHASE",
        merchant_id=merchant_id,
        device_id=device_id,
        location_id=location_id,
        category=category,
    )


def test_amount_and_account_age_features() -> None:
    """Verify amount, log transform, and dynamic point-in-time account age."""
    acc_created = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    acc = _make_account(created_at=acc_created)
    eval_t = datetime(2026, 2, 15, 12, 0, 0, tzinfo=UTC)  # 45.5 days later
    eval_tx = _make_eval_tx(acc.id, occurred_at=eval_t, amount=Decimal("100.00"))

    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=[],
    )
    vec = compute_feature_vector(ctx)
    meta = build_feature_metadata(ctx)

    assert vec.amount == 100.0
    assert math.isclose(vec.amount_log, math.log1p(100.0), rel_tol=1e-6)
    assert math.isclose(vec.account_age_days, 45.5, rel_tol=1e-5)
    assert meta.is_account_created_after_txn is False


def test_negative_account_age_clamping_and_metadata_flag() -> None:
    """Verify that transactions occurring before account persistence clamp to 0.0 without triggering cold start."""
    acc_created = datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)
    acc = _make_account(created_at=acc_created)
    # Historical transaction occurring before the account was persisted in DB
    eval_t = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    eval_tx = _make_eval_tx(acc.id, occurred_at=eval_t, amount=Decimal("200.00"))

    # Supply 5 historical transactions so the account has sufficient history
    hist = [
        _make_hist_tx(
            eval_t - timedelta(hours=i),
            Decimal("150.00"),
        )
        for i in range(1, 6)
    ]

    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=hist,
    )
    vec = compute_feature_vector(ctx)
    meta = build_feature_metadata(ctx)

    assert vec.account_age_days == 0.0
    assert meta.is_account_created_after_txn is True
    # Cold start is determined strictly by transaction count, NOT account age!
    assert vec.is_cold_start == 0


def test_velocity_windows_and_boundary_inclusivity() -> None:
    """Verify 5m, 1h, 24h count and amount velocity including exact boundary test."""
    acc = _make_account()
    eval_t = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    eval_tx = _make_eval_tx(
        acc.id,
        occurred_at=eval_t,
        amount=Decimal("500.00"),
        direction="DEBIT",
        currency="INR",
    )

    # 1. Exactly on 5m lower boundary: eval_t - 300s (should be INCLUDED)
    tx_at_5m = _make_hist_tx(
        eval_t - timedelta(seconds=VELOCITY_WINDOW_5M_SECONDS),
        Decimal("100.00"),
    )
    # 2. Inside 5m: eval_t - 100s (INCLUDED)
    tx_in_5m = _make_hist_tx(eval_t - timedelta(seconds=100), Decimal("200.00"))
    # 3. Immediately outside 5m: eval_t - 301s (EXCLUDED from 5m, INCLUDED in 1h)
    tx_just_outside_5m = _make_hist_tx(
        eval_t - timedelta(seconds=301), Decimal("300.00")
    )
    # 4. Inside 1h but outside 5m: eval_t - 1800s (INCLUDED in 1h & 24h)
    tx_in_1h = _make_hist_tx(eval_t - timedelta(seconds=1800), Decimal("400.00"))
    # 5. Inside 24h but outside 1h: eval_t - 7200s (INCLUDED in 24h only)
    tx_in_24h = _make_hist_tx(eval_t - timedelta(seconds=7200), Decimal("500.00"))
    # 6. Outside 24h: eval_t - 90000s (EXCLUDED from all velocity windows)
    tx_outside_24h = _make_hist_tx(
        eval_t - timedelta(seconds=90000), Decimal("1000.00")
    )

    bounded = [
        tx_at_5m,
        tx_in_5m,
        tx_just_outside_5m,
        tx_in_1h,
        tx_in_24h,
        tx_outside_24h,
    ]
    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=bounded,
    )
    vec = compute_feature_vector(ctx)

    assert vec.velocity_5m_count == 2  # tx_at_5m and tx_in_5m
    assert vec.velocity_5m_amount == 300.0  # 100 + 200

    assert (
        vec.velocity_1h_count == 4
    )  # tx_at_5m, tx_in_5m, tx_just_outside_5m, tx_in_1h
    assert vec.velocity_1h_amount == 1000.0  # 100 + 200 + 300 + 400

    assert vec.velocity_24h_count == 5  # plus tx_in_24h
    assert vec.velocity_24h_amount == 1500.0  # 1000 + 500


def test_amount_deviation_sparse_history_sentinels() -> None:
    """Verify that histories with fewer than 3 observations return approved neutral sentinels."""
    acc = _make_account()
    eval_tx = _make_eval_tx(acc.id, amount=Decimal("1500.00"))

    # Only 2 historical observations
    hist = [
        _make_hist_tx(eval_tx.occurred_at - timedelta(hours=1), Decimal("1000.00")),
        _make_hist_tx(eval_tx.occurred_at - timedelta(hours=2), Decimal("1200.00")),
    ]

    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=hist,
    )
    vec = compute_feature_vector(ctx)

    assert vec.has_direction_baseline == 0
    assert vec.has_zero_variance_baseline == 0
    assert vec.amount_vs_mean_ratio == 1.0
    assert vec.amount_vs_median_ratio == 1.0
    assert vec.amount_zscore == 0.0
    assert vec.is_amount_different_from_constant_baseline == 0
    assert vec.is_cold_start == 1


def test_amount_deviation_with_sufficient_history() -> None:
    """Verify exact mean, median (including even-length), and sample standard deviation calculations."""
    acc = _make_account()
    eval_tx = _make_eval_tx(acc.id, amount=Decimal("3000.00"))

    # 4 historical observations: [1000, 2000, 3000, 4000]
    # mean = 2500.0
    # median for even count [1000, 2000, 3000, 4000] = (2000 + 3000) / 2 = 2500.0
    # sample variance = ((1000-2500)^2 + (2000-2500)^2 + (3000-2500)^2 + (4000-2500)^2) / 3
    #                 = (2250000 + 250000 + 250000 + 2250000) / 3 = 5000000 / 3 = 1666666.666...
    # stddev = sqrt(1666666.666...) ≈ 1290.9944487358
    # zscore = (3000 - 2500) / 1290.9944 ≈ 0.387298
    hist = [
        _make_hist_tx(eval_tx.occurred_at - timedelta(days=4), Decimal("1000.00")),
        _make_hist_tx(eval_tx.occurred_at - timedelta(days=3), Decimal("2000.00")),
        _make_hist_tx(eval_tx.occurred_at - timedelta(days=2), Decimal("3000.00")),
        _make_hist_tx(eval_tx.occurred_at - timedelta(days=1), Decimal("4000.00")),
    ]

    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=hist,
    )
    vec = compute_feature_vector(ctx)

    assert vec.has_direction_baseline == 1
    assert vec.has_zero_variance_baseline == 0
    assert math.isclose(vec.amount_vs_mean_ratio, 3000.0 / 2500.0, rel_tol=1e-5)
    assert math.isclose(vec.amount_vs_median_ratio, 3000.0 / 2500.0, rel_tol=1e-5)
    expected_std = statistics.stdev([1000.0, 2000.0, 3000.0, 4000.0])
    expected_z = (3000.0 - 2500.0) / expected_std
    assert math.isclose(vec.amount_zscore, expected_z, rel_tol=1e-5)
    assert vec.is_amount_different_from_constant_baseline == 0
    assert vec.is_cold_start == 0


def test_zero_variance_baseline_semantics() -> None:
    """Verify that invariant history sets has_zero_variance_baseline and detects constant baseline differences."""
    acc = _make_account()
    # Case 1: Invariant history of 4 debits of ₹500, current transaction ₹500
    eval_tx_equal = _make_eval_tx(acc.id, amount=Decimal("500.00"))
    hist = [
        _make_hist_tx(eval_tx_equal.occurred_at - timedelta(days=i), Decimal("500.00"))
        for i in range(1, 5)
    ]
    ctx_equal = EvaluationContext(
        evaluated_transaction=eval_tx_equal,
        account_profile=acc,
        bounded_transactions=hist,
    )
    vec_equal = compute_feature_vector(ctx_equal)

    assert vec_equal.has_direction_baseline == 1
    assert vec_equal.has_zero_variance_baseline == 1
    assert vec_equal.amount_zscore == 0.0
    assert vec_equal.amount_vs_mean_ratio == 1.0
    assert vec_equal.is_amount_different_from_constant_baseline == 0

    # Case 2: Invariant history of 4 debits of ₹500, current transaction ₹2500 (anomaly!)
    eval_tx_diff = _make_eval_tx(acc.id, amount=Decimal("2500.00"))
    ctx_diff = EvaluationContext(
        evaluated_transaction=eval_tx_diff,
        account_profile=acc,
        bounded_transactions=hist,
    )
    vec_diff = compute_feature_vector(ctx_diff)

    assert vec_diff.has_direction_baseline == 1
    assert vec_diff.has_zero_variance_baseline == 1
    # Z-score must remain neutral sentinel 0.0 to prevent division by zero or arbitrary numbers
    assert vec_diff.amount_zscore == 0.0
    assert vec_diff.amount_vs_mean_ratio == 5.0
    # Preserves anomaly signal through dedicated feature
    assert vec_diff.is_amount_different_from_constant_baseline == 1


def test_direction_and_currency_isolation() -> None:
    """Verify that Credit transactions and different currencies do not cross-pollute Debit baselines."""
    acc = _make_account()
    eval_tx = _make_eval_tx(
        acc.id, amount=Decimal("1000.00"), currency="INR", direction="DEBIT"
    )

    # Historical: 5 CREDITs in INR (salary), and 5 DEBITs in USD
    hist = [
        _make_hist_tx(
            eval_tx.occurred_at - timedelta(days=i),
            Decimal("50000.00"),
            currency="INR",
            direction="CREDIT",
        )
        for i in range(1, 6)
    ] + [
        _make_hist_tx(
            eval_tx.occurred_at - timedelta(days=i),
            Decimal("50.00"),
            currency="USD",
            direction="DEBIT",
        )
        for i in range(1, 6)
    ]

    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=hist,
    )
    vec = compute_feature_vector(ctx)

    # Account has 10 prior transactions overall, so is_cold_start is 0
    assert vec.is_cold_start == 0
    # But 0 historical DEBITs in INR, so has_direction_baseline is 0!
    assert vec.has_direction_baseline == 0
    assert vec.amount_vs_mean_ratio == 1.0
    assert vec.amount_zscore == 0.0
    assert vec.velocity_24h_amount == 0.00  # Currency & direction isolated


def test_entity_familiarity_and_sentinel_contract() -> None:
    """Verify device, merchant, location novelty and familiarity counts."""
    home_loc = uuid.uuid4()
    seen_loc = uuid.uuid4()
    new_loc = uuid.uuid4()

    seen_dev = uuid.uuid4()
    new_dev = uuid.uuid4()

    seen_merch = uuid.uuid4()
    new_merch = uuid.uuid4()

    acc = _make_account(home_location_id=home_loc)
    eval_t = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    hist = [
        _make_hist_tx(
            eval_t - timedelta(days=i),
            Decimal("500.00"),
            merchant_id=seen_merch,
            device_id=seen_dev,
            location_id=seen_loc,
        )
        for i in range(1, 4)
    ]

    # Test 1: Evaluated tx uses seen entities and home location
    eval_tx_known = _make_eval_tx(
        acc.id,
        occurred_at=eval_t,
        device_id=seen_dev,
        merchant_id=seen_merch,
        location_id=home_loc,
    )
    vec_known = compute_feature_vector(
        EvaluationContext(
            evaluated_transaction=eval_tx_known,
            account_profile=acc,
            bounded_transactions=hist,
        )
    )

    assert vec_known.has_device == 1
    assert vec_known.is_new_device == 0
    assert vec_known.device_tx_count == 3

    assert vec_known.has_merchant == 1
    assert vec_known.is_new_merchant == 0
    assert vec_known.merchant_tx_count == 3

    assert vec_known.has_location == 1
    assert vec_known.is_home_location == 1
    assert vec_known.is_new_location == 0
    assert vec_known.location_tx_count == 0  # First time at home location

    # Test 2: Evaluated tx uses brand new entities
    eval_tx_new = _make_eval_tx(
        acc.id,
        occurred_at=eval_t,
        device_id=new_dev,
        merchant_id=new_merch,
        location_id=new_loc,
    )
    vec_new = compute_feature_vector(
        EvaluationContext(
            evaluated_transaction=eval_tx_new,
            account_profile=acc,
            bounded_transactions=hist,
        )
    )

    assert vec_new.is_new_device == 1
    assert vec_new.device_tx_count == 0
    assert vec_new.is_new_merchant == 1
    assert vec_new.merchant_tx_count == 0
    assert vec_new.is_home_location == 0
    assert vec_new.is_new_location == 1
    assert vec_new.location_tx_count == 0
    assert vec_new.location_frequency == 0.0

    # Test 3: Missing entity identifiers (NULLs) must return approved 0 sentinels
    eval_tx_nulls = _make_eval_tx(
        acc.id,
        occurred_at=eval_t,
        device_id=None,
        merchant_id=None,
        location_id=None,
        category=None,
    )
    vec_nulls = compute_feature_vector(
        EvaluationContext(
            evaluated_transaction=eval_tx_nulls,
            account_profile=acc,
            bounded_transactions=hist,
        )
    )

    assert vec_nulls.has_device == 0
    assert vec_nulls.is_new_device == 0
    assert vec_nulls.device_tx_count == 0

    assert vec_nulls.has_merchant == 0
    assert vec_nulls.is_new_merchant == 0
    assert vec_nulls.merchant_tx_count == 0

    assert vec_nulls.has_location == 0
    assert vec_nulls.is_home_location == 0
    assert vec_nulls.is_new_location == 0
    assert vec_nulls.location_frequency == 0.0

    assert vec_nulls.has_category == 0
    assert vec_nulls.is_new_category == 0
    assert vec_nulls.category_spend_share_30d == 0.0


def test_category_spend_share_30d_semantics() -> None:
    """Verify category novelty and spend share over 30d debit spending."""
    acc = _make_account()
    eval_t = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
    eval_tx = _make_eval_tx(
        acc.id,
        occurred_at=eval_t,
        category="TRAVEL",
        direction="DEBIT",
        currency="INR",
    )

    # In preceding 30 days:
    # 2 DEBITs in GROCERIES: ₹600.00
    # 2 DEBITs in TRAVEL: ₹400.00
    # Total 30d DEBIT spend in INR = ₹1000.00
    # Numerator (TRAVEL) = ₹400.00
    # Share = 400.0 / 1000.0 = 0.40
    hist = [
        _make_hist_tx(
            eval_t - timedelta(days=5),
            Decimal("300.00"),
            category="GROCERIES",
            direction="DEBIT",
        ),
        _make_hist_tx(
            eval_t - timedelta(days=10),
            Decimal("300.00"),
            category="GROCERIES",
            direction="DEBIT",
        ),
        _make_hist_tx(
            eval_t - timedelta(days=15),
            Decimal("200.00"),
            category="TRAVEL",
            direction="DEBIT",
        ),
        _make_hist_tx(
            eval_t - timedelta(days=20),
            Decimal("200.00"),
            category="TRAVEL",
            direction="DEBIT",
        ),
        # Credit transaction (must be excluded from debit denominator):
        _make_hist_tx(
            eval_t - timedelta(days=25),
            Decimal("50000.00"),
            category="TRAVEL",
            direction="CREDIT",
        ),
    ]

    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=hist,
    )
    vec = compute_feature_vector(ctx)

    assert vec.has_category == 1
    assert vec.is_new_category == 0  # Travel was previously seen
    assert math.isclose(vec.category_spend_share_30d, 0.40, rel_tol=1e-5)


def test_temporal_utc_features() -> None:
    """Verify UTC hour, day of week, weekend indicator, and nocturnal unusual hour."""
    acc = _make_account()

    # Case 1: Sunday at 03:30 AM UTC (Weekend and Nocturnal)
    sunday_night = datetime(2026, 3, 1, 3, 30, 0, tzinfo=UTC)  # 2026-03-01 is Sunday
    eval_tx1 = _make_eval_tx(acc.id, occurred_at=sunday_night)
    vec1 = compute_feature_vector(
        EvaluationContext(eval_tx1, acc, bounded_transactions=[])
    )

    assert vec1.hour_of_day == 3
    assert vec1.day_of_week == 6  # Sunday is 6
    assert vec1.is_weekend == 1
    assert vec1.is_unusual_hour == 1

    # Case 2: Wednesday at 14:00 PM UTC (Weekday daytime)
    wed_afternoon = datetime(
        2026, 3, 4, 14, 0, 0, tzinfo=UTC
    )  # 2026-03-04 is Wednesday
    eval_tx2 = _make_eval_tx(acc.id, occurred_at=wed_afternoon)
    vec2 = compute_feature_vector(
        EvaluationContext(eval_tx2, acc, bounded_transactions=[])
    )

    assert vec2.hour_of_day == 14
    assert vec2.day_of_week == 2  # Wednesday is 2
    assert vec2.is_weekend == 0
    assert vec2.is_unusual_hour == 0


def test_self_exclusion_and_same_timestamp_uuid_ordering() -> None:
    """Verify strict self-exclusion and sub-second UUID total ordering."""
    acc = _make_account()
    same_t = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    # Create three UUIDs with known integer ordering
    id_low = uuid.UUID("00000000-0000-0000-0000-000000000001")
    id_eval = uuid.UUID("00000000-0000-0000-0000-000000000002")
    id_high = uuid.UUID("00000000-0000-0000-0000-000000000003")

    eval_tx = _make_eval_tx(
        acc.id, occurred_at=same_t, tx_id=id_eval, amount=Decimal("500.00")
    )

    hist_low = _make_hist_tx(same_t, Decimal("100.00"), tx_id=id_low)
    # The evaluated transaction itself erroneously passed in the candidate list:
    hist_self = _make_hist_tx(same_t, Decimal("500.00"), tx_id=id_eval)
    hist_high = _make_hist_tx(same_t, Decimal("300.00"), tx_id=id_high)

    bounded = [hist_low, hist_self, hist_high]

    ctx = EvaluationContext(
        evaluated_transaction=eval_tx,
        account_profile=acc,
        bounded_transactions=bounded,
    )
    vec = compute_feature_vector(ctx)

    # Only hist_low has occurred_at == eval_t AND id < id_eval!
    # hist_self and hist_high must be strictly excluded.
    assert vec.velocity_5m_count == 1
    assert vec.velocity_5m_amount == 100.0
