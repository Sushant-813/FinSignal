"""Unit tests for analytics Pydantic schemas and calendar helpers (Phase 5)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from finsignal.analytics.schemas import (
    CategoryAnalyticsResponse,
    OverviewAnalyticsResponse,
    TrendAnalyticsResponse,
    TrendInterval,
    UnusualSpendingResponse,
    count_calendar_buckets,
    to_money_str,
    to_optional_money_str,
)


def test_money_str_formatter() -> None:
    """Verify to_money_str formats Decimal, float, int, str to two-decimal strings."""
    assert to_money_str(Decimal("123.456")) == "123.46"
    assert to_money_str(Decimal("123.4")) == "123.40"
    assert to_money_str(100) == "100.00"
    assert to_money_str(99.9) == "99.90"
    assert to_money_str("45000.5") == "45000.50"
    assert to_money_str(None) == "0.00"

    with pytest.raises(ValueError):
        to_money_str(object())


def test_optional_money_str_formatter() -> None:
    """Verify to_optional_money_str formats values or returns None."""
    assert to_optional_money_str(None) is None
    assert to_optional_money_str(Decimal("0")) == "0.00"
    assert to_optional_money_str("12.34") == "12.34"


def test_trend_interval_enum() -> None:
    """Verify TrendInterval values."""
    assert TrendInterval.DAY.value == "day"
    assert TrendInterval.MONTH.value == "month"
    assert TrendInterval("day") == TrendInterval.DAY
    assert TrendInterval("month") == TrendInterval.MONTH


def test_count_calendar_buckets_daily() -> None:
    """Verify daily calendar bucket count across half-open windows."""
    # Exactly 1 day
    t0 = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC)
    assert count_calendar_buckets(t0, t1, "UTC", "day") == 1

    # Exactly 30 days
    t30 = datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC)
    assert count_calendar_buckets(t0, t30, "UTC", "day") == 30

    # Sub-second boundary into next day produces 2 buckets
    t_sub = datetime(2026, 9, 2, 0, 0, 0, 500000, tzinfo=UTC)
    assert count_calendar_buckets(t0, t_sub, "UTC", "day") == 2

    # Negative or equal range produces 0
    assert count_calendar_buckets(t1, t0, "UTC", "day") == 0
    assert count_calendar_buckets(t0, t0, "UTC", "day") == 0


def test_count_calendar_buckets_monthly() -> None:
    """Verify monthly calendar bucket count across half-open windows."""
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC)
    assert count_calendar_buckets(t0, t1, "UTC", "month") == 1

    t_full_year = datetime(2027, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert count_calendar_buckets(t0, t_full_year, "UTC", "month") == 12


def test_count_calendar_buckets_dst_transition() -> None:
    """Verify daily buckets count across DST spring-forward."""
    # US DST spring-forward: March 8, 2026
    t0 = datetime(2026, 3, 7, 5, 0, 0, tzinfo=UTC)  # midnight EST
    t1 = datetime(2026, 3, 10, 4, 0, 0, tzinfo=UTC)  # midnight EDT 3 days later
    assert count_calendar_buckets(t0, t1, "America/New_York", "day") == 3


def test_overview_schema_serialization() -> None:
    """Verify OverviewAnalyticsResponse validates and formats monetary fields to strings."""
    data = {
        "source_namespace": "SYNTHETIC",
        "currency": "INR",
        "from_time": "2026-09-01T00:00:00Z",
        "to_time": "2026-10-01T00:00:00Z",
        "total_transaction_count": 100,
        "debit_transaction_count": 80,
        "credit_transaction_count": 20,
        "total_volume_amount": Decimal("150000.5"),
        "total_debit_amount": Decimal("90000.5"),
        "total_credit_amount": Decimal("60000.0"),
        "net_cash_flow": Decimal("-30000.5"),
        "average_transaction_amount": Decimal("1500.005"),
        "median_transaction_amount": Decimal("1200.00"),
        "debit_average_amount": Decimal("1125.006"),
        "debit_median_amount": Decimal("1000.00"),
        "credit_average_amount": Decimal("3000.00"),
        "credit_median_amount": Decimal("2500.00"),
        "min_transaction_amount": Decimal("10.00"),
        "max_transaction_amount": Decimal("50000.00"),
    }
    model = OverviewAnalyticsResponse(**data)
    dumped = model.model_dump()
    assert dumped["total_volume_amount"] == "150000.50"
    assert dumped["net_cash_flow"] == "-30000.50"
    assert dumped["debit_average_amount"] == "1125.01"


def test_trend_schema_serialization() -> None:
    """Verify TrendAnalyticsResponse serializes buckets correctly."""
    data = {
        "source_namespace": "SYNTHETIC",
        "currency": "INR",
        "interval": "day",
        "timezone": "UTC",
        "from_time": "2026-09-01T00:00:00Z",
        "to_time": "2026-09-03T00:00:00Z",
        "total_buckets": 2,
        "buckets": [
            {
                "bucket_start": "2026-09-01T00:00:00Z",
                "transaction_count": 5,
                "debit_count": 4,
                "credit_count": 1,
                "total_debit_amount": Decimal("400.00"),
                "total_credit_amount": Decimal("100.00"),
                "net_cash_flow": Decimal("-300.00"),
            },
            {
                "bucket_start": "2026-09-02T00:00:00Z",
                "transaction_count": 0,
                "debit_count": 0,
                "credit_count": 0,
                "total_debit_amount": Decimal("0.00"),
                "total_credit_amount": Decimal("0.00"),
                "net_cash_flow": Decimal("0.00"),
            },
        ],
    }
    model = TrendAnalyticsResponse(**data)
    assert model.total_buckets == 2
    assert model.buckets[0].total_debit_amount == "400.00"
    assert model.buckets[1].total_debit_amount == "0.00"


def test_category_schema_serialization() -> None:
    """Verify CategoryAnalyticsResponse serializes categories."""
    data = {
        "source_namespace": "SYNTHETIC",
        "currency": "INR",
        "direction": "DEBIT",
        "total_directional_amount": Decimal("1000.00"),
        "categories": [
            {
                "category_name": "FOOD",
                "transaction_count": 10,
                "total_amount": Decimal("600.00"),
                "percentage_of_total": "60.00",
                "average_amount": Decimal("60.00"),
            }
        ],
    }
    model = CategoryAnalyticsResponse(**data)
    assert model.total_directional_amount == "1000.00"
    assert model.categories[0].percentage_of_total == "60.00"


def test_unusual_spending_schema_serialization() -> None:
    """Verify UnusualSpendingResponse serializes outlier items."""
    acc_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    data = {
        "account_id": acc_id,
        "currency": "INR",
        "account_median_debit": Decimal("500.00"),
        "multiplier": "3.0",
        "outlier_threshold_amount": Decimal("1500.00"),
        "unusual_transaction_count": 1,
        "returned_count": 1,
        "transactions": [
            {
                "transaction_id": tx_id,
                "external_transaction_id": "TXN_001",
                "occurred_at": datetime.now(UTC),
                "amount": Decimal("2500.00"),
                "currency": "INR",
                "transaction_type": "PURCHASE",
                "direction": "DEBIT",
                "category": "ELECTRONICS",
                "deviation_ratio": "5.00",
            }
        ],
    }
    model = UnusualSpendingResponse(**data)
    assert model.account_median_debit == "500.00"
    assert model.outlier_threshold_amount == "1500.00"
    assert model.transactions[0].amount == "2500.00"
