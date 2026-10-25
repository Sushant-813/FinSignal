"""PostgreSQL integration tests for FeatureRepository (Phase 6)."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
from finsignal.common.exceptions import NotFoundError
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.devices.models import Device
from finsignal.features.repository import FeatureRepository
from finsignal.locations.models import Location
from finsignal.merchants.models import Merchant
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


async def _create_account(
    session: AsyncSession,
    home_loc_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> Account:
    acc = Account(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_account_id=f"ACC_{uuid.uuid4().hex[:6]}",
        account_type="CHECKING",
        status="ACTIVE",
        home_location_id=home_loc_id,
        created_at=created_at or datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    session.add(acc)
    await session.commit()
    return acc


async def _create_tx(
    session: AsyncSession,
    account: Account,
    amount: Decimal,
    direction: str = "DEBIT",
    currency: str = "INR",
    occurred_at: datetime | None = None,
    tx_id: uuid.UUID | None = None,
    category: str | None = "GROCERIES",
    merchant_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
) -> Transaction:
    tx = Transaction(
        id=tx_id or uuid.uuid4(),
        source_namespace=account.source_namespace,
        external_transaction_id=f"TXN_{uuid.uuid4().hex[:8]}",
        account_id=account.id,
        amount=amount,
        direction=direction,
        currency=currency,
        occurred_at=occurred_at or datetime.now(UTC),
        category=category,
        merchant_id=merchant_id,
        device_id=device_id,
        location_id=location_id,
        transaction_type="PURCHASE",
    )
    session.add(tx)
    await session.commit()
    return tx


@pytest.mark.asyncio
async def test_bounded_historical_query_and_uuid_tie_breaking(
    async_session: AsyncSession,
) -> None:
    """Verify bounded window filtering, self-exclusion, and UUID sub-second tie-breaking in PostgreSQL."""
    acc = await _create_account(async_session)
    repo = FeatureRepository()

    same_t = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    # Deterministic UUID integer ordering
    id_low = uuid.UUID("00000000-0000-0000-0000-000000000001")
    id_eval = uuid.UUID("00000000-0000-0000-0000-000000000002")
    id_high = uuid.UUID("00000000-0000-0000-0000-000000000003")

    # 1. Historical transaction 2 hours prior: must be INCLUDED
    tx_prior = await _create_tx(
        async_session,
        acc,
        Decimal("100.00"),
        occurred_at=same_t - timedelta(hours=2),
    )

    # 2. Same timestamp, lower UUID: must be INCLUDED
    tx_same_low = await _create_tx(
        async_session,
        acc,
        Decimal("200.00"),
        occurred_at=same_t,
        tx_id=id_low,
    )

    # 3. Evaluated transaction itself: must be EXCLUDED
    eval_tx = await _create_tx(
        async_session,
        acc,
        Decimal("300.00"),
        occurred_at=same_t,
        tx_id=id_eval,
    )

    # 4. Same timestamp, higher UUID: must be EXCLUDED
    tx_same_high = await _create_tx(
        async_session,
        acc,
        Decimal("400.00"),
        occurred_at=same_t,
        tx_id=id_high,
    )

    # 5. Future transaction 1 minute later: must be EXCLUDED
    tx_future = await _create_tx(
        async_session,
        acc,
        Decimal("500.00"),
        occurred_at=same_t + timedelta(minutes=1),
    )

    # Execute repository query
    history = await repo.get_bounded_historical_transactions(
        async_session,
        account_id=acc.id,
        eval_occurred_at=eval_tx.occurred_at,
        eval_id=eval_tx.id,
        window_seconds=86400,
    )

    history_ids = [tx.id for tx in history]

    assert tx_prior.id in history_ids
    assert tx_same_low.id in history_ids
    assert eval_tx.id not in history_ids  # Self-exclusion
    assert tx_same_high.id not in history_ids  # Higher UUID excluded
    assert tx_future.id not in history_ids  # Future excluded
    assert len(history) == 2


@pytest.mark.asyncio
async def test_lifetime_baseline_summary_aggregation(
    async_session: AsyncSession,
) -> None:
    """Verify PostgreSQL aggregate calculations for lifetime mean, median, stddev, and entity counts."""
    acc = await _create_account(async_session)
    repo = FeatureRepository()

    t_eval = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)

    dev1 = uuid.uuid4()
    merch1 = uuid.uuid4()
    loc1 = uuid.uuid4()

    # Create dummy reference entities
    async_session.add(Device(id=dev1, external_device_id="DEV_1"))
    async_session.add(
        Merchant(
            id=merch1,
            merchant_name="Store 1",
            merchant_category="FOOD",
            external_merchant_id="MERCH_1",
        )
    )
    async_session.add(Location(id=loc1, city="Mumbai", country="IND"))
    await async_session.commit()

    # Seed 4 DEBITs in INR: [100.00, 200.00, 300.00, 400.00]
    # Mean = 250.00, Median = 250.00
    for i, amt in enumerate(
        [
            Decimal("100.00"),
            Decimal("200.00"),
            Decimal("300.00"),
            Decimal("400.00"),
        ]
    ):
        await _create_tx(
            async_session,
            acc,
            amt,
            direction="DEBIT",
            currency="INR",
            occurred_at=t_eval - timedelta(days=4 - i),
            device_id=dev1,
            merchant_id=merch1,
            location_id=loc1,
            category="FOOD",
        )

    # Seed 1 CREDIT in INR (should NOT enter debit baseline)
    await _create_tx(
        async_session,
        acc,
        Decimal("50000.00"),
        direction="CREDIT",
        currency="INR",
        occurred_at=t_eval - timedelta(days=2),
    )

    # Seed 1 DEBIT in USD (should NOT enter INR debit baseline)
    await _create_tx(
        async_session,
        acc,
        Decimal("50.00"),
        direction="DEBIT",
        currency="USD",
        occurred_at=t_eval - timedelta(days=1),
    )

    eval_tx = await _create_tx(
        async_session,
        acc,
        Decimal("600.00"),
        direction="DEBIT",
        currency="INR",
        occurred_at=t_eval,
    )

    summary = await repo.get_lifetime_baseline_summary(
        async_session,
        account_id=acc.id,
        currency="INR",
        direction="DEBIT",
        eval_occurred_at=eval_tx.occurred_at,
        eval_id=eval_tx.id,
    )

    assert summary.count == 4
    assert summary.mean == Decimal("250.00")
    assert summary.median == Decimal("250.00")
    assert summary.stddev is not None
    assert summary.total_lifetime_count == 6  # 4 debits + 1 credit + 1 USD debit
    assert dev1 in summary.seen_devices
    assert summary.device_tx_counts[dev1] == 4
    assert merch1 in summary.seen_merchants
    assert loc1 in summary.seen_locations
    assert "FOOD" in summary.seen_categories


@pytest.mark.asyncio
async def test_assemble_evaluation_context_and_not_found_handling(
    async_session: AsyncSession,
) -> None:
    """Verify context assembly and NotFoundError on missing IDs."""
    acc = await _create_account(async_session)
    repo = FeatureRepository()

    tx = await _create_tx(async_session, acc, Decimal("500.00"))

    context = await repo.assemble_evaluation_context(async_session, tx.id)
    assert context.evaluated_transaction.id == tx.id
    assert context.account_profile.id == acc.id
    assert context.lifetime_summary is not None

    with pytest.raises(NotFoundError) as exc_info:
        await repo.assemble_evaluation_context(async_session, uuid.uuid4())
    assert exc_info.value.code == "TRANSACTION_NOT_FOUND"
