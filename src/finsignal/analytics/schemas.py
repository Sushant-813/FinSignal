"""Pydantic v2 schemas for financial analytics (Phase 5)."""

import uuid
import zoneinfo
from datetime import datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class TrendInterval(StrEnum):
    """Supported aggregation intervals for trend analytics."""

    DAY = "day"
    MONTH = "month"


def to_money_str(v: Any) -> str:
    """Format monetary numbers to strict two-decimal string representation."""
    if v is None:
        return "0.00"
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    if isinstance(v, (int, float)):
        return f"{Decimal(str(v)):.2f}"
    if isinstance(v, str):
        return f"{Decimal(v):.2f}"
    raise ValueError(f"Cannot format {v!r} as monetary string")


def to_optional_money_str(v: Any) -> str | None:
    """Format optional monetary numbers to strict two-decimal string or None."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    if isinstance(v, (int, float)):
        return f"{Decimal(str(v)):.2f}"
    if isinstance(v, str):
        return f"{Decimal(v):.2f}"
    raise ValueError(f"Cannot format {v!r} as monetary string")


MoneyStr = Annotated[str, BeforeValidator(to_money_str)]
OptionalMoneyStr = Annotated[str | None, BeforeValidator(to_optional_money_str)]


# ---------------------------------------------------------------------------
# 1. Overview Analytics
# ---------------------------------------------------------------------------


class OverviewAnalyticsResponse(BaseModel):
    """Platform or filtered financial macro-aggregates."""

    model_config = ConfigDict(extra="forbid")

    source_namespace: str
    currency: str
    from_time: datetime | None = None
    to_time: datetime | None = None
    total_transaction_count: int
    debit_transaction_count: int
    credit_transaction_count: int
    total_volume_amount: MoneyStr
    total_debit_amount: MoneyStr
    total_credit_amount: MoneyStr
    net_cash_flow: MoneyStr
    average_transaction_amount: OptionalMoneyStr = None
    median_transaction_amount: OptionalMoneyStr = None
    debit_average_amount: OptionalMoneyStr = None
    debit_median_amount: OptionalMoneyStr = None
    credit_average_amount: OptionalMoneyStr = None
    credit_median_amount: OptionalMoneyStr = None
    min_transaction_amount: OptionalMoneyStr = None
    max_transaction_amount: OptionalMoneyStr = None


# ---------------------------------------------------------------------------
# 2. Trends Analytics
# ---------------------------------------------------------------------------


class TrendBucketItem(BaseModel):
    """Single temporal bucket within a trend series."""

    model_config = ConfigDict(extra="forbid")

    bucket_start: datetime
    transaction_count: int
    debit_count: int
    credit_count: int
    total_debit_amount: MoneyStr
    total_credit_amount: MoneyStr
    net_cash_flow: MoneyStr


class TrendAnalyticsResponse(BaseModel):
    """Contiguous time-series transaction counts and debit/credit volume buckets."""

    model_config = ConfigDict(extra="forbid")

    source_namespace: str
    currency: str
    interval: str
    timezone: str
    from_time: datetime
    to_time: datetime
    total_buckets: int
    buckets: list[TrendBucketItem]


# ---------------------------------------------------------------------------
# 3. Category Distribution Analytics
# ---------------------------------------------------------------------------


class CategoryDistributionItem(BaseModel):
    """Distribution metric for a single transaction category."""

    model_config = ConfigDict(extra="forbid")

    category_name: str
    transaction_count: int
    total_amount: MoneyStr
    percentage_of_total: str
    average_amount: MoneyStr


class CategoryAnalyticsResponse(BaseModel):
    """Spending and volume distributions grouped by transaction category."""

    model_config = ConfigDict(extra="forbid")

    source_namespace: str
    currency: str
    direction: str
    total_directional_amount: MoneyStr
    categories: list[CategoryDistributionItem]


# ---------------------------------------------------------------------------
# 4. Merchant Analytics
# ---------------------------------------------------------------------------


class MerchantDistributionItem(BaseModel):
    """Spending and volume metric for a single merchant."""

    model_config = ConfigDict(extra="forbid")

    merchant_id: uuid.UUID
    merchant_name: str
    merchant_category: str
    transaction_count: int
    total_amount: MoneyStr
    average_amount: MoneyStr
    percentage_of_total_debit: str
    percentage_of_merchant_spend: str


class MerchantAnalyticsResponse(BaseModel):
    """Top merchants ranked by transaction volume or frequency."""

    model_config = ConfigDict(extra="forbid")

    source_namespace: str
    currency: str
    total_debit_amount: MoneyStr
    total_merchant_debit_amount: MoneyStr
    non_merchant_debit_amount: MoneyStr
    returned_merchant_count: int
    merchants: list[MerchantDistributionItem]


# ---------------------------------------------------------------------------
# 5. Account Activity Analytics
# ---------------------------------------------------------------------------


class AccountSummaryItem(BaseModel):
    """Financial aggregate summary for an account."""

    model_config = ConfigDict(extra="forbid")

    total_transaction_count: int
    debit_transaction_count: int
    credit_transaction_count: int
    total_volume_amount: MoneyStr
    total_debit_amount: MoneyStr
    total_credit_amount: MoneyStr
    net_cash_flow: MoneyStr
    average_transaction_amount: OptionalMoneyStr = None
    median_transaction_amount: OptionalMoneyStr = None
    debit_average_amount: OptionalMoneyStr = None
    debit_median_amount: OptionalMoneyStr = None
    credit_average_amount: OptionalMoneyStr = None
    credit_median_amount: OptionalMoneyStr = None
    min_transaction_amount: OptionalMoneyStr = None
    max_transaction_amount: OptionalMoneyStr = None


class AccountTopCategoryItem(BaseModel):
    """Top spending category for an account."""

    model_config = ConfigDict(extra="forbid")

    category_name: str
    transaction_count: int
    total_amount: MoneyStr
    percentage_of_total: str


class AccountTopMerchantItem(BaseModel):
    """Top merchant for an account."""

    model_config = ConfigDict(extra="forbid")

    merchant_id: uuid.UUID
    merchant_name: str
    merchant_category: str
    transaction_count: int
    total_amount: MoneyStr
    percentage_of_total_debit: str
    percentage_of_merchant_spend: str


class AccountActivityResponse(BaseModel):
    """Account-specific financial activity and summary."""

    model_config = ConfigDict(extra="forbid")

    account_id: uuid.UUID
    external_account_id: str | None = None
    source_namespace: str
    account_type: str
    status: str
    currency: str
    available_currencies: list[str] = Field(default_factory=list)
    first_transaction_at: datetime | None = None
    last_transaction_at: datetime | None = None
    active_days_count: int
    summary: AccountSummaryItem
    top_categories: list[AccountTopCategoryItem] = Field(default_factory=list)
    top_merchants: list[AccountTopMerchantItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. Unusual Spending Analytics
# ---------------------------------------------------------------------------


class UnusualSpendingItem(BaseModel):
    """Single unusual debit outlier transaction."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: uuid.UUID
    external_transaction_id: str
    occurred_at: datetime
    amount: MoneyStr
    currency: str
    transaction_type: str
    direction: str
    category: str | None = None
    deviation_ratio: str


class UnusualSpendingResponse(BaseModel):
    """Deterministic statistical outliers for an account."""

    model_config = ConfigDict(extra="forbid")

    account_id: uuid.UUID
    currency: str
    account_median_debit: OptionalMoneyStr = None
    multiplier: str
    outlier_threshold_amount: OptionalMoneyStr = None
    unusual_transaction_count: int  # Total matching count before pagination
    returned_count: int  # Number of returned items on this page
    transactions: list[UnusualSpendingItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Domain Helpers & Calendar Validation
# ---------------------------------------------------------------------------

MAX_DAILY_BUCKETS = 366
MAX_MONTHLY_BUCKETS = 120


def count_calendar_buckets(
    from_time: datetime,
    to_time: datetime,
    tz_name: str,
    interval: str,
) -> int:
    """Calculate the exact number of calendar buckets in the requested timezone.

    Operates over the half-open interval [from_time, to_time).
    """
    tz = zoneinfo.ZoneInfo(tz_name)
    local_from = from_time.astimezone(tz)
    local_to = to_time.astimezone(tz)

    if local_from >= local_to:
        return 0

    if interval == "day":
        d_start = local_from.date()
        # In a half-open window, if local_to is exactly at midnight, the latest instant
        # falls on the preceding calendar day.
        if local_to.time() == time.min:
            d_last = local_to.date() - timedelta(days=1)
        else:
            d_last = local_to.date()
        return max(0, (d_last - d_start).days + 1)

    if interval == "month":
        y_start, m_start = local_from.year, local_from.month
        if local_to.day == 1 and local_to.time() == time.min:
            prior = local_to - timedelta(microseconds=1)
            y_last, m_last = prior.year, prior.month
        else:
            y_last, m_last = local_to.year, local_to.month
        return max(0, (y_last - y_start) * 12 + (m_last - m_start) + 1)

    raise ValueError(f"Unsupported interval: '{interval}'. Must be 'day' or 'month'.")
