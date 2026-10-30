"""Risk domain constants, factor taxonomy, and default configuration parameters."""

# Feature contract version
RISK_FEATURE_VERSION: str = "v1.0"

# Default risk scoring configuration version
DEFAULT_RISK_CONFIG_VERSION: str = "rc_v1.0"

# Default hybrid scoring weights (w_ml + w_rule == 1.0)
DEFAULT_WEIGHT_ML: float = 0.60
DEFAULT_WEIGHT_RULE: float = 0.40

# Risk-tier score boundaries [LOW: [0, 25), MEDIUM: [25, 50), HIGH: [50, 75), CRITICAL: [75, 100]]
DEFAULT_TIER_LOW_UPPER: float = 25.0
DEFAULT_TIER_MEDIUM_UPPER: float = 50.0
DEFAULT_TIER_HIGH_UPPER: float = 75.0

# Severity floor levels
SEVERITY_FLOOR_HIGH: float = 50.0
SEVERITY_FLOOR_CRITICAL: float = 75.0

# Fallback normalization anomaly score bounds when not in model metrics
DEFAULT_FALLBACK_SCORE_MIN: float = 0.30
DEFAULT_FALLBACK_SCORE_MAX: float = 0.80

# Maximum operational alert rate budget (5%)
MAX_OPERATIONAL_ALERT_RATE: float = 0.05

# Rule points by severity
RULE_POINTS_MAP: dict[str, float] = {
    "CRITICAL": 40.0,
    "HIGH": 25.0,
    "MEDIUM": 15.0,
    "LOW": 5.0,
    "INFO": 0.0,
}
