"""Integration tests for ReferenceEntityPersistenceService on disposable PostgreSQL."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account, AccountDevice
from finsignal.common.exceptions import ConflictError
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.dataset.generator import (
    GeneratorConfig,
    ReferenceEntityGenerator,
    ReferenceEntityPersistenceService,
)
from finsignal.dataset.generator.schemas import (
    GeneratedDevice,
    GeneratedMerchant,
    GeneratedReferenceDataset,
)
from finsignal.devices.models import Device
from finsignal.locations.models import Location
from finsignal.merchants.models import Merchant


@pytest.fixture
async def async_session(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound to the disposable test database."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        yield session
        # Clean up database tables for complete test isolation
        try:
            await session.rollback()
            await session.execute(
                text(
                    "TRUNCATE TABLE account_devices, accounts, merchants, devices, locations CASCADE;"
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_persist_reference_entities(async_session: AsyncSession) -> None:
    """Verify persisting a GeneratedReferenceDataset creates expected database entities and relationships."""
    cfg = GeneratorConfig(
        seed=42,
        source_namespace="SYNTHETIC_INT_1",
        account_count=20,
        merchant_count=10,
        device_count=30,
        location_count=5,
    )
    generator = ReferenceEntityGenerator(cfg)
    dataset = generator.generate()

    service = ReferenceEntityPersistenceService()
    summary = await service.persist(async_session, dataset)
    await async_session.commit()

    assert summary.source_namespace == "SYNTHETIC_INT_1"
    assert summary.accounts_count == 20
    assert summary.merchants_count == 10
    assert summary.devices_count == 30
    assert summary.locations_count == 5

    # 1. Verify locations in DB
    loc_stmt = select(func.count(Location.id))
    loc_count = (await async_session.execute(loc_stmt)).scalar()
    assert loc_count == 5

    # 2. Verify merchants in DB and foreign keys to locations
    merch_stmt = select(Merchant).where(Merchant.external_merchant_id == "MERCH_00001")
    merch = (await async_session.execute(merch_stmt)).scalar_one()
    assert merch.location_id is not None
    assert merch.location_id in summary.location_id_map.values()

    # 3. Verify devices in DB
    dev_stmt = select(func.count(Device.id))
    dev_count = (await async_session.execute(dev_stmt)).scalar()
    assert dev_count == 30

    # 4. Verify accounts in DB and namespace
    acc_stmt = select(Account).where(
        Account.source_namespace == "SYNTHETIC_INT_1",
        Account.external_account_id == "ACC_000001",
    )
    acc = (await async_session.execute(acc_stmt)).scalar_one()
    assert acc.source_namespace == "SYNTHETIC_INT_1"
    assert acc.home_location_id in summary.location_id_map.values()

    # 5. Verify account_devices in DB
    ad_stmt = select(AccountDevice).where(AccountDevice.account_id == acc.id)
    ad_records = (await async_session.execute(ad_stmt)).scalars().all()
    assert len(ad_records) >= 1
    # Exactly one primary device
    assert sum(1 for ad in ad_records if ad.is_primary) == 1


@pytest.mark.asyncio
async def test_persist_conflict_on_duplicate_accounts(
    async_session: AsyncSession,
) -> None:
    """Verify attempting to re-persist existing accounts in the same namespace raises ConflictError."""
    cfg = GeneratorConfig(
        seed=101,
        source_namespace="SYNTHETIC_CONFLICT_TEST",
        account_count=5,
        merchant_count=2,
        device_count=5,
        location_count=2,
    )
    dataset = ReferenceEntityGenerator(cfg).generate()
    service = ReferenceEntityPersistenceService()

    # First persistence -> SUCCESS
    await service.persist(async_session, dataset)
    await async_session.commit()

    # Second persistence with same namespace and account IDs -> FAILS with ConflictError
    with pytest.raises(ConflictError) as exc_info:
        await service.persist(async_session, dataset)

    assert exc_info.value.code == "STATE_CONFLICT"
    assert "SYNTHETIC_CONFLICT_TEST" in str(exc_info.value)


@pytest.mark.asyncio
async def test_persist_distinct_namespace_reuses_shared_reference_entities(
    async_session: AsyncSession,
) -> None:
    """Verify distinct namespaces reuse matching locations, merchants, and devices without duplication."""
    cfg1 = GeneratorConfig(
        seed=202,
        source_namespace="SYNTHETIC_PARTITION_A",
        account_count=5,
        merchant_count=2,
        device_count=5,
        location_count=2,
    )
    cfg2 = GeneratorConfig(
        seed=202,
        source_namespace="SYNTHETIC_PARTITION_B",
        account_count=5,
        merchant_count=2,
        device_count=5,
        location_count=2,
    )

    ds1 = ReferenceEntityGenerator(cfg1).generate()
    ds2 = ReferenceEntityGenerator(cfg2).generate()
    service = ReferenceEntityPersistenceService()

    # Both persist successfully
    s1 = await service.persist(async_session, ds1)
    s2 = await service.persist(async_session, ds2)
    await async_session.commit()

    assert s1.source_namespace == "SYNTHETIC_PARTITION_A"
    assert s2.source_namespace == "SYNTHETIC_PARTITION_B"

    # Reference entities are reused, NOT duplicated
    loc_count = (await async_session.execute(select(func.count(Location.id)))).scalar()
    assert loc_count == 2

    merch_count = (
        await async_session.execute(select(func.count(Merchant.id)))
    ).scalar()
    assert merch_count == 2

    dev_count = (await async_session.execute(select(func.count(Device.id)))).scalar()
    assert dev_count == 5

    # Accounts are distinct across namespaces (5 + 5 = 10)
    acc_count = (await async_session.execute(select(func.count(Account.id)))).scalar()
    assert acc_count == 10

    # Confirm both account sets exist with their respective namespaces
    a1 = (
        await async_session.execute(
            select(Account).where(
                Account.source_namespace == "SYNTHETIC_PARTITION_A",
                Account.external_account_id == "ACC_000001",
            )
        )
    ).scalar_one_or_none()
    a2 = (
        await async_session.execute(
            select(Account).where(
                Account.source_namespace == "SYNTHETIC_PARTITION_B",
                Account.external_account_id == "ACC_000001",
            )
        )
    ).scalar_one_or_none()

    assert a1 is not None
    assert a2 is not None
    assert a1.id != a2.id


@pytest.mark.asyncio
async def test_persist_conflict_on_mismatched_merchant_attributes(
    async_session: AsyncSession,
) -> None:
    """Verify attempting to persist an existing merchant ID with conflicting attributes raises ConflictError."""
    cfg = GeneratorConfig(
        seed=303,
        source_namespace="SYNTHETIC_MERCH_CONFLICT_1",
        account_count=3,
        merchant_count=2,
        device_count=3,
        location_count=2,
    )
    dataset = ReferenceEntityGenerator(cfg).generate()
    service = ReferenceEntityPersistenceService()

    await service.persist(async_session, dataset)
    await async_session.commit()

    # Create a dataset with conflicting merchant name for MERCH_00001
    conflicting_merchants = [
        GeneratedMerchant(
            merchant_id="MERCH_00001",
            merchant_name="CONTRADICTORY NAME",
            merchant_category=dataset.merchants[0].merchant_category,
            location_id=dataset.merchants[0].location_id,
        )
    ]
    conflicting_dataset = GeneratedReferenceDataset(
        config=GeneratorConfig(
            seed=304,
            source_namespace="SYNTHETIC_MERCH_CONFLICT_2",
            account_count=1,
            merchant_count=1,
            device_count=1,
            location_count=2,
        ),
        locations=dataset.locations,
        merchants=conflicting_merchants,
        devices=[dataset.devices[0]],
        accounts=[
            dataset.accounts[0].__class__(
                account_id="ACC_000999",
                source_namespace="SYNTHETIC_MERCH_CONFLICT_2",
                account_type="PERSONAL",
                customer_age=30,
                home_location_id=dataset.locations[0].location_id,
                status="ACTIVE",
                created_at=dataset.accounts[0].created_at,
            )
        ],
        account_devices=[
            dataset.account_devices[0].__class__(
                account_id="ACC_000999",
                device_id=dataset.devices[0].device_id,
                first_seen_at=dataset.account_devices[0].first_seen_at,
                last_seen_at=None,
                is_primary=True,
            )
        ],
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.persist(async_session, conflicting_dataset)

    assert "MERCH_00001" in str(exc_info.value)
    assert exc_info.value.code == "STATE_CONFLICT"


@pytest.mark.asyncio
async def test_persist_conflict_on_mismatched_device_attributes(
    async_session: AsyncSession,
) -> None:
    """Verify attempting to persist an existing device ID with conflicting attributes raises ConflictError."""
    cfg = GeneratorConfig(
        seed=404,
        source_namespace="SYNTHETIC_DEV_CONFLICT_1",
        account_count=2,
        merchant_count=1,
        device_count=2,
        location_count=1,
    )
    dataset = ReferenceEntityGenerator(cfg).generate()
    service = ReferenceEntityPersistenceService()

    await service.persist(async_session, dataset)
    await async_session.commit()

    # Create a dataset with conflicting device_type for DEV_000001
    conflicting_devices = [
        GeneratedDevice(
            device_id="DEV_000001",
            device_type="CONTRADICTORY_TYPE",
            operating_system=dataset.devices[0].operating_system,
            first_seen_at=dataset.devices[0].first_seen_at,
        )
    ]
    conflicting_dataset = GeneratedReferenceDataset(
        config=GeneratorConfig(
            seed=405,
            source_namespace="SYNTHETIC_DEV_CONFLICT_2",
            account_count=1,
            merchant_count=1,
            device_count=1,
            location_count=1,
        ),
        locations=dataset.locations,
        merchants=dataset.merchants,
        devices=conflicting_devices,
        accounts=[
            dataset.accounts[0].__class__(
                account_id="ACC_000888",
                source_namespace="SYNTHETIC_DEV_CONFLICT_2",
                account_type="PERSONAL",
                customer_age=25,
                home_location_id=dataset.locations[0].location_id,
                status="ACTIVE",
                created_at=dataset.accounts[0].created_at,
            )
        ],
        account_devices=[
            dataset.account_devices[0].__class__(
                account_id="ACC_000888",
                device_id="DEV_000001",
                first_seen_at=dataset.account_devices[0].first_seen_at,
                last_seen_at=None,
                is_primary=True,
            )
        ],
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.persist(async_session, conflicting_dataset)

    assert "DEV_000001" in str(exc_info.value)
    assert exc_info.value.code == "STATE_CONFLICT"


@pytest.mark.asyncio
async def test_persist_atomic_rollback_on_failure_leaves_zero_partial_writes(
    async_session: AsyncSession,
) -> None:
    """Verify that if persistence fails midway, session is rolled back and zero partial records persist."""
    # Capture initial database counts
    init_loc_count = (
        await async_session.execute(select(func.count(Location.id)))
    ).scalar() or 0
    init_merch_count = (
        await async_session.execute(select(func.count(Merchant.id)))
    ).scalar() or 0
    init_dev_count = (
        await async_session.execute(select(func.count(Device.id)))
    ).scalar() or 0
    init_acc_count = (
        await async_session.execute(select(func.count(Account.id)))
    ).scalar() or 0

    cfg = GeneratorConfig(
        seed=505,
        source_namespace="SYNTHETIC_FAIL_ROLLBACK",
        account_count=2,
        merchant_count=2,
        device_count=2,
        location_count=2,
    )
    dataset = ReferenceEntityGenerator(cfg).generate()

    # Intentionally induce a conflict at the merchant step after locations were prepared
    corrupted_merchants = [
        GeneratedMerchant(
            merchant_id="MERCH_00001",
            merchant_name="CORRUPT",
            merchant_category=dataset.merchants[0].merchant_category,
            location_id="NON_EXISTENT_LOCATION_KEY",  # Will fail when resolving foreign key
        )
    ]
    corrupted_dataset = GeneratedReferenceDataset(
        config=cfg,
        locations=dataset.locations,
        merchants=corrupted_merchants,
        devices=dataset.devices,
        accounts=dataset.accounts,
        account_devices=dataset.account_devices,
    )

    service = ReferenceEntityPersistenceService()
    with pytest.raises(KeyError):
        await service.persist(async_session, corrupted_dataset)

    # Verify that database state has zero partial writes (counts remain exactly at baseline)
    post_loc_count = (
        await async_session.execute(select(func.count(Location.id)))
    ).scalar() or 0
    post_merch_count = (
        await async_session.execute(select(func.count(Merchant.id)))
    ).scalar() or 0
    post_dev_count = (
        await async_session.execute(select(func.count(Device.id)))
    ).scalar() or 0
    post_acc_count = (
        await async_session.execute(select(func.count(Account.id)))
    ).scalar() or 0

    assert post_loc_count == init_loc_count
    assert post_merch_count == init_merch_count
    assert post_dev_count == init_dev_count
    assert post_acc_count == init_acc_count
