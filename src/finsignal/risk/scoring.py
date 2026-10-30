"""Hybrid risk scoring engine combining ML anomaly signals with deterministic rule signals."""

import math

from finsignal.risk.constants import (
    SEVERITY_FLOOR_CRITICAL,
    SEVERITY_FLOOR_HIGH,
)
from finsignal.risk.exceptions import RiskConfigurationError
from finsignal.risk.schemas import (
    RiskFactorDTO,
    RiskLevel,
    RiskScoringConfig,
    RiskSeverity,
)


class HybridScoringEngine:
    """Combines normalized ML anomaly signals and deterministic rule signals into a bounded prioritization score."""

    def __init__(self, config: RiskScoringConfig | None = None) -> None:
        self.config = config or RiskScoringConfig()
        self._validate_config(self.config)

    def _validate_config(self, config: RiskScoringConfig) -> None:
        """Verify that configuration weights and tier thresholds satisfy domain invariants."""
        if not math.isfinite(config.w_ml) or not math.isfinite(config.w_rule):
            msg = "Scoring weights must be finite real numbers."
            raise RiskConfigurationError(message=msg)

        if config.w_ml < 0.0 or config.w_rule < 0.0:
            msg = "Scoring weights must be non-negative."
            raise RiskConfigurationError(message=msg)

        weight_sum = config.w_ml + config.w_rule
        if abs(weight_sum - 1.0) > 1e-4:
            msg = f"Scoring weights must sum to 1.0; got {weight_sum:.4f}."
            raise RiskConfigurationError(message=msg)

        if not (
            0.0
            < config.tier_low_upper
            < config.tier_medium_upper
            < config.tier_high_upper
            < 100.0
        ):
            msg = (
                "Tier boundaries must strictly satisfy: "
                "0.0 < tier_low_upper < tier_medium_upper < tier_high_upper < 100.0."
            )
            raise RiskConfigurationError(message=msg)

    def calculate_score(
        self,
        normalized_ml_score: float,
        rule_score: float,
        factors: list[RiskFactorDTO],
    ) -> tuple[float, RiskLevel]:
        """Compute composite risk score and map to risk tier.

        Returns:
            tuple of (composite_score [0.00, 100.00], risk_level)
        """
        # Linear weighted baseline combination
        raw_composite = (self.config.w_ml * normalized_ml_score) + (
            self.config.w_rule * rule_score
        )

        # Optional evidence-gated severity floor
        if self.config.escalation_floor_enabled:
            severities = {f.severity for f in factors}
            if RiskSeverity.CRITICAL in severities:
                raw_composite = max(raw_composite, SEVERITY_FLOOR_CRITICAL)
            elif RiskSeverity.HIGH in severities:
                raw_composite = max(raw_composite, SEVERITY_FLOOR_HIGH)

        # Strict clamping within [0.00, 100.00] and 2-decimal precision
        score = round(max(0.0, min(100.0, raw_composite)), 2)

        # Tier mapping
        if score < self.config.tier_low_upper:
            level = RiskLevel.LOW
        elif score < self.config.tier_medium_upper:
            level = RiskLevel.MEDIUM
        elif score < self.config.tier_high_upper:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL

        return score, level
