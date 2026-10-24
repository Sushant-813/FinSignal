"""Financial analytics domain orchestration and business rules (Phase 5)."""

import re
import uuid
import zoneinfo
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.analytics.repository import AnalyticsRepository
from finsignal.analytics.schemas import (
    MAX_DAILY_BUCKETS,
    MAX_MONTHLY_BUCKETS,
    AccountActivityResponse,
    AccountSummaryItem,
    AccountTopCategoryItem,
    AccountTopMerchantItem,
    CategoryAnalyticsResponse,
    CategoryDistributionItem,
    MerchantAnalyticsResponse,
    MerchantDistributionItem,
    OverviewAnalyticsResponse,
    TrendAnalyticsResponse,
    TrendBucketItem,
    UnusualSpendingItem,
    UnusualSpendingResponse,
    count_calendar_buckets,
)
from finsignal.common.exceptions import NotFoundError, ValidationError
from finsignal.users.models import User

NAMESPACE_REGEX = re.compile(r"^[A-Z0-9_]{3,64}$")
CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")


class AnalyticsService:
    """Orchestrates deterministic financial analytics queries and validates business invariants."""

    def __init__(self, repository: AnalyticsRepository | None = None) -> None:
        self.repo = repository or AnalyticsRepository()

    def _validate_namespace_format(self, namespace: str) -> None:
        if not NAMESPACE_REGEX.match(namespace):
            raise ValidationError(
                message=f"Invalid namespace format: '{namespace}'. Must match ^[A-Z0-9_]{{3,64}}$",
                code="INVALID_NAMESPACE_FORMAT",
                details={"namespace": namespace},
            )

    def _validate_currency_format(self, currency: str) -> None:
        if not CURRENCY_REGEX.match(currency):
            raise ValidationError(
                message=f"Invalid currency code: '{currency}'. Must be 3 uppercase letters (ISO-4217).",
                code="INVALID_CURRENCY_FORMAT",
                details={"currency": currency},
            )

    def _validate_time_window(
        self, from_time: datetime | None, to_time: datetime | None
    ) -> None:
        if from_time is not None and to_time is not None and from_time >= to_time:
            raise ValidationError(
                message="from_time must be strictly earlier than to_time.",
                code="INVALID_DATE_RANGE",
                details={
                    "from_time": from_time.isoformat(),
                    "to_time": to_time.isoformat(),
                },
            )

    def _validate_timezone(self, tz_name: str) -> str:
        if tz_name not in zoneinfo.available_timezones():
            raise ValidationError(
                message=f"Invalid or unrecognized IANA timezone: '{tz_name}'.",
                code="INVALID_TIMEZONE",
                details={"timezone": tz_name},
            )
        return tz_name

    async def _authorize_and_verify_namespace(
        self, session: AsyncSession, user: User, namespace: str
    ) -> str:
        """Validate namespace format and verify existence in accounts or imports."""
        self._validate_namespace_format(namespace)
        exists = await self.repo.verify_namespace_exists(session, namespace)
        if not exists:
            raise NotFoundError(
                message=f"Target namespace '{namespace}' does not exist.",
                code="NAMESPACE_NOT_FOUND",
                details={"namespace": namespace},
            )
        return namespace

    async def get_overview(
        self,
        session: AsyncSession,
        *,
        user: User,
        namespace: str = "SYNTHETIC",
        currency: str = "INR",
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        account_id: uuid.UUID | None = None,
    ) -> OverviewAnalyticsResponse:
        """Retrieve global or filtered financial macro-aggregates."""
        await self._authorize_and_verify_namespace(session, user, namespace)
        self._validate_currency_format(currency)
        self._validate_time_window(from_time, to_time)

        raw = await self.repo.get_overview_metrics(
            session,
            namespace=namespace,
            currency=currency,
            from_time=from_time,
            to_time=to_time,
            account_id=account_id,
        )

        return OverviewAnalyticsResponse(
            source_namespace=namespace,
            currency=currency,
            from_time=from_time,
            to_time=to_time,
            total_transaction_count=raw["total_transaction_count"],
            debit_transaction_count=raw["debit_transaction_count"],
            credit_transaction_count=raw["credit_transaction_count"],
            total_volume_amount=raw["total_volume_amount"],
            total_debit_amount=raw["total_debit_amount"],
            total_credit_amount=raw["total_credit_amount"],
            net_cash_flow=raw["net_cash_flow"],
            average_transaction_amount=raw["average_transaction_amount"],
            median_transaction_amount=raw["median_transaction_amount"],
            debit_average_amount=raw["debit_average_amount"],
            debit_median_amount=raw["debit_median_amount"],
            credit_average_amount=raw["credit_average_amount"],
            credit_median_amount=raw["credit_median_amount"],
            min_transaction_amount=raw["min_transaction_amount"],
            max_transaction_amount=raw["max_transaction_amount"],
        )

    async def get_trends(
        self,
        session: AsyncSession,
        *,
        user: User,
        from_time: datetime,
        to_time: datetime,
        namespace: str = "SYNTHETIC",
        currency: str = "INR",
        interval: str = "day",
        timezone: str = "UTC",
        account_id: uuid.UUID | None = None,
    ) -> TrendAnalyticsResponse:
        """Retrieve contiguous zero-filled daily or monthly trend buckets."""
        await self._authorize_and_verify_namespace(session, user, namespace)
        self._validate_currency_format(currency)
        self._validate_time_window(from_time, to_time)
        tz_name = self._validate_timezone(timezone)

        if interval not in ("day", "month"):
            raise ValidationError(
                message=f"Unsupported trend interval: '{interval}'. Must be 'day' or 'month'.",
                code="INVALID_INTERVAL",
                details={"interval": interval},
            )

        bucket_count = count_calendar_buckets(from_time, to_time, tz_name, interval)
        max_allowed = MAX_DAILY_BUCKETS if interval == "day" else MAX_MONTHLY_BUCKETS
        if bucket_count > max_allowed:
            raise ValidationError(
                message=f"Requested range generates {bucket_count} {interval} buckets, exceeding maximum limit of {max_allowed}.",
                code="TREND_BUCKET_COUNT_EXCEEDS_LIMIT",
                details={
                    "interval": interval,
                    "bucket_count": bucket_count,
                    "max_allowed": max_allowed,
                },
            )

        rows = await self.repo.get_trend_buckets(
            session,
            namespace=namespace,
            currency=currency,
            from_time=from_time,
            to_time=to_time,
            interval=interval,
            tz_name=tz_name,
            account_id=account_id,
        )

        bucket_items = [
            TrendBucketItem(
                bucket_start=r["bucket_start"],
                transaction_count=r["transaction_count"],
                debit_count=r["debit_count"],
                credit_count=r["credit_count"],
                total_debit_amount=r["total_debit_amount"],
                total_credit_amount=r["total_credit_amount"],
                net_cash_flow=r["net_cash_flow"],
            )
            for r in rows
        ]

        return TrendAnalyticsResponse(
            source_namespace=namespace,
            currency=currency,
            interval=interval,
            timezone=tz_name,
            from_time=from_time,
            to_time=to_time,
            total_buckets=len(bucket_items),
            buckets=bucket_items,
        )

    async def get_categories(
        self,
        session: AsyncSession,
        *,
        user: User,
        namespace: str = "SYNTHETIC",
        currency: str = "INR",
        direction: str = "DEBIT",
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        account_id: uuid.UUID | None = None,
    ) -> CategoryAnalyticsResponse:
        """Retrieve category spending/volume distribution with percentage shares."""
        await self._authorize_and_verify_namespace(session, user, namespace)
        self._validate_currency_format(currency)
        self._validate_time_window(from_time, to_time)

        if direction not in ("DEBIT", "CREDIT"):
            raise ValidationError(
                message=f"Invalid direction: '{direction}'. Must be 'DEBIT' or 'CREDIT'.",
                code="INVALID_DIRECTION",
                details={"direction": direction},
            )

        total_amount, rows = await self.repo.get_category_distribution(
            session,
            namespace=namespace,
            currency=currency,
            direction=direction,
            from_time=from_time,
            to_time=to_time,
            account_id=account_id,
        )

        items: list[CategoryDistributionItem] = []
        for r in rows:
            cat_amt = Decimal(str(r["total_amount"]))
            pct = (
                (cat_amt / total_amount * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if total_amount > 0
                else Decimal("0.00")
            )
            items.append(
                CategoryDistributionItem(
                    category_name=r["category_name"],
                    transaction_count=r["transaction_count"],
                    total_amount=r["total_amount"],
                    percentage_of_total=f"{pct:.2f}",
                    average_amount=r["average_amount"],
                )
            )

        return CategoryAnalyticsResponse(
            source_namespace=namespace,
            currency=currency,
            direction=direction,
            total_directional_amount=total_amount,
            categories=items,
        )

    async def get_merchants(
        self,
        session: AsyncSession,
        *,
        user: User,
        namespace: str = "SYNTHETIC",
        currency: str = "INR",
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        sort_by: str = "amount",
        limit: int = 20,
        offset: int = 0,
    ) -> MerchantAnalyticsResponse:
        """Retrieve top merchants ranked by debit volume or count with dual percentages."""
        await self._authorize_and_verify_namespace(session, user, namespace)
        self._validate_currency_format(currency)
        self._validate_time_window(from_time, to_time)

        if sort_by not in ("amount", "count"):
            raise ValidationError(
                message=f"Invalid sort_by: '{sort_by}'. Must be 'amount' or 'count'.",
                code="INVALID_SORT_BY",
                details={"sort_by": sort_by},
            )

        if limit < 1 or limit > 100:
            raise ValidationError(
                message="limit must be between 1 and 100.",
                code="INVALID_PAGINATION_LIMIT",
                details={"limit": limit},
            )

        if offset < 0:
            raise ValidationError(
                message="offset must be greater than or equal to 0.",
                code="INVALID_PAGINATION_OFFSET",
                details={"offset": offset},
            )

        (
            tot_debit,
            tot_merch,
            non_merch,
            rows,
        ) = await self.repo.get_merchant_distribution(
            session,
            namespace=namespace,
            currency=currency,
            from_time=from_time,
            to_time=to_time,
            sort_by=sort_by,
            limit=limit,
            offset=offset,
        )

        merch_items: list[MerchantDistributionItem] = []
        for r in rows:
            m_amt = Decimal(str(r["total_amount"]))
            pct_total = (
                (m_amt / tot_debit * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if tot_debit > 0
                else Decimal("0.00")
            )
            pct_merch = (
                (m_amt / tot_merch * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if tot_merch > 0
                else Decimal("0.00")
            )
            merch_items.append(
                MerchantDistributionItem(
                    merchant_id=r["merchant_id"],
                    merchant_name=r["merchant_name"],
                    merchant_category=r["merchant_category"],
                    transaction_count=r["transaction_count"],
                    total_amount=r["total_amount"],
                    average_amount=r["average_amount"],
                    percentage_of_total_debit=f"{pct_total:.2f}",
                    percentage_of_merchant_spend=f"{pct_merch:.2f}",
                )
            )

        return MerchantAnalyticsResponse(
            source_namespace=namespace,
            currency=currency,
            total_debit_amount=tot_debit,
            total_merchant_debit_amount=tot_merch,
            non_merchant_debit_amount=non_merch,
            returned_merchant_count=len(merch_items),
            merchants=merch_items,
        )

    async def get_account_activity(
        self,
        session: AsyncSession,
        *,
        user: User,
        account_id: uuid.UUID,
        currency: str = "INR",
        timezone: str = "UTC",
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> AccountActivityResponse:
        """Retrieve account activity and summary scoped to authoritative account namespace."""
        account = await self.repo.get_account_by_id(session, account_id)
        if account is None:
            raise NotFoundError(
                message=f"Account with ID '{account_id}' was not found.",
                code="RESOURCE_NOT_FOUND",
                details={"account_id": str(account_id)},
            )

        account_namespace = account.source_namespace
        self._validate_currency_format(currency)
        self._validate_time_window(from_time, to_time)
        tz_name = self._validate_timezone(timezone)

        # 1. Available currencies for this account in its namespace
        available_currencies = await self.repo.get_available_currencies(
            session, account_id=account_id, namespace=account_namespace
        )

        # 2. Account-level financial summary
        raw_overview = await self.repo.get_overview_metrics(
            session,
            namespace=account_namespace,
            currency=currency,
            from_time=from_time,
            to_time=to_time,
            account_id=account_id,
        )

        summary_item = AccountSummaryItem(
            total_transaction_count=raw_overview["total_transaction_count"],
            debit_transaction_count=raw_overview["debit_transaction_count"],
            credit_transaction_count=raw_overview["credit_transaction_count"],
            total_volume_amount=raw_overview["total_volume_amount"],
            total_debit_amount=raw_overview["total_debit_amount"],
            total_credit_amount=raw_overview["total_credit_amount"],
            net_cash_flow=raw_overview["net_cash_flow"],
            average_transaction_amount=raw_overview["average_transaction_amount"],
            median_transaction_amount=raw_overview["median_transaction_amount"],
            debit_average_amount=raw_overview["debit_average_amount"],
            debit_median_amount=raw_overview["debit_median_amount"],
            credit_average_amount=raw_overview["credit_average_amount"],
            credit_median_amount=raw_overview["credit_median_amount"],
            min_transaction_amount=raw_overview["min_transaction_amount"],
            max_transaction_amount=raw_overview["max_transaction_amount"],
        )

        # 3. Account activity details (timestamps, active days, top categories/merchants)
        details = await self.repo.get_account_activity_details(
            session,
            account_id=account_id,
            namespace=account_namespace,
            currency=currency,
            tz_name=tz_name,
            from_time=from_time,
            to_time=to_time,
        )

        total_debit = Decimal(str(raw_overview["total_debit_amount"]))

        top_cats: list[AccountTopCategoryItem] = []
        for cat in details["top_categories"]:
            cat_amt = Decimal(str(cat["total_amount"]))
            pct = (
                (cat_amt / total_debit * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if total_debit > 0
                else Decimal("0.00")
            )
            top_cats.append(
                AccountTopCategoryItem(
                    category_name=cat["category_name"],
                    transaction_count=cat["transaction_count"],
                    total_amount=cat["total_amount"],
                    percentage_of_total=f"{pct:.2f}",
                )
            )

        # Compute total merchant debit for the account
        top_merch_total = sum(
            Decimal(str(m["total_amount"])) for m in details["top_merchants"]
        )
        top_merchants: list[AccountTopMerchantItem] = []
        for m in details["top_merchants"]:
            m_amt = Decimal(str(m["total_amount"]))
            pct_debit = (
                (m_amt / total_debit * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if total_debit > 0
                else Decimal("0.00")
            )
            pct_merch = (
                (m_amt / top_merch_total * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if top_merch_total > 0
                else Decimal("0.00")
            )
            top_merchants.append(
                AccountTopMerchantItem(
                    merchant_id=m["merchant_id"],
                    merchant_name=m["merchant_name"],
                    merchant_category=m["merchant_category"],
                    transaction_count=m["transaction_count"],
                    total_amount=m["total_amount"],
                    percentage_of_total_debit=f"{pct_debit:.2f}",
                    percentage_of_merchant_spend=f"{pct_merch:.2f}",
                )
            )

        return AccountActivityResponse(
            account_id=account.id,
            external_account_id=account.external_account_id,
            source_namespace=account_namespace,
            account_type=account.account_type,
            status=account.status,
            currency=currency,
            available_currencies=available_currencies,
            first_transaction_at=details["first_transaction_at"],
            last_transaction_at=details["last_transaction_at"],
            active_days_count=details["active_days_count"],
            summary=summary_item,
            top_categories=top_cats,
            top_merchants=top_merchants,
        )

    async def get_unusual_spending(
        self,
        session: AsyncSession,
        *,
        user: User,
        account_id: uuid.UUID,
        currency: str = "INR",
        multiplier: Decimal = Decimal("3.0"),
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> UnusualSpendingResponse:
        """Identify deterministic debit outliers exceeding multiplier * median_debit."""
        account = await self.repo.get_account_by_id(session, account_id)
        if account is None:
            raise NotFoundError(
                message=f"Account with ID '{account_id}' was not found.",
                code="RESOURCE_NOT_FOUND",
                details={"account_id": str(account_id)},
            )

        account_namespace = account.source_namespace
        self._validate_currency_format(currency)
        self._validate_time_window(from_time, to_time)

        if multiplier < Decimal("1.5") or multiplier > Decimal("10.0"):
            raise ValidationError(
                message="multiplier must be between 1.5 and 10.0.",
                code="INVALID_MULTIPLIER",
                details={"multiplier": str(multiplier)},
            )

        if limit < 1 or limit > 100:
            raise ValidationError(
                message="limit must be between 1 and 100.",
                code="INVALID_PAGINATION_LIMIT",
                details={"limit": limit},
            )

        if offset < 0:
            raise ValidationError(
                message="offset must be greater than or equal to 0.",
                code="INVALID_PAGINATION_OFFSET",
                details={"offset": offset},
            )

        med, thresh, total_count, rows = await self.repo.get_unusual_spending_outliers(
            session,
            account_id=account_id,
            namespace=account_namespace,
            currency=currency,
            multiplier=multiplier,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
            offset=offset,
        )

        items = [
            UnusualSpendingItem(
                transaction_id=r["transaction_id"],
                external_transaction_id=r["external_transaction_id"],
                occurred_at=r["occurred_at"],
                amount=r["amount"],
                currency=r["currency"],
                transaction_type=r["transaction_type"],
                direction=r["direction"],
                category=r["category"],
                deviation_ratio=str(r["deviation_ratio"]),
            )
            for r in rows
        ]

        return UnusualSpendingResponse(
            account_id=account.id,
            currency=currency,
            account_median_debit=med,
            multiplier=f"{multiplier:.1f}",
            outlier_threshold_amount=thresh,
            unusual_transaction_count=total_count,
            returned_count=len(items),
            transactions=items,
        )
