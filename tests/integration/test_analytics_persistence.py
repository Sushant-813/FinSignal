"""PostgreSQL integration tests for financial analytics repository and services (Phase 5)."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
from finsignal.analytics.repository import AnalyticsRepository
from finsignal.analytics.service import AnalyticsService
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.merchants.models import Merchant
from finsignal.transactions.models import Transaction
from finsignal.users.models import User


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
                text("TRUNCATE TABLE transactions, accounts, merchants, users CASCADE;")
            )
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


def _make_dummy_user() -> User:
    user = User()
    user.id = uuid.uuid4()
    user.role = "ADMIN"
    user.email = "admin@example.com"
    user.is_active = True
    return user


async def _create_test_account(
    session: AsyncSession,
    namespace: str = "SYNTHETIC",
    external_id: str | None = None,
) -> Account:
    acc = Account(
        id=uuid.uuid4(),
        source_namespace=namespace,
        external_account_id=external_id or f"ACC_{uuid.uuid4().hex[:6]}",
        account_type="CHECKING",
        status="ACTIVE",
    )
    session.add(acc)
    await session.commit()
    return acc


async def _create_test_merchant(
    session: AsyncSession,
    name: str = "Test Merchant",
    category: str = "RETAIL",
) -> Merchant:
    m = Merchant(
        id=uuid.uuid4(),
        merchant_name=name,
        merchant_category=category,
        external_merchant_id=f"MERCH_{uuid.uuid4().hex[:6]}",
    )
    session.add(m)
    await session.commit()
    return m


async def _create_test_transaction(
    session: AsyncSession,
    account: Account,
    amount: Decimal,
    direction: str = "DEBIT",
    currency: str = "INR",
    occurred_at: datetime | None = None,
    category: str | None = "OTHER",
    merchant: Merchant | None = None,
    tx_type: str = "PURCHASE",
) -> Transaction:
    tx = Transaction(
        id=uuid.uuid4(),
        source_namespace=account.source_namespace,
        external_transaction_id=f"TXN_{uuid.uuid4().hex[:8]}",
        account_id=account.id,
        amount=amount,
        direction=direction,
        currency=currency,
        occurred_at=occurred_at or datetime.now(UTC),
        category=category,
        merchant_id=merchant.id if merchant else None,
        transaction_type=tx_type,
    )
    session.add(tx)
    await session.commit()
    return tx


@pytest.mark.asyncio
async def test_hand_calculated_overview_and_halfway_median(
    async_session: AsyncSession,
) -> None:
    """Verify hand-calculated metrics and halfway continuous median rounding (100.015 -> 100.02)."""
    acc = await _create_test_account(async_session, "SYNTHETIC")

    # Seed 2 debits specifically designed to test halfway median rounding: 100.01 and 100.02
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    t3 = datetime(2026, 9, 3, 10, 0, 0, tzinfo=UTC)

    await _create_test_transaction(
        async_session, acc, Decimal("100.01"), "DEBIT", occurred_at=t1
    )
    await _create_test_transaction(
        async_session, acc, Decimal("100.02"), "DEBIT", occurred_at=t2
    )
    # Plus 1 credit of 500.00
    await _create_test_transaction(
        async_session, acc, Decimal("500.00"), "CREDIT", occurred_at=t3
    )

    repo = AnalyticsRepository()
    res = await repo.get_overview_metrics(
        async_session, namespace="SYNTHETIC", currency="INR"
    )

    assert res["total_transaction_count"] == 3
    assert res["debit_transaction_count"] == 2
    assert res["credit_transaction_count"] == 1

    # Exact sums
    assert res["total_debit_amount"] == Decimal("200.03")
    assert res["total_credit_amount"] == Decimal("500.00")
    assert res["total_volume_amount"] == Decimal("700.03")
    assert res["net_cash_flow"] == Decimal("299.97")  # 500.00 - 200.03

    # Halfway median rounding assertion: continuous median is 100.015 -> rounds to 100.02 under ROUND_HALF_UP
    assert res["debit_median_amount"] == Decimal("100.02")
    assert res["credit_median_amount"] == Decimal("500.00")


@pytest.mark.asyncio
async def test_half_open_boundaries(async_session: AsyncSession) -> None:
    """Verify half-open time interval: [from_time, to_time) strictly includes from_time and excludes to_time."""
    acc = await _create_test_account(async_session, "SYNTHETIC")

    t_start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    t_mid = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC)
    t_after = datetime(2026, 9, 2, 0, 0, 1, tzinfo=UTC)

    # 1. Exactly at from_time -> MUST BE INCLUDED
    await _create_test_transaction(
        async_session, acc, Decimal("10.00"), occurred_at=t_start
    )
    # 2. In middle -> MUST BE INCLUDED
    await _create_test_transaction(
        async_session, acc, Decimal("20.00"), occurred_at=t_mid
    )
    # 3. Exactly at to_time -> MUST BE EXCLUDED
    await _create_test_transaction(
        async_session, acc, Decimal("30.00"), occurred_at=t_end
    )
    # 4. After to_time -> MUST BE EXCLUDED
    await _create_test_transaction(
        async_session, acc, Decimal("40.00"), occurred_at=t_after
    )

    repo = AnalyticsRepository()
    res = await repo.get_overview_metrics(
        async_session,
        namespace="SYNTHETIC",
        currency="INR",
        from_time=t_start,
        to_time=t_end,
    )

    assert res["total_transaction_count"] == 2
    assert res["total_debit_amount"] == Decimal("30.00")  # 10.00 + 20.00


@pytest.mark.asyncio
async def test_sub_second_boundary_regression(async_session: AsyncSession) -> None:
    """Verify that to_time with fractional seconds retains the current day bucket without dropping it."""
    acc = await _create_test_account(async_session, "SYNTHETIC")

    t_tx = datetime(2026, 9, 2, 0, 0, 0, 100000, tzinfo=UTC)  # 100ms into day 2
    await _create_test_transaction(
        async_session, acc, Decimal("50.00"), occurred_at=t_tx
    )

    repo = AnalyticsRepository()
    t_from = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    t_to = datetime(2026, 9, 2, 0, 0, 0, 500000, tzinfo=UTC)  # 500ms into day 2

    buckets = await repo.get_trend_buckets(
        async_session,
        namespace="SYNTHETIC",
        currency="INR",
        from_time=t_from,
        to_time=t_to,
        interval="day",
        tz_name="UTC",
    )

    assert len(buckets) == 2
    # Day 1 bucket (09-01) -> 0 tx
    assert buckets[0]["transaction_count"] == 0
    # Day 2 bucket (09-02) -> 1 tx
    assert buckets[1]["transaction_count"] == 1
    assert buckets[1]["total_debit_amount"] == Decimal("50.00")


@pytest.mark.asyncio
async def test_zero_filled_trends(async_session: AsyncSession) -> None:
    """Verify zero-filled contiguous buckets for daily and monthly intervals."""
    acc = await _create_test_account(async_session, "SYNTHETIC")

    # Day 1
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)
    # Day 4
    t4 = datetime(2026, 9, 4, 15, 0, 0, tzinfo=UTC)

    await _create_test_transaction(
        async_session, acc, Decimal("100.00"), occurred_at=t1
    )
    await _create_test_transaction(
        async_session, acc, Decimal("200.00"), occurred_at=t4
    )

    repo = AnalyticsRepository()
    from_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    to_time = datetime(2026, 9, 5, 0, 0, 0, tzinfo=UTC)

    buckets = await repo.get_trend_buckets(
        async_session,
        namespace="SYNTHETIC",
        currency="INR",
        from_time=from_time,
        to_time=to_time,
        interval="day",
        tz_name="UTC",
    )

    assert len(buckets) == 4
    assert buckets[0]["transaction_count"] == 1
    assert buckets[0]["total_debit_amount"] == Decimal("100.00")
    # Day 2 & 3 must be zero-filled
    assert buckets[1]["transaction_count"] == 0
    assert buckets[1]["total_debit_amount"] == Decimal("0.00")
    assert buckets[2]["transaction_count"] == 0
    assert buckets[2]["total_debit_amount"] == Decimal("0.00")
    # Day 4
    assert buckets[3]["transaction_count"] == 1
    assert buckets[3]["total_debit_amount"] == Decimal("200.00")


@pytest.mark.asyncio
async def test_timezone_independence_and_session_mismatch(
    async_session: AsyncSession,
) -> None:
    """Verify trends are calculated using requested timezone, unaffected by session timezone."""
    acc = await _create_test_account(async_session, "SYNTHETIC")

    # Transaction occurred at 2026-09-01 02:00:00 UTC
    # In America/New_York (UTC-4 in Sep), this is 2026-08-31 22:00:00 (August 31!)
    # In Asia/Kolkata (UTC+5:30), this is 2026-09-01 07:30:00 (September 1!)
    t_tx = datetime(2026, 9, 1, 2, 0, 0, tzinfo=UTC)
    await _create_test_transaction(
        async_session, acc, Decimal("75.00"), occurred_at=t_tx
    )

    # Force database session timezone to Asia/Kolkata
    await async_session.execute(text("SET LOCAL timezone = 'Asia/Kolkata'"))

    repo = AnalyticsRepository()
    # Query with reporting timezone = America/New_York
    from_time = datetime(2026, 8, 31, 4, 0, 0, tzinfo=UTC)  # NY midnight Aug 31
    to_time = datetime(2026, 9, 2, 4, 0, 0, tzinfo=UTC)  # NY midnight Sep 2

    buckets = await repo.get_trend_buckets(
        async_session,
        namespace="SYNTHETIC",
        currency="INR",
        from_time=from_time,
        to_time=to_time,
        interval="day",
        tz_name="America/New_York",
    )

    assert len(buckets) == 2
    # The transaction must be counted in bucket 0 (August 31), not bucket 1
    assert buckets[0]["transaction_count"] == 1
    assert buckets[0]["total_debit_amount"] == Decimal("75.00")
    assert buckets[1]["transaction_count"] == 0


@pytest.mark.asyncio
async def test_dst_spring_forward_transition(async_session: AsyncSession) -> None:
    """Verify trends bucket correctly across DST spring-forward 23-hour day."""
    acc = await _create_test_account(async_session, "SYNTHETIC")

    # In America/New_York:
    # 2026-03-07: EST (UTC-5) -> midnight is 05:00 UTC
    # 2026-03-08: DST spring-forward day (23 hours) -> midnight is 05:00 UTC
    # 2026-03-09: EDT (UTC-4) -> midnight is 04:00 UTC
    t_mar7 = datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC)
    t_mar8 = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)
    t_mar9 = datetime(2026, 3, 9, 12, 0, 0, tzinfo=UTC)

    await _create_test_transaction(
        async_session, acc, Decimal("10.00"), occurred_at=t_mar7
    )
    await _create_test_transaction(
        async_session, acc, Decimal("20.00"), occurred_at=t_mar8
    )
    await _create_test_transaction(
        async_session, acc, Decimal("30.00"), occurred_at=t_mar9
    )

    repo = AnalyticsRepository()
    from_time = datetime(2026, 3, 7, 5, 0, 0, tzinfo=UTC)
    to_time = datetime(2026, 3, 10, 4, 0, 0, tzinfo=UTC)

    buckets = await repo.get_trend_buckets(
        async_session,
        namespace="SYNTHETIC",
        currency="INR",
        from_time=from_time,
        to_time=to_time,
        interval="day",
        tz_name="America/New_York",
    )

    assert len(buckets) == 3
    assert buckets[0]["transaction_count"] == 1
    assert buckets[0]["total_debit_amount"] == Decimal("10.00")

    assert buckets[1]["transaction_count"] == 1
    assert buckets[1]["total_debit_amount"] == Decimal("20.00")

    assert buckets[2]["transaction_count"] == 1
    assert buckets[2]["total_debit_amount"] == Decimal("30.00")


@pytest.mark.asyncio
async def test_category_and_merchant_aggregations(async_session: AsyncSession) -> None:
    """Verify category and merchant aggregations, percentage calculations, and non-merchant handling."""
    acc = await _create_test_account(async_session, "SYNTHETIC")
    m1 = await _create_test_merchant(
        async_session, name="Super Grocer", category="GROCERIES"
    )
    m2 = await _create_test_merchant(
        async_session, name="Gadget World", category="ELECTRONICS"
    )

    # 1. Debit to M1 in GROCERIES: 400.00
    await _create_test_transaction(
        async_session,
        acc,
        Decimal("400.00"),
        direction="DEBIT",
        category="GROCERIES",
        merchant=m1,
    )
    # 2. Debit to M2 in ELECTRONICS: 400.00
    await _create_test_transaction(
        async_session,
        acc,
        Decimal("400.00"),
        direction="DEBIT",
        category="ELECTRONICS",
        merchant=m2,
    )
    # 3. Debit with no merchant: 200.00 in OTHER
    await _create_test_transaction(
        async_session,
        acc,
        Decimal("200.00"),
        direction="DEBIT",
        category="OTHER",
        merchant=None,
    )

    service = AnalyticsService()
    user = _make_dummy_user()

    # Category Breakdown
    cat_resp = await service.get_categories(
        async_session,
        user=user,
        namespace="SYNTHETIC",
        currency="INR",
        direction="DEBIT",
    )
    assert cat_resp.total_directional_amount == "1000.00"
    assert len(cat_resp.categories) == 3

    # Merchant Breakdown
    merch_resp = await service.get_merchants(
        async_session, user=user, namespace="SYNTHETIC", currency="INR"
    )
    assert merch_resp.total_debit_amount == "1000.00"
    assert merch_resp.total_merchant_debit_amount == "800.00"
    assert merch_resp.non_merchant_debit_amount == "200.00"
    assert len(merch_resp.merchants) == 2

    # Percentage assertions for M1:
    # 400 / 1000 = 40.00% of total debit
    # 400 / 800 = 50.00% of merchant spend
    top_m = merch_resp.merchants[0]
    assert top_m.percentage_of_total_debit == "40.00"
    assert top_m.percentage_of_merchant_spend == "50.00"


@pytest.mark.asyncio
async def test_account_activity_and_empty_currency_semantics(
    async_session: AsyncSession,
) -> None:
    """Verify account-specific scoping and 200 OK with zeroed metrics for currency with no activity."""
    acc1 = await _create_test_account(async_session, "SYNTHETIC")
    acc2 = await _create_test_account(async_session, "SYNTHETIC")

    # Acc1 has INR transactions
    await _create_test_transaction(
        async_session, acc1, Decimal("100.00"), direction="DEBIT", currency="INR"
    )
    # Acc2 has INR transactions (must NOT leak into Acc1)
    await _create_test_transaction(
        async_session, acc2, Decimal("999.00"), direction="DEBIT", currency="INR"
    )

    service = AnalyticsService()
    user = _make_dummy_user()

    # 1. Query Acc1 in INR -> returns Acc1 summary only
    act_inr = await service.get_account_activity(
        async_session, user=user, account_id=acc1.id, currency="INR"
    )
    assert act_inr.summary.total_transaction_count == 1
    assert act_inr.summary.total_debit_amount == "100.00"
    assert act_inr.available_currencies == ["INR"]

    # 2. Query Acc1 in USD (no transactions in USD for Acc1) -> returns zeroed summary, 200 OK
    act_usd = await service.get_account_activity(
        async_session, user=user, account_id=acc1.id, currency="USD"
    )
    assert act_usd.summary.total_transaction_count == 0
    assert act_usd.summary.total_debit_amount == "0.00"
    assert act_usd.available_currencies == ["INR"]  # available currencies for Acc1


@pytest.mark.asyncio
async def test_unusual_spending_pre_pagination_count(
    async_session: AsyncSession,
) -> None:
    """Verify outlier selection math and pre-pagination count independence from limit and offset."""
    acc = await _create_test_account(async_session, "SYNTHETIC")

    # Seed baseline debit transactions:
    # 15 debits of 100.00 -> median debit = 100.00 with 8 outliers of 500.00
    for _ in range(15):
        await _create_test_transaction(
            async_session, acc, Decimal("100.00"), direction="DEBIT"
        )

    # Multiplier = 3.0 -> outlier threshold = 300.00
    # Seed 8 transactions exceeding threshold (500.00)
    for _ in range(8):
        await _create_test_transaction(
            async_session, acc, Decimal("500.00"), direction="DEBIT"
        )

    service = AnalyticsService()
    user = _make_dummy_user()

    # Page 1: limit=3, offset=0
    page1 = await service.get_unusual_spending(
        async_session,
        user=user,
        account_id=acc.id,
        currency="INR",
        multiplier=Decimal("3.0"),
        limit=3,
        offset=0,
    )
    assert page1.unusual_transaction_count == 8  # Total outliers before pagination
    assert page1.returned_count == 3
    assert len(page1.transactions) == 3

    # Page 3: limit=3, offset=6 (remaining 2 items)
    page3 = await service.get_unusual_spending(
        async_session,
        user=user,
        account_id=acc.id,
        currency="INR",
        multiplier=Decimal("3.0"),
        limit=3,
        offset=6,
    )
    assert page3.unusual_transaction_count == 8  # Still reports total 8!
    assert page3.returned_count == 2
    assert len(page3.transactions) == 2
