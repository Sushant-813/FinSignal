"""Pure functional feature computation engine for FinSignal Phase 6.

Enforces:
- Point-in-time correctness: strictly uses transactions where
  occurred_at < eval.occurred_at OR (occurred_at == eval.occurred_at AND id < eval.id)
- Evaluated transaction is strictly excluded from its own baseline
- Mathematical purity: no database access, no mutation, finite float outputs
- Precision: Decimal arithmetic for monetary sums before float conversion
"""

import math
import statistics
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from finsignal.features.constants import (
    CATEGORY_WINDOW_30D_SECONDS,
    MIN_BASELINE_OBSERVATIONS,
    UNUSUAL_HOURS,
    VELOCITY_WINDOW_1H_SECONDS,
    VELOCITY_WINDOW_5M_SECONDS,
    VELOCITY_WINDOW_24H_SECONDS,
    WEEKEND_DAYS,
)
from finsignal.features.schemas import (
    EvaluationContext,
    FeatureMetadata,
    FeatureVector,
    HistoricalTransactionDTO,
)


def _to_utc(dt: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC datetime."""
    if dt.tzinfo is UTC:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def is_strictly_prior(
    tx: HistoricalTransactionDTO,
    eval_occurred_at: datetime,
    eval_id: uuid.UUID,
) -> bool:
    """Evaluate whether candidate transaction strictly precedes the evaluated transaction.

    Deterministic Total Ordering:
    occurred_at < eval_occurred_at OR (occurred_at == eval_occurred_at AND id < eval_id)
    """
    tx_t = _to_utc(tx.occurred_at)
    e_t = _to_utc(eval_occurred_at)
    if tx_t < e_t:
        return True
    if tx_t == e_t:
        return tx.id.int < eval_id.int
    return False


def compute_feature_vector(context: EvaluationContext) -> FeatureVector:
    """Compute the 34-feature vector purely from the provided evaluation context.

    Pure function: zero side effects, zero DB I/O, no mutation of domain entities.
    """
    eval_tx = context.evaluated_transaction
    account = context.account_profile
    eval_t = _to_utc(eval_tx.occurred_at)
    eval_id = eval_tx.id

    # Filter bounded transactions to strictly eligible historical records
    eligible_bounded = [
        tx
        for tx in context.bounded_transactions
        if is_strictly_prior(tx, eval_t, eval_id)
    ]

    # 1. Amount features
    amount_float = float(eval_tx.amount)
    amount_log = math.log1p(amount_float)

    # 2. Account profile features
    acc_created = _to_utc(account.created_at)
    age_seconds = (eval_t - acc_created).total_seconds()
    account_age_days = max(0.0, age_seconds / 86400.0)

    # 3. Velocity counts (all currencies, all directions)
    t_5m = eval_t - timedelta(seconds=VELOCITY_WINDOW_5M_SECONDS)
    t_1h = eval_t - timedelta(seconds=VELOCITY_WINDOW_1H_SECONDS)
    t_24h = eval_t - timedelta(seconds=VELOCITY_WINDOW_24H_SECONDS)

    v5m_txs = [tx for tx in eligible_bounded if _to_utc(tx.occurred_at) >= t_5m]
    v1h_txs = [tx for tx in eligible_bounded if _to_utc(tx.occurred_at) >= t_1h]
    v24h_txs = [tx for tx in eligible_bounded if _to_utc(tx.occurred_at) >= t_24h]

    velocity_5m_count = len(v5m_txs)
    velocity_1h_count = len(v1h_txs)
    velocity_24h_count = len(v24h_txs)

    # 4. Velocity amounts (direction-matched and currency-matched)
    v5m_amount_dec = sum(
        (
            tx.amount
            for tx in v5m_txs
            if tx.direction == eval_tx.direction and tx.currency == eval_tx.currency
        ),
        start=Decimal(0),
    )
    v1h_amount_dec = sum(
        (
            tx.amount
            for tx in v1h_txs
            if tx.direction == eval_tx.direction and tx.currency == eval_tx.currency
        ),
        start=Decimal(0),
    )
    v24h_amount_dec = sum(
        (
            tx.amount
            for tx in v24h_txs
            if tx.direction == eval_tx.direction and tx.currency == eval_tx.currency
        ),
        start=Decimal(0),
    )

    velocity_5m_amount = float(v5m_amount_dec)
    velocity_1h_amount = float(v1h_amount_dec)
    velocity_24h_amount = float(v24h_amount_dec)

    # 5. Amount deviation and baseline indicators
    # Check if a precomputed lifetime summary was provided
    if context.lifetime_summary is not None:
        summary = context.lifetime_summary
        hist_count = summary.count
        hist_mean = summary.mean
        hist_stddev = summary.stddev
        hist_median = summary.median
        total_hist_count = summary.total_lifetime_count
        seen_devices = summary.seen_devices
        seen_merchants = summary.seen_merchants
        seen_locations = summary.seen_locations
        seen_categories = summary.seen_categories
        device_tx_counts = summary.device_tx_counts
        merchant_tx_counts = summary.merchant_tx_counts
        location_tx_counts = summary.location_tx_counts
    else:
        # Full historical slice present in bounded_transactions
        matching_lifetime = [
            tx
            for tx in eligible_bounded
            if tx.direction == eval_tx.direction and tx.currency == eval_tx.currency
        ]
        hist_count = len(matching_lifetime)
        total_hist_count = len(eligible_bounded)

        if hist_count > 0:
            amounts_dec = [tx.amount for tx in matching_lifetime]
            hist_mean = sum(amounts_dec, start=Decimal(0)) / Decimal(hist_count)
            amounts_sorted = sorted(amounts_dec)
            if hist_count % 2 == 1:
                hist_median = amounts_sorted[hist_count // 2]
            else:
                mid = hist_count // 2
                hist_median = (amounts_sorted[mid - 1] + amounts_sorted[mid]) / Decimal(
                    2
                )

            if hist_count >= 2:
                amounts_float = [float(a) for a in amounts_dec]
                hist_stddev = statistics.stdev(amounts_float)
            else:
                hist_stddev = 0.0
        else:
            hist_mean = None
            hist_stddev = None
            hist_median = None

        seen_devices = frozenset(
            tx.device_id for tx in eligible_bounded if tx.device_id is not None
        )
        seen_merchants = frozenset(
            tx.merchant_id for tx in eligible_bounded if tx.merchant_id is not None
        )
        seen_locations = frozenset(
            tx.location_id for tx in eligible_bounded if tx.location_id is not None
        )
        seen_categories = frozenset(
            tx.category for tx in eligible_bounded if tx.category is not None
        )

        device_tx_counts = {}
        merchant_tx_counts = {}
        location_tx_counts = {}
        for tx in eligible_bounded:
            if tx.device_id is not None:
                device_tx_counts[tx.device_id] = (
                    device_tx_counts.get(tx.device_id, 0) + 1
                )
            if tx.merchant_id is not None:
                merchant_tx_counts[tx.merchant_id] = (
                    merchant_tx_counts.get(tx.merchant_id, 0) + 1
                )
            if tx.location_id is not None:
                location_tx_counts[tx.location_id] = (
                    location_tx_counts.get(tx.location_id, 0) + 1
                )

    # Evaluate baseline conditions
    if (
        hist_count >= MIN_BASELINE_OBSERVATIONS
        and hist_mean is not None
        and hist_median is not None
    ):
        has_direction_baseline = 1
        amount_vs_mean_ratio = amount_float / float(hist_mean)
        amount_vs_median_ratio = amount_float / float(hist_median)

        if hist_stddev is None or hist_stddev == 0.0:
            has_zero_variance_baseline = 1
            amount_zscore = 0.0
            is_amount_different_from_constant_baseline = (
                1 if eval_tx.amount != hist_mean else 0
            )
        else:
            has_zero_variance_baseline = 0
            amount_zscore = (amount_float - float(hist_mean)) / hist_stddev
            is_amount_different_from_constant_baseline = 0
    else:
        # Sparse history neutral sentinels
        has_direction_baseline = 0
        has_zero_variance_baseline = 0
        amount_vs_mean_ratio = 1.0
        amount_vs_median_ratio = 1.0
        amount_zscore = 0.0
        is_amount_different_from_constant_baseline = 0

    # Cold start indicator (based strictly on total transaction count, not account age)
    is_cold_start = 1 if total_hist_count < MIN_BASELINE_OBSERVATIONS else 0

    # 6. Device familiarity
    has_device = 1 if eval_tx.device_id is not None else 0
    if eval_tx.device_id is not None:
        is_new_device = 1 if eval_tx.device_id not in seen_devices else 0
        device_tx_count = device_tx_counts.get(eval_tx.device_id, 0)
    else:
        is_new_device = 0
        device_tx_count = 0

    # 7. Merchant familiarity
    has_merchant = 1 if eval_tx.merchant_id is not None else 0
    if eval_tx.merchant_id is not None:
        is_new_merchant = 1 if eval_tx.merchant_id not in seen_merchants else 0
        merchant_tx_count = merchant_tx_counts.get(eval_tx.merchant_id, 0)
    else:
        is_new_merchant = 0
        merchant_tx_count = 0

    # 8. Location familiarity
    has_location = 1 if eval_tx.location_id is not None else 0
    if eval_tx.location_id is not None:
        is_home_location = (
            1
            if account.home_location_id is not None
            and eval_tx.location_id == account.home_location_id
            else 0
        )
        is_new_location = (
            1
            if (
                account.home_location_id is None
                or eval_tx.location_id != account.home_location_id
            )
            and eval_tx.location_id not in seen_locations
            else 0
        )
        location_tx_count = location_tx_counts.get(eval_tx.location_id, 0)
        location_frequency = (
            location_tx_count / total_hist_count if total_hist_count > 0 else 0.0
        )
    else:
        is_home_location = 0
        is_new_location = 0
        location_tx_count = 0
        location_frequency = 0.0

    # 9. Category behavior
    has_category = 1 if eval_tx.category is not None else 0
    if eval_tx.category is not None:
        is_new_category = 1 if eval_tx.category not in seen_categories else 0
    else:
        is_new_category = 0

    # Category spend share in preceding 30 days:
    # Historical DEBIT transactions in matching currency in [t - 30d, t)*
    t_30d = eval_t - timedelta(seconds=CATEGORY_WINDOW_30D_SECONDS)
    v30d_debits = [
        tx
        for tx in eligible_bounded
        if _to_utc(tx.occurred_at) >= t_30d
        and tx.direction == "DEBIT"
        and tx.currency == eval_tx.currency
    ]
    denom_30d = sum((tx.amount for tx in v30d_debits), start=Decimal(0))
    if eval_tx.category is not None and denom_30d > Decimal(0):
        num_30d = sum(
            (tx.amount for tx in v30d_debits if tx.category == eval_tx.category),
            start=Decimal(0),
        )
        category_spend_share_30d = min(1.0, max(0.0, float(num_30d / denom_30d)))
    else:
        category_spend_share_30d = 0.0

    # 10. Temporal behavior (UTC)
    hour_of_day = eval_t.hour
    day_of_week = eval_t.weekday()
    is_weekend = 1 if day_of_week in WEEKEND_DAYS else 0
    is_unusual_hour = 1 if hour_of_day in UNUSUAL_HOURS else 0

    return FeatureVector(
        amount=amount_float,
        amount_log=amount_log,
        account_age_days=account_age_days,
        velocity_5m_count=velocity_5m_count,
        velocity_1h_count=velocity_1h_count,
        velocity_24h_count=velocity_24h_count,
        velocity_5m_amount=velocity_5m_amount,
        velocity_1h_amount=velocity_1h_amount,
        velocity_24h_amount=velocity_24h_amount,
        amount_vs_mean_ratio=amount_vs_mean_ratio,
        amount_vs_median_ratio=amount_vs_median_ratio,
        amount_zscore=amount_zscore,
        is_amount_different_from_constant_baseline=is_amount_different_from_constant_baseline,
        has_direction_baseline=has_direction_baseline,
        has_zero_variance_baseline=has_zero_variance_baseline,
        is_cold_start=is_cold_start,
        has_device=has_device,
        is_new_device=is_new_device,
        device_tx_count=device_tx_count,
        has_merchant=has_merchant,
        is_new_merchant=is_new_merchant,
        merchant_tx_count=merchant_tx_count,
        has_location=has_location,
        is_home_location=is_home_location,
        is_new_location=is_new_location,
        location_tx_count=location_tx_count,
        location_frequency=location_frequency,
        has_category=has_category,
        is_new_category=is_new_category,
        category_spend_share_30d=category_spend_share_30d,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        is_weekend=is_weekend,
        is_unusual_hour=is_unusual_hour,
    )


def build_feature_metadata(
    context: EvaluationContext,
    calculated_at: datetime | None = None,
) -> FeatureMetadata:
    """Build diagnostic metadata decoupled from the 34-feature vector."""
    eval_tx = context.evaluated_transaction
    account = context.account_profile
    calc_t = calculated_at or datetime.now(UTC)

    eval_t = _to_utc(eval_tx.occurred_at)
    acc_created = _to_utc(account.created_at)
    is_created_after = eval_t < acc_created

    return FeatureMetadata(
        account_id=account.id,
        transaction_id=eval_tx.id,
        occurred_at=eval_t,
        calculated_at=_to_utc(calc_t),
        is_account_created_after_txn=is_created_after,
        diagnostics={
            "currency": eval_tx.currency,
            "direction": eval_tx.direction,
            "source_namespace": eval_tx.source_namespace,
        },
    )
