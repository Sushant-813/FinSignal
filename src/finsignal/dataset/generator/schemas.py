"""In-memory domain schemas for generated reference entities."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from finsignal.dataset.generator.config import GeneratorConfig


@dataclass(frozen=True)
class GeneratedLocation:
    """Deterministic in-memory location entity."""

    location_id: str
    city: str
    state: str | None
    country: str
    latitude: Decimal | None
    longitude: Decimal | None


@dataclass(frozen=True)
class GeneratedMerchant:
    """Deterministic in-memory merchant entity."""

    merchant_id: str
    merchant_name: str
    merchant_category: str
    location_id: str


@dataclass(frozen=True)
class GeneratedDevice:
    """Deterministic in-memory device entity."""

    device_id: str
    device_type: str
    operating_system: str
    first_seen_at: datetime


@dataclass(frozen=True)
class GeneratedAccount:
    """Deterministic in-memory account entity."""

    account_id: str
    source_namespace: str
    account_type: str
    customer_age: int | None
    home_location_id: str
    status: str
    created_at: datetime


@dataclass(frozen=True)
class GeneratedAccountDevice:
    """Deterministic in-memory account-device association."""

    account_id: str
    device_id: str
    first_seen_at: datetime
    last_seen_at: datetime | None
    is_primary: bool


@dataclass(frozen=True)
class GeneratedReferenceDataset:
    """Container holding all generated reference entities for a configuration."""

    config: GeneratorConfig
    locations: list[GeneratedLocation]
    merchants: list[GeneratedMerchant]
    devices: list[GeneratedDevice]
    accounts: list[GeneratedAccount]
    account_devices: list[GeneratedAccountDevice]

    @property
    def location_ids(self) -> set[str]:
        return {loc.location_id for loc in self.locations}

    @property
    def merchant_ids(self) -> set[str]:
        return {m.merchant_id for m in self.merchants}

    @property
    def device_ids(self) -> set[str]:
        return {d.device_id for d in self.devices}

    @property
    def account_ids(self) -> set[str]:
        return {a.account_id for a in self.accounts}

    def to_dict(self) -> dict[str, Any]:
        """Serialize dataset to a deterministic JSON-compatible dictionary."""
        return {
            "config": self.config.model_dump(),
            "locations": [
                {
                    **asdict(loc),
                    "latitude": str(loc.latitude) if loc.latitude is not None else None,
                    "longitude": str(loc.longitude)
                    if loc.longitude is not None
                    else None,
                }
                for loc in self.locations
            ],
            "merchants": [asdict(m) for m in self.merchants],
            "devices": [
                {
                    **asdict(d),
                    "first_seen_at": d.first_seen_at.isoformat(),
                }
                for d in self.devices
            ],
            "accounts": [
                {
                    **asdict(a),
                    "created_at": a.created_at.isoformat(),
                }
                for a in self.accounts
            ],
            "account_devices": [
                {
                    **asdict(ad),
                    "first_seen_at": ad.first_seen_at.isoformat(),
                    "last_seen_at": ad.last_seen_at.isoformat()
                    if ad.last_seen_at is not None
                    else None,
                }
                for ad in self.account_devices
            ],
        }

    def to_json(self, *, indent: int | None = None, sort_keys: bool = True) -> str:
        """Serialize dataset to a canonical JSON string.

        Guarantees:
        - Sorted keys for deterministic byte representation.
        - ISO 8601 UTC datetimes.
        - Exact Decimal string representations for coordinates without float precision loss.
        """
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeneratedReferenceDataset":
        """Reconstruct a GeneratedReferenceDataset from a dictionary payload."""
        config = GeneratorConfig.model_validate(data["config"])
        locations = [
            GeneratedLocation(
                location_id=item["location_id"],
                city=item["city"],
                state=item.get("state"),
                country=item["country"],
                latitude=Decimal(item["latitude"])
                if item.get("latitude") is not None
                else None,
                longitude=Decimal(item["longitude"])
                if item.get("longitude") is not None
                else None,
            )
            for item in data["locations"]
        ]
        merchants = [
            GeneratedMerchant(
                merchant_id=item["merchant_id"],
                merchant_name=item["merchant_name"],
                merchant_category=item["merchant_category"],
                location_id=item["location_id"],
            )
            for item in data["merchants"]
        ]
        devices = [
            GeneratedDevice(
                device_id=item["device_id"],
                device_type=item["device_type"],
                operating_system=item["operating_system"],
                first_seen_at=datetime.fromisoformat(item["first_seen_at"]),
            )
            for item in data["devices"]
        ]
        accounts = [
            GeneratedAccount(
                account_id=item["account_id"],
                source_namespace=item["source_namespace"],
                account_type=item["account_type"],
                customer_age=item.get("customer_age"),
                home_location_id=item["home_location_id"],
                status=item["status"],
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in data["accounts"]
        ]
        account_devices = [
            GeneratedAccountDevice(
                account_id=item["account_id"],
                device_id=item["device_id"],
                first_seen_at=datetime.fromisoformat(item["first_seen_at"]),
                last_seen_at=datetime.fromisoformat(item["last_seen_at"])
                if item.get("last_seen_at") is not None
                else None,
                is_primary=item["is_primary"],
            )
            for item in data["account_devices"]
        ]
        return cls(
            config=config,
            locations=locations,
            merchants=merchants,
            devices=devices,
            accounts=accounts,
            account_devices=account_devices,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "GeneratedReferenceDataset":
        """Reconstruct a GeneratedReferenceDataset from a JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass(frozen=True)
class GeneratedTransaction:
    """Deterministic synthetic transaction entity."""

    transaction_id: str
    source_namespace: str
    account_id: str
    counterparty_account_id: str | None
    merchant_id: str | None
    device_id: str | None
    location_id: str | None
    occurred_at: datetime
    amount: Decimal
    currency: str
    transaction_type: str
    direction: str
    category: str | None
    payment_method: str | None
    channel: str | None


@dataclass(frozen=True)
class GeneratedGroundTruth:
    """Ground truth isolation metadata strictly decoupled from transactions."""

    transaction_id: str
    is_fraud: bool
    fraud_scenario: str | None
    scenario_instance_id: str | None
    anomaly_notes: str | None


@dataclass(frozen=True)
class DatasetMetadata:
    """Run metadata and summary statistics for a generated dataset."""

    generator_version: str
    seed: int
    source_namespace: str
    account_count: int
    merchant_count: int
    device_count: int
    location_count: int
    transaction_count: int
    fraud_count: int
    achieved_fraud_rate: float
    scenario_counts: dict[str, int]
    period_start: datetime
    period_end: datetime
    config: dict[str, Any]


@dataclass(frozen=True)
class GeneratedTransactionDataset:
    """Complete synthesized dataset containing references, transactions, and isolated ground truth."""

    reference_dataset: GeneratedReferenceDataset
    transactions: list[GeneratedTransaction]
    ground_truth: list[GeneratedGroundTruth]
    metadata: DatasetMetadata

    @property
    def config(self) -> GeneratorConfig:
        return self.reference_dataset.config
