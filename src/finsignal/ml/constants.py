"""Constants for FinSignal Phase 7 Machine Learning and Anomaly Detection."""

from typing import Final

# Feature Contract Version
FEATURE_VERSION: Final[str] = "v1.0"

# Canonical Model Family Name
MODEL_FAMILY: Final[str] = "transaction_anomaly_isolation_forest"

# Default Model Seed
DEFAULT_RANDOM_SEED: Final[int] = 42

# Default Validation Alert Rate Cap
DEFAULT_MAX_ALERT_RATE: Final[float] = 0.05

# Strict, canonical 34-feature contract matching FeatureVector in Phase 6
CANONICAL_FEATURE_NAMES: Final[tuple[str, ...]] = (
    "amount",
    "amount_log",
    "account_age_days",
    "velocity_5m_count",
    "velocity_1h_count",
    "velocity_24h_count",
    "velocity_5m_amount",
    "velocity_1h_amount",
    "velocity_24h_amount",
    "amount_vs_mean_ratio",
    "amount_vs_median_ratio",
    "amount_zscore",
    "is_amount_different_from_constant_baseline",
    "has_direction_baseline",
    "has_zero_variance_baseline",
    "is_cold_start",
    "has_device",
    "is_new_device",
    "device_tx_count",
    "has_merchant",
    "is_new_merchant",
    "merchant_tx_count",
    "has_location",
    "is_home_location",
    "is_new_location",
    "location_tx_count",
    "location_frequency",
    "has_category",
    "is_new_category",
    "category_spend_share_30d",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_unusual_hour",
)
