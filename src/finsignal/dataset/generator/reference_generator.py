"""Deterministic reference entity generator (Locations, Merchants, Devices, Accounts)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from finsignal.dataset.generator.config import GeneratorConfig
from finsignal.dataset.generator.identifiers import (
    format_account_id,
    format_device_id,
    format_location_id,
    format_merchant_id,
)
from finsignal.dataset.generator.random_streams import get_entity_rng
from finsignal.dataset.generator.schemas import (
    GeneratedAccount,
    GeneratedAccountDevice,
    GeneratedDevice,
    GeneratedLocation,
    GeneratedMerchant,
    GeneratedReferenceDataset,
)

# Reference baseline catalog for geographic locations
_CURATED_CITIES: tuple[tuple[str, str, str, str, str], ...] = (
    ("Bengaluru", "Karnataka", "IND", "12.971599", "77.594566"),
    ("Mumbai", "Maharashtra", "IND", "19.076090", "72.877426"),
    ("Delhi", "Delhi", "IND", "28.704060", "77.102493"),
    ("Hyderabad", "Telangana", "IND", "17.385044", "78.486671"),
    ("Chennai", "Tamil Nadu", "IND", "13.082680", "80.270721"),
    ("Kolkata", "West Bengal", "IND", "22.572645", "88.363892"),
    ("Pune", "Maharashtra", "IND", "18.520430", "73.856743"),
    ("Ahmedabad", "Gujarat", "IND", "23.022505", "72.571365"),
    ("Jaipur", "Rajasthan", "IND", "26.912434", "75.787270"),
    ("Mysuru", "Karnataka", "IND", "12.295810", "76.639381"),
    ("Kochi", "Kerala", "IND", "9.931233", "76.267303"),
    ("Chandigarh", "Punjab", "IND", "30.733315", "76.779419"),
    ("Lucknow", "Uttar Pradesh", "IND", "26.846708", "80.946159"),
    ("Bhopal", "Madhya Pradesh", "IND", "23.259933", "77.412613"),
    ("Indore", "Madhya Pradesh", "IND", "22.719568", "75.857727"),
    ("Coimbatore", "Tamil Nadu", "IND", "11.016844", "76.955833"),
    ("Nagpur", "Maharashtra", "IND", "21.145800", "79.088158"),
    ("Visakhapatnam", "Andhra Pradesh", "IND", "17.686816", "83.218483"),
    ("Surat", "Gujarat", "IND", "21.170240", "72.831062"),
    ("Patna", "Bihar", "IND", "25.594095", "85.137566"),
)

# Merchant reference categories per DATASET_SPECIFICATION.md Section 14
_MERCHANT_CATEGORIES: tuple[str, ...] = (
    "FOOD",
    "GROCERIES",
    "SHOPPING",
    "ELECTRONICS",
    "TRAVEL",
    "HOTEL",
    "ENTERTAINMENT",
    "UTILITIES",
    "HEALTHCARE",
    "RENT",
    "INSURANCE",
    "SUBSCRIPTION",
    "OTHER",
)

_MERCHANT_NAME_PREFIXES: tuple[str, ...] = (
    "Apex",
    "Prime",
    "Metro",
    "City",
    "Blue",
    "Global",
    "Royal",
    "Evergreen",
    "Summit",
    "Swift",
    "Pioneer",
    "Star",
)

_DEVICE_TYPES: tuple[str, ...] = ("MOBILE", "DESKTOP", "TABLET", "POS")

_OPERATING_SYSTEMS: tuple[str, ...] = (
    "ANDROID",
    "IOS",
    "WINDOWS",
    "MACOS",
    "LINUX",
)

_ACCOUNT_TYPES: tuple[str, ...] = ("PERSONAL", "BUSINESS", "PREMIUM")
_ACCOUNT_TYPE_WEIGHTS: tuple[float, ...] = (0.75, 0.15, 0.10)

_ACCOUNT_STATUSES: tuple[str, ...] = ("ACTIVE", "SUSPENDED")
_ACCOUNT_STATUS_WEIGHTS: tuple[float, ...] = (0.95, 0.05)

# Fixed baseline epoch (2026-01-01 00:00:00 UTC) to decouple from wall-clock time
_BASE_EPOCH = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


class ReferenceEntityGenerator:
    """Generates deterministic reference entities adhering strictly to schema and specifications."""

    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config

    def generate_locations(self) -> list[GeneratedLocation]:
        """Generate location reference records with deterministic coordinates."""
        locations: list[GeneratedLocation] = []
        curated_len = len(_CURATED_CITIES)

        for i in range(1, self.config.location_count + 1):
            loc_id = format_location_id(i)
            # Use per-entity PRNG to ensure reproducibility and prefix stability
            rng = get_entity_rng(
                self.config.seed,
                "locations",
                i,
                self.config.generator_version,
            )

            city_idx = (i - 1) % curated_len
            city, state, country, base_lat, base_lon = _CURATED_CITIES[city_idx]

            # If location_count exceeds curated pool, append cycle suffix and micro-jitter
            if i > curated_len:
                cycle = (i - 1) // curated_len + 1
                city_name = f"{city} Sector {cycle}"
                # Small deterministic jitter within ~0.05 degrees
                jitter_lat = Decimal(str(round(rng.uniform(-0.05, 0.05), 6)))
                jitter_lon = Decimal(str(round(rng.uniform(-0.05, 0.05), 6)))
                lat = Decimal(base_lat) + jitter_lat
                lon = Decimal(base_lon) + jitter_lon
            else:
                city_name = city
                lat = Decimal(base_lat)
                lon = Decimal(base_lon)

            locations.append(
                GeneratedLocation(
                    location_id=loc_id,
                    city=city_name,
                    state=state,
                    country=country,
                    latitude=lat,
                    longitude=lon,
                )
            )
        return locations

    def generate_merchants(
        self, locations: list[GeneratedLocation]
    ) -> list[GeneratedMerchant]:
        """Generate merchant reference records referencing valid locations."""
        if not locations:
            raise ValueError("Cannot generate merchants without reference locations.")

        merchants: list[GeneratedMerchant] = []
        loc_count = len(locations)

        for i in range(1, self.config.merchant_count + 1):
            merch_id = format_merchant_id(i)
            rng = get_entity_rng(
                self.config.seed,
                "merchants",
                i,
                self.config.generator_version,
            )

            category = rng.choice(_MERCHANT_CATEGORIES)
            prefix = rng.choice(_MERCHANT_NAME_PREFIXES)
            merchant_name = f"{prefix} {category.capitalize()} #{i}"

            # Deterministic location assignment from generated locations
            loc_idx = rng.randint(0, loc_count - 1)
            location_id = locations[loc_idx].location_id

            merchants.append(
                GeneratedMerchant(
                    merchant_id=merch_id,
                    merchant_name=merchant_name,
                    merchant_category=category,
                    location_id=location_id,
                )
            )
        return merchants

    def generate_devices(self) -> list[GeneratedDevice]:
        """Generate device reference records with deterministic observation timestamps."""
        devices: list[GeneratedDevice] = []

        for i in range(1, self.config.device_count + 1):
            dev_id = format_device_id(i)
            rng = get_entity_rng(
                self.config.seed,
                "devices",
                i,
                self.config.generator_version,
            )

            device_type = rng.choice(_DEVICE_TYPES)
            # Ensure plausible OS per device type
            if device_type == "MOBILE":
                os_choice = rng.choice(["ANDROID", "IOS"])
            elif device_type == "DESKTOP":
                os_choice = rng.choice(["WINDOWS", "MACOS", "LINUX"])
            elif device_type == "TABLET":
                os_choice = rng.choice(["ANDROID", "IOS"])
            else:  # POS
                os_choice = rng.choice(["LINUX", "ANDROID", "WINDOWS"])

            # Deterministic first_seen_at offset within first 90 days of 2026
            day_offset = rng.randint(0, 90)
            sec_offset = rng.randint(0, 86399)
            first_seen = _BASE_EPOCH + timedelta(days=day_offset, seconds=sec_offset)

            devices.append(
                GeneratedDevice(
                    device_id=dev_id,
                    device_type=device_type,
                    operating_system=os_choice,
                    first_seen_at=first_seen,
                )
            )
        return devices

    def generate_accounts(
        self,
        locations: list[GeneratedLocation],
        devices: list[GeneratedDevice],
    ) -> tuple[list[GeneratedAccount], list[GeneratedAccountDevice]]:
        """Generate accounts and account_device associations with referential consistency."""
        if not locations:
            raise ValueError("Cannot generate accounts without reference locations.")
        if not devices:
            raise ValueError("Cannot generate accounts without reference devices.")

        accounts: list[GeneratedAccount] = []
        account_devices: list[GeneratedAccountDevice] = []

        loc_count = len(locations)
        dev_count = len(devices)

        for i in range(1, self.config.account_count + 1):
            acc_id = format_account_id(i)
            rng = get_entity_rng(
                self.config.seed,
                "accounts",
                i,
                self.config.generator_version,
            )

            account_type = rng.choices(_ACCOUNT_TYPES, weights=_ACCOUNT_TYPE_WEIGHTS)[0]
            status = rng.choices(_ACCOUNT_STATUSES, weights=_ACCOUNT_STATUS_WEIGHTS)[0]
            customer_age = rng.randint(18, 80) if account_type != "BUSINESS" else None

            # Primary home location assignment
            home_loc_idx = rng.randint(0, loc_count - 1)
            home_loc_id = locations[home_loc_idx].location_id

            # Deterministic creation date within first 60 days of 2026
            created_days = rng.randint(0, 60)
            created_secs = rng.randint(0, 86399)
            created_at = _BASE_EPOCH + timedelta(
                days=created_days, seconds=created_secs
            )

            accounts.append(
                GeneratedAccount(
                    account_id=acc_id,
                    source_namespace=self.config.source_namespace,
                    account_type=account_type,
                    customer_age=customer_age,
                    home_location_id=home_loc_id,
                    status=status,
                    created_at=created_at,
                )
            )

            # Assign 1 to 3 devices per account from the devices pool
            # To ensure progressive scale stability for account i, device selection
            # must not depend on other accounts. We sample device indices deterministically.
            num_devices = rng.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            # Primary device: deterministic choice based on account index modulo device count
            primary_dev_idx = (i - 1) % dev_count
            chosen_dev_indices = [primary_dev_idx]

            # Additional devices if needed
            while (
                len(chosen_dev_indices) < num_devices
                and len(chosen_dev_indices) < dev_count
            ):
                alt_idx = rng.randint(0, dev_count - 1)
                if alt_idx not in chosen_dev_indices:
                    chosen_dev_indices.append(alt_idx)

            for order, d_idx in enumerate(chosen_dev_indices):
                is_primary = order == 0
                dev = devices[d_idx]
                # Account-device first_seen_at must be >= max(account.created_at, device.first_seen_at)
                assoc_start = max(created_at, dev.first_seen_at)
                assoc_offset = rng.randint(0, 30)
                assoc_first_seen = assoc_start + timedelta(days=assoc_offset)
                last_seen_offset = rng.randint(1, 90)
                assoc_last_seen = assoc_first_seen + timedelta(days=last_seen_offset)

                account_devices.append(
                    GeneratedAccountDevice(
                        account_id=acc_id,
                        device_id=dev.device_id,
                        first_seen_at=assoc_first_seen,
                        last_seen_at=assoc_last_seen,
                        is_primary=is_primary,
                    )
                )

        return accounts, account_devices

    def generate(self) -> GeneratedReferenceDataset:
        """Execute complete reference dataset generation with internal referential validation."""
        locations = self.generate_locations()
        merchants = self.generate_merchants(locations)
        devices = self.generate_devices()
        accounts, account_devices = self.generate_accounts(locations, devices)

        dataset = GeneratedReferenceDataset(
            config=self.config,
            locations=locations,
            merchants=merchants,
            devices=devices,
            accounts=accounts,
            account_devices=account_devices,
        )

        # Integrity assertions
        self._validate_integrity(dataset)
        return dataset

    def _validate_integrity(self, dataset: GeneratedReferenceDataset) -> None:
        """Validate strict referential integrity across all generated entity collections."""
        loc_ids = dataset.location_ids
        dev_ids = dataset.device_ids
        acc_ids = dataset.account_ids

        # 1. Location references in merchants
        for m in dataset.merchants:
            if m.location_id not in loc_ids:
                raise ValueError(
                    f"Dangling location reference in merchant {m.merchant_id}: {m.location_id}"
                )

        # 2. Location references in accounts
        for a in dataset.accounts:
            if a.home_location_id not in loc_ids:
                raise ValueError(
                    f"Dangling location reference in account {a.account_id}: {a.home_location_id}"
                )

        # 3. Account-Device references
        account_has_primary: dict[str, int] = {acc_id: 0 for acc_id in acc_ids}
        for ad in dataset.account_devices:
            if ad.account_id not in acc_ids:
                raise ValueError(
                    f"Dangling account reference in account_devices: {ad.account_id}"
                )
            if ad.device_id not in dev_ids:
                raise ValueError(
                    f"Dangling device reference in account_devices: {ad.device_id}"
                )
            if ad.is_primary:
                account_has_primary[ad.account_id] += 1

        # 4. Each account must have exactly one primary device
        for acc_id, primary_count in account_has_primary.items():
            if primary_count != 1:
                raise ValueError(
                    f"Account {acc_id} has {primary_count} primary devices (expected exactly 1)."
                )
