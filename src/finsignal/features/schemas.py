"""Domain schemas, immutable feature vectors, and evaluation contexts for Phase 6."""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from finsignal.features.constants import FEATURE_VERSION


class FeatureVector(BaseModel):
    """Immutable, validated feature vector containing exactly 34 model input features.

    Strict Contract:
    - version: v1.0
    - immutability: frozen=True
    - strict attributes: extra='forbid'
    - finite floats: NaN and +/-Inf are strictly rejected
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # 1. Amount features
    amount: float
    amount_log: float

    # 2. Account profile features
    account_age_days: float

    # 3. Transaction velocity (counts)
    velocity_5m_count: int
    velocity_1h_count: int
    velocity_24h_count: int

    # 4. Transaction velocity (direction- & currency-matched amounts)
    velocity_5m_amount: float
    velocity_1h_amount: float
    velocity_24h_amount: float

    # 5. Amount deviation (direction- & currency-matched)
    amount_vs_mean_ratio: float
    amount_vs_median_ratio: float
    amount_zscore: float
    is_amount_different_from_constant_baseline: int

    # 6. Baseline quality & cold-start indicators
    has_direction_baseline: int
    has_zero_variance_baseline: int
    is_cold_start: int

    # 7. Device familiarity
    has_device: int
    is_new_device: int
    device_tx_count: int

    # 8. Merchant familiarity
    has_merchant: int
    is_new_merchant: int
    merchant_tx_count: int

    # 9. Location familiarity
    has_location: int
    is_home_location: int
    is_new_location: int
    location_tx_count: int
    location_frequency: float

    # 10. Category behavior
    has_category: int
    is_new_category: int
    category_spend_share_30d: float

    # 11. Temporal behavior (UTC)
    hour_of_day: int
    day_of_week: int
    is_weekend: int
    is_unusual_hour: int

    @model_validator(mode="after")
    def validate_finite_numerical_fields(self) -> "FeatureVector":
        """Verify that all floating-point features are finite real numbers."""
        for name, value in self.__dict__.items():
            if isinstance(value, float) and not math.isfinite(value):
                msg = f"Feature '{name}' contains non-finite float value: {value}"
                raise ValueError(msg)
        return self


class FeatureMetadata(BaseModel):
    """Point-in-time calculation metadata and execution diagnostics.

    Kept strictly separated from FeatureVector to prevent diagnostic metadata
    from entering machine-learning inference feature vectors.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    feature_version: str = FEATURE_VERSION
    account_id: uuid.UUID
    transaction_id: uuid.UUID
    occurred_at: datetime
    calculated_at: datetime
    is_account_created_after_txn: bool
    diagnostics: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HistoricalTransactionDTO:
    """Lightweight facts of a historical transaction eligible for baseline computation."""

    id: uuid.UUID
    occurred_at: datetime
    amount: Decimal
    currency: str
    direction: str
    transaction_type: str
    merchant_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    category: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluatedTransactionDTO:
    """Facts of the transaction being evaluated at point-in-time."""

    id: uuid.UUID
    account_id: uuid.UUID
    occurred_at: datetime
    amount: Decimal
    currency: str
    direction: str
    transaction_type: str
    source_namespace: str = "SYNTHETIC"
    merchant_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    category: str | None = None


@dataclass(frozen=True, slots=True)
class AccountProfileDTO:
    """Account reference attributes for behavioral feature baseline evaluation."""

    id: uuid.UUID
    source_namespace: str
    home_location_id: uuid.UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LifetimeBaselineSummary:
    """Direction- and currency-matched lifetime historical statistics."""

    count: int
    mean: Decimal | None
    stddev: float | None
    median: Decimal | None
    total_lifetime_count: int
    seen_devices: frozenset[uuid.UUID] = field(default_factory=frozenset)
    seen_merchants: frozenset[uuid.UUID] = field(default_factory=frozenset)
    seen_locations: frozenset[uuid.UUID] = field(default_factory=frozenset)
    seen_categories: frozenset[str] = field(default_factory=frozenset)
    device_tx_counts: dict[uuid.UUID, int] = field(default_factory=dict)
    merchant_tx_counts: dict[uuid.UUID, int] = field(default_factory=dict)
    location_tx_counts: dict[uuid.UUID, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """Complete context required by the pure feature computation engine."""

    evaluated_transaction: EvaluatedTransactionDTO
    account_profile: AccountProfileDTO
    bounded_transactions: list[HistoricalTransactionDTO]
    lifetime_summary: LifetimeBaselineSummary | None = None


@dataclass(frozen=True, slots=True)
class FeatureEvaluationResult:
    """Composite container uniting the 34-feature vector and calculation metadata."""

    features: FeatureVector
    metadata: FeatureMetadata
