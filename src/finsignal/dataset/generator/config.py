"""Validated generator configuration model (ADR-029, ADR-065)."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from finsignal.dataset.generator.identifiers import (
    MAX_ACCOUNT_CAPACITY,
    MAX_DEVICE_CAPACITY,
    MAX_LOCATION_CAPACITY,
    MAX_MERCHANT_CAPACITY,
    MAX_TRANSACTION_CAPACITY,
)

NAMESPACE_REGEX = re.compile(r"^[A-Z0-9_]{3,64}$")

DEFAULT_SCENARIO_DISTRIBUTION: dict[str, float] = {
    "F001": 0.20,
    "F002": 0.15,
    "F003": 0.15,
    "F004": 0.10,
    "F005": 0.15,
    "F006": 0.15,
    "F007": 0.10,
}


class GeneratorConfig(BaseModel):
    """Configuration for deterministic reference entity and transaction generation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int = Field(
        default=20261004,
        ge=0,
        le=2**63 - 1,
        description="Explicit master seed for reproducible PRNG derivation.",
    )
    generator_version: str = Field(
        default="1.0.0",
        min_length=1,
        max_length=64,
        description="Explicit semantic generator version string.",
    )
    source_namespace: str = Field(
        default="SYNTHETIC",
        description="Target source namespace partition for generated accounts and transactions.",
    )
    account_count: int = Field(
        default=100,
        ge=1,
        le=MAX_ACCOUNT_CAPACITY,
        description=f"Number of synthetic accounts to generate (max {MAX_ACCOUNT_CAPACITY}).",
    )
    merchant_count: int = Field(
        default=50,
        ge=1,
        le=MAX_MERCHANT_CAPACITY,
        description=f"Number of synthetic merchants to generate (max {MAX_MERCHANT_CAPACITY}).",
    )
    device_count: int = Field(
        default=200,
        ge=1,
        le=MAX_DEVICE_CAPACITY,
        description=f"Number of synthetic devices to generate (max {MAX_DEVICE_CAPACITY}).",
    )
    location_count: int = Field(
        default=20,
        ge=1,
        le=MAX_LOCATION_CAPACITY,
        description=f"Number of geographic reference locations to generate (max {MAX_LOCATION_CAPACITY}).",
    )
    transaction_count: int = Field(
        default=5_000,
        ge=1,
        le=MAX_TRANSACTION_CAPACITY,
        description=f"Number of synthetic transactions to generate (max {MAX_TRANSACTION_CAPACITY}).",
    )
    fraud_rate: float = Field(
        default=0.03,
        ge=0.0,
        le=1.0,
        description="Target proportion of transactions involved in anomalous/fraud scenarios [0.0, 1.0].",
    )
    period_days: int = Field(
        default=90,
        ge=1,
        le=730,
        description="Observation duration in days for transaction synthesis.",
    )
    scenario_distribution: dict[str, float] = Field(
        default_factory=lambda: dict(DEFAULT_SCENARIO_DISTRIBUTION),
        description="Target proportional distribution across fraud scenarios F001-F007.",
    )

    @field_validator("source_namespace")
    @classmethod
    def validate_namespace_format(cls, v: str) -> str:
        """Enforce strict uppercase identifier syntax for source_namespace."""
        if not NAMESPACE_REGEX.match(v):
            raise ValueError(
                f"Invalid source_namespace '{v}'. Must match pattern ^[A-Z0-9_]{{3,64}}$"
            )
        return v

    @classmethod
    def small(cls, **kwargs: Any) -> "GeneratorConfig":
        """Small scale: 100 accounts, 5,000 transactions."""
        params: dict[str, Any] = {
            "account_count": 100,
            "merchant_count": 50,
            "device_count": 200,
            "location_count": 20,
            "transaction_count": 5_000,
        }
        params.update(kwargs)
        return cls(**params)

    @classmethod
    def medium(cls, **kwargs: Any) -> "GeneratorConfig":
        """Medium scale: 1,000 accounts, 50,000 transactions."""
        params: dict[str, Any] = {
            "account_count": 1_000,
            "merchant_count": 250,
            "device_count": 2_000,
            "location_count": 50,
            "transaction_count": 50_000,
        }
        params.update(kwargs)
        return cls(**params)

    @classmethod
    def full(cls, **kwargs: Any) -> "GeneratorConfig":
        """Full scale: 5,000 accounts, 500 merchants, 8,000 devices, 100 locations, 250,000 transactions."""
        params: dict[str, Any] = {
            "account_count": 5_000,
            "merchant_count": 500,
            "device_count": 8_000,
            "location_count": 100,
            "transaction_count": 250_000,
        }
        params.update(kwargs)
        return cls(**params)
