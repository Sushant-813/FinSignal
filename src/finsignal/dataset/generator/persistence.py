"""Persistence service for generated reference entities adhering to SQLAlchemy 2.0 async conventions."""

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account, AccountDevice
from finsignal.common.exceptions import ConflictError
from finsignal.dataset.generator.schemas import GeneratedReferenceDataset
from finsignal.devices.models import Device
from finsignal.locations.models import Location
from finsignal.merchants.models import Merchant

logger = logging.getLogger("finsignal.dataset.generator.persistence")


@dataclass(frozen=True)
class ReferencePersistenceSummary:
    """Summary of persisted reference entities."""

    source_namespace: str
    locations_count: int
    merchants_count: int
    devices_count: int
    accounts_count: int
    account_devices_count: int
    account_id_map: dict[str, uuid.UUID]
    merchant_id_map: dict[str, uuid.UUID]
    device_id_map: dict[str, uuid.UUID]
    location_id_map: dict[str, uuid.UUID]


class ReferenceEntityPersistenceService:
    """Persists a GeneratedReferenceDataset into PostgreSQL with strict referential integrity.

    Persistence Policy & Entity Contract:
    --------------------------------------
    1. Locations (Geographic Reference Data):
       - Identity: (city, state, country)
       - Policy: If an existing location matches (city, state, country):
           - Coordinates (lat, lon) must match within 0.0001 precision.
           - Matching locations are safely reused without duplicating rows.
           - Conflicting coordinates raise ConflictError.
         Otherwise, a new Location row is created.

    2. Merchants (Commercial Reference Data):
       - Identity: external_merchant_id
       - Policy: If an existing merchant matches external_merchant_id:
           - Attributes (merchant_name, merchant_category, location_id) must match.
           - Matching merchants are safely reused.
           - Conflicting attributes raise ConflictError.
         Otherwise, a new Merchant row is created.

    3. Devices (Hardware Reference Data):
       - Identity: external_device_id
       - Policy: If an existing device matches external_device_id:
           - Attributes (device_type, operating_system) must match.
           - Matching devices are safely reused.
           - Conflicting attributes raise ConflictError.
         Otherwise, a new Device row is created.

    4. Accounts (Financial Accounts Scoped by Source Namespace):
       - Identity: (source_namespace, external_account_id)
       - Policy: Strictly partitioned by source_namespace. If ANY external_account_id
         in the dataset already exists within the target namespace, persistence is REJECTED
         with ConflictError. Accounts are never silently overwritten or merged.

    5. AccountDevices (Many-to-Many Associations):
       - Identity: (account_id, device_id)
       - Policy: Persisted fresh for the newly created accounts.

    Transaction Ownership Contract:
    -------------------------------
    - The persistence service executes within the caller's AsyncSession.
    - Atomicity: If any validation failure, conflict, or database error occurs during
      persistence, the service performs an explicit `await session.rollback()` to guarantee
      zero partial writes remain in the database session.
    - The caller retains final commit authority: the caller issues `await session.commit()`
      upon successful return of ReferencePersistenceSummary.
    """

    async def persist(
        self,
        session: AsyncSession,
        dataset: GeneratedReferenceDataset,
    ) -> ReferencePersistenceSummary:
        """Persist generated reference entities into the database atomically."""
        namespace = dataset.config.source_namespace

        try:
            # 1. Preflight Account Conflict Check in target namespace
            acc_business_ids = list(dataset.account_ids)
            stmt = (
                select(Account.external_account_id)
                .where(
                    Account.source_namespace == namespace,
                    Account.external_account_id.in_(acc_business_ids),
                )
                .limit(5)
            )
            raw_accounts = (await session.execute(stmt)).scalars().all()
            existing_accounts = [acc for acc in raw_accounts if acc is not None]
            if existing_accounts:
                details_str = ", ".join(existing_accounts)
                raise ConflictError(
                    message=(
                        f"Conflicting accounts already exist in namespace '{namespace}': {details_str}. "
                        "Refusing to overwrite existing financial accounts."
                    ),
                    details={
                        "namespace": namespace,
                        "conflicting_accounts": existing_accounts,
                    },
                )

            loc_id_map: dict[str, uuid.UUID] = {}
            merch_id_map: dict[str, uuid.UUID] = {}
            dev_id_map: dict[str, uuid.UUID] = {}
            acc_id_map: dict[str, uuid.UUID] = {}

            # 2. Locations: Reuse identical existing or insert new
            cities = list({loc.city for loc in dataset.locations})
            existing_loc_stmt = select(Location).where(Location.city.in_(cities))
            existing_loc_rows = (
                (await session.execute(existing_loc_stmt)).scalars().all()
            )
            existing_loc_map: dict[tuple[str, str | None, str], Location] = {
                (loc.city, loc.state, loc.country): loc for loc in existing_loc_rows
            }

            new_loc_models: list[tuple[str, Location]] = []
            for loc in dataset.locations:
                key = (loc.city, loc.state, loc.country)
                if key in existing_loc_map:
                    ex_loc = existing_loc_map[key]
                    lat_diff = (
                        abs(ex_loc.latitude - loc.latitude)
                        if (ex_loc.latitude is not None and loc.latitude is not None)
                        else Decimal(0)
                    )
                    lon_diff = (
                        abs(ex_loc.longitude - loc.longitude)
                        if (ex_loc.longitude is not None and loc.longitude is not None)
                        else Decimal(0)
                    )
                    if lat_diff > Decimal("0.0001") or lon_diff > Decimal("0.0001"):
                        raise ConflictError(
                            message=(
                                f"Location '{loc.city}, {loc.state}, {loc.country}' already exists with "
                                f"conflicting coordinates ({ex_loc.latitude}, {ex_loc.longitude}) vs "
                                f"({loc.latitude}, {loc.longitude})."
                            ),
                            details={
                                "city": loc.city,
                                "existing_lat": str(ex_loc.latitude),
                                "new_lat": str(loc.latitude),
                            },
                        )
                    loc_id_map[loc.location_id] = ex_loc.id
                else:
                    new_loc = Location(
                        city=loc.city,
                        state=loc.state,
                        country=loc.country,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                    )
                    session.add(new_loc)
                    new_loc_models.append((loc.location_id, new_loc))
                    existing_loc_map[key] = new_loc

            if new_loc_models:
                await session.flush()
                for loc_biz_id, new_l in new_loc_models:
                    loc_id_map[loc_biz_id] = new_l.id

            # 3. Merchants: Reuse identical existing or insert new
            merch_biz_ids = list(dataset.merchant_ids)
            existing_merch_stmt = select(Merchant).where(
                Merchant.external_merchant_id.in_(merch_biz_ids)
            )
            existing_merch_rows = (
                (await session.execute(existing_merch_stmt)).scalars().all()
            )
            existing_merch_map: dict[str, Merchant] = {
                m.external_merchant_id: m
                for m in existing_merch_rows
                if m.external_merchant_id is not None
            }

            new_merch_models: list[tuple[str, Merchant]] = []
            for m in dataset.merchants:
                target_loc_id = loc_id_map[m.location_id]
                if m.merchant_id in existing_merch_map:
                    ex_m = existing_merch_map[m.merchant_id]
                    if (
                        ex_m.merchant_name != m.merchant_name
                        or ex_m.merchant_category != m.merchant_category
                        or ex_m.location_id != target_loc_id
                    ):
                        raise ConflictError(
                            message=(
                                f"Merchant '{m.merchant_id}' already exists with conflicting attributes: "
                                f"existing ('{ex_m.merchant_name}', '{ex_m.merchant_category}') vs "
                                f"generated ('{m.merchant_name}', '{m.merchant_category}')."
                            ),
                            details={
                                "merchant_id": m.merchant_id,
                                "existing_name": ex_m.merchant_name,
                                "generated_name": m.merchant_name,
                            },
                        )
                    merch_id_map[m.merchant_id] = ex_m.id
                else:
                    new_m = Merchant(
                        external_merchant_id=m.merchant_id,
                        merchant_name=m.merchant_name,
                        merchant_category=m.merchant_category,
                        location_id=target_loc_id,
                    )
                    session.add(new_m)
                    new_merch_models.append((m.merchant_id, new_m))
                    existing_merch_map[m.merchant_id] = new_m

            if new_merch_models:
                await session.flush()
                for m_biz_id, new_merch in new_merch_models:
                    merch_id_map[m_biz_id] = new_merch.id

            # 4. Devices: Reuse identical existing or insert new
            dev_biz_ids = list(dataset.device_ids)
            existing_dev_stmt = select(Device).where(
                Device.external_device_id.in_(dev_biz_ids)
            )
            existing_dev_rows = (
                (await session.execute(existing_dev_stmt)).scalars().all()
            )
            existing_dev_map: dict[str, Device] = {
                d.external_device_id: d
                for d in existing_dev_rows
                if d.external_device_id is not None
            }

            new_dev_models: list[tuple[str, Device]] = []
            for d in dataset.devices:
                if d.device_id in existing_dev_map:
                    ex_d = existing_dev_map[d.device_id]
                    if (
                        ex_d.device_type != d.device_type
                        or ex_d.operating_system != d.operating_system
                    ):
                        raise ConflictError(
                            message=(
                                f"Device '{d.device_id}' already exists with conflicting attributes: "
                                f"existing ('{ex_d.device_type}', '{ex_d.operating_system}') vs "
                                f"generated ('{d.device_type}', '{d.operating_system}')."
                            ),
                            details={
                                "device_id": d.device_id,
                                "existing_type": ex_d.device_type,
                                "generated_type": d.device_type,
                            },
                        )
                    dev_id_map[d.device_id] = ex_d.id
                else:
                    new_d = Device(
                        external_device_id=d.device_id,
                        device_type=d.device_type,
                        operating_system=d.operating_system,
                        first_seen_at=d.first_seen_at,
                    )
                    session.add(new_d)
                    new_dev_models.append((d.device_id, new_d))
                    existing_dev_map[d.device_id] = new_d

            if new_dev_models:
                await session.flush()
                for d_biz_id, new_dev in new_dev_models:
                    dev_id_map[d_biz_id] = new_dev.id

            # 5. Accounts: Insert new accounts in target namespace
            account_models: list[Account] = []
            for a in dataset.accounts:
                home_loc_uuid = loc_id_map[a.home_location_id]
                a_model = Account(
                    source_namespace=a.source_namespace,
                    external_account_id=a.account_id,
                    account_type=a.account_type,
                    customer_age=a.customer_age,
                    home_location_id=home_loc_uuid,
                    status=a.status,
                    created_at=a.created_at,
                )
                session.add(a_model)
                account_models.append(a_model)

            await session.flush()
            for a, acc_m in zip(dataset.accounts, account_models, strict=True):
                acc_id_map[a.account_id] = acc_m.id

            # 6. AccountDevices: Insert relationships
            for ad in dataset.account_devices:
                acc_uuid = acc_id_map[ad.account_id]
                dev_uuid = dev_id_map[ad.device_id]
                ad_model = AccountDevice(
                    account_id=acc_uuid,
                    device_id=dev_uuid,
                    first_seen_at=ad.first_seen_at,
                    last_seen_at=ad.last_seen_at,
                    is_primary=ad.is_primary,
                )
                session.add(ad_model)

            await session.flush()

            logger.info(
                "Persisted reference dataset: namespace=%s accounts=%d merchants=%d devices=%d locations=%d",
                namespace,
                len(dataset.accounts),
                len(dataset.merchants),
                len(dataset.devices),
                len(dataset.locations),
            )

            return ReferencePersistenceSummary(
                source_namespace=namespace,
                locations_count=len(dataset.locations),
                merchants_count=len(dataset.merchants),
                devices_count=len(dataset.devices),
                accounts_count=len(dataset.accounts),
                account_devices_count=len(dataset.account_devices),
                account_id_map=acc_id_map,
                merchant_id_map=merch_id_map,
                device_id_map=dev_id_map,
                location_id_map=loc_id_map,
            )
        except Exception:
            await session.rollback()
            raise
