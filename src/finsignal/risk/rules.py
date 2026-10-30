"""Deterministic rule evaluation engine for financial transaction signals."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from finsignal.features.schemas import EvaluatedTransactionDTO, FeatureVector
from finsignal.risk.constants import RULE_POINTS_MAP
from finsignal.risk.schemas import RiskFactorCode, RiskSeverity


@dataclass(frozen=True, slots=True)
class FiredRule:
    """Internal representation of a fired risk heuristic rule."""

    code: RiskFactorCode
    label: str
    severity: RiskSeverity
    points: float
    description: str
    value_numeric: Decimal | None
    value_text: str | None
    evidence: dict[str, Any]


class RiskRuleEngine:
    """Evaluates transparent, deterministic heuristic rules against transaction features and facts."""

    def evaluate(
        self,
        features: FeatureVector,
        evaluated_tx: EvaluatedTransactionDTO,
    ) -> list[FiredRule]:
        """Evaluate deterministic rules and return fired rule descriptors."""
        fired: list[FiredRule] = []

        # 1. Cold-start account indicator (INFO severity)
        if features.is_cold_start == 1:
            fired.append(
                FiredRule(
                    code=RiskFactorCode.COLD_START_ACCOUNT,
                    label="Cold-Start Account",
                    severity=RiskSeverity.INFO,
                    points=RULE_POINTS_MAP["INFO"],
                    description=(
                        f"Account has sparse historical observations (< 3 transactions; age: "
                        f"{features.account_age_days:.1f} days). Behavioral baselines are neutral."
                    ),
                    value_numeric=Decimal(f"{features.account_age_days:.2f}"),
                    value_text=None,
                    evidence={
                        "account_age_days": features.account_age_days,
                        "is_cold_start": 1,
                        "has_direction_baseline": features.has_direction_baseline,
                    },
                )
            )

        # 2. High velocity bursts (5-minute and 1-hour windows)
        if features.velocity_5m_count >= 3 or features.velocity_1h_count >= 5:
            if features.velocity_5m_count >= 5:
                sev = RiskSeverity.CRITICAL
            elif features.velocity_5m_count >= 3:
                sev = RiskSeverity.HIGH
            else:
                sev = RiskSeverity.MEDIUM

            fired.append(
                FiredRule(
                    code=RiskFactorCode.HIGH_VELOCITY,
                    label="High Transaction Velocity",
                    severity=sev,
                    points=RULE_POINTS_MAP[sev.value],
                    description=(
                        f"Account initiated {features.velocity_5m_count} transactions in the last 5 minutes "
                        f"({features.velocity_1h_count} in last 1 hour)."
                    ),
                    value_numeric=Decimal(features.velocity_5m_count),
                    value_text=None,
                    evidence={
                        "velocity_5m_count": features.velocity_5m_count,
                        "velocity_1h_count": features.velocity_1h_count,
                        "velocity_5m_amount": features.velocity_5m_amount,
                        "velocity_1h_amount": features.velocity_1h_amount,
                    },
                )
            )

        # 3. Large amount deviation (only when historical direction baseline exists and not cold-start)
        if (
            features.has_direction_baseline == 1
            and features.is_cold_start == 0
            and (
                features.amount_vs_median_ratio >= 3.0 or features.amount_zscore >= 3.0
            )
        ):
            if features.amount_vs_median_ratio >= 10.0:
                sev = RiskSeverity.CRITICAL
            elif features.amount_vs_median_ratio >= 5.0:
                sev = RiskSeverity.HIGH
            else:
                sev = RiskSeverity.MEDIUM

            fired.append(
                FiredRule(
                    code=RiskFactorCode.LARGE_AMOUNT_DEVIATION,
                    label="Large Amount Deviation",
                    severity=sev,
                    points=RULE_POINTS_MAP[sev.value],
                    description=(
                        f"Transaction amount is {features.amount_vs_median_ratio:.1f}x the account's "
                        f"baseline median (z-score: {features.amount_zscore:.2f})."
                    ),
                    value_numeric=Decimal(f"{features.amount_vs_median_ratio:.4f}"),
                    value_text=None,
                    evidence={
                        "amount": features.amount,
                        "amount_vs_median_ratio": features.amount_vs_median_ratio,
                        "amount_zscore": features.amount_zscore,
                    },
                )
            )

        # 4. New device
        if features.has_device == 1 and features.is_new_device == 1:
            if (
                features.amount_vs_median_ratio >= 3.0
                or features.velocity_1h_count >= 3
            ):
                sev = RiskSeverity.HIGH
            else:
                sev = RiskSeverity.MEDIUM

            dev_str = str(evaluated_tx.device_id) if evaluated_tx.device_id else None
            fired.append(
                FiredRule(
                    code=RiskFactorCode.NEW_DEVICE,
                    label="New Device",
                    severity=sev,
                    points=RULE_POINTS_MAP[sev.value],
                    description="Transaction initiated from a device not previously associated with this account.",
                    value_numeric=Decimal(0),
                    value_text=dev_str,
                    evidence={
                        "device_id": dev_str,
                        "device_tx_count": features.device_tx_count,
                        "has_device": 1,
                    },
                )
            )

        # 5. New non-home location
        if (
            features.has_location == 1
            and features.is_new_location == 1
            and features.is_home_location == 0
        ):
            if features.is_new_device == 1:
                sev = RiskSeverity.HIGH
            else:
                sev = RiskSeverity.MEDIUM

            loc_str = (
                str(evaluated_tx.location_id) if evaluated_tx.location_id else None
            )
            fired.append(
                FiredRule(
                    code=RiskFactorCode.NEW_LOCATION,
                    label="New Location",
                    severity=sev,
                    points=RULE_POINTS_MAP[sev.value],
                    description="Transaction occurred from a new, non-home geographic location.",
                    value_numeric=Decimal(0),
                    value_text=loc_str,
                    evidence={
                        "location_id": loc_str,
                        "is_home_location": 0,
                        "location_tx_count": 0,
                    },
                )
            )

        # 6. Unusual transaction hour
        if features.is_unusual_hour == 1:
            if (
                evaluated_tx.direction == "DEBIT"
                and features.amount_vs_median_ratio >= 2.0
            ):
                sev = RiskSeverity.MEDIUM
            else:
                sev = RiskSeverity.LOW

            fired.append(
                FiredRule(
                    code=RiskFactorCode.UNUSUAL_TIME,
                    label="Unusual Transaction Hour",
                    severity=sev,
                    points=RULE_POINTS_MAP[sev.value],
                    description=(
                        f"Transaction occurred at hour {features.hour_of_day:02d}:00 UTC, which deviates "
                        f"from typical account active hours."
                    ),
                    value_numeric=Decimal(features.hour_of_day),
                    value_text=None,
                    evidence={
                        "hour_of_day": features.hour_of_day,
                        "day_of_week": features.day_of_week,
                        "is_weekend": features.is_weekend,
                    },
                )
            )

        # 7. Behavioral spending shift (new category with high spend share deviation)
        behavioral_shift_fired = False
        if (
            features.has_category == 1
            and features.is_new_category == 1
            and features.category_spend_share_30d < 0.05
            and features.amount_vs_mean_ratio >= 2.0
            and features.is_cold_start == 0
        ):
            behavioral_shift_fired = True
            if features.amount_vs_mean_ratio >= 5.0:
                sev = RiskSeverity.HIGH
            else:
                sev = RiskSeverity.MEDIUM

            cat_str = evaluated_tx.category or "Unknown"
            fired.append(
                FiredRule(
                    code=RiskFactorCode.BEHAVIORAL_SHIFT,
                    label="Behavioral Spending Shift",
                    severity=sev,
                    points=RULE_POINTS_MAP[sev.value],
                    description=(
                        f"Uncharacteristic spending in new category '{cat_str}' with "
                        f"significant monetary deviation ({features.amount_vs_mean_ratio:.1f}x account mean)."
                    ),
                    value_numeric=Decimal(f"{features.category_spend_share_30d:.4f}"),
                    value_text=cat_str,
                    evidence={
                        "category": cat_str,
                        "category_spend_share_30d": features.category_spend_share_30d,
                        "amount_vs_mean_ratio": features.amount_vs_mean_ratio,
                    },
                )
            )

        # 8. New merchant
        if features.has_merchant == 1 and features.is_new_merchant == 1:
            merch_str = (
                str(evaluated_tx.merchant_id) if evaluated_tx.merchant_id else None
            )
            fired.append(
                FiredRule(
                    code=RiskFactorCode.NEW_MERCHANT,
                    label="New Merchant",
                    severity=RiskSeverity.LOW,
                    points=RULE_POINTS_MAP["LOW"],
                    description="First transaction observed with this merchant.",
                    value_numeric=Decimal(0),
                    value_text=merch_str,
                    evidence={
                        "merchant_id": merch_str,
                        "merchant_tx_count": features.merchant_tx_count,
                    },
                )
            )

        # 9. New category (only if behavioral shift did not already fire to avoid double-counting)
        if (
            features.has_category == 1
            and features.is_new_category == 1
            and not behavioral_shift_fired
        ):
            cat_str = evaluated_tx.category or "Unknown"
            fired.append(
                FiredRule(
                    code=RiskFactorCode.NEW_CATEGORY,
                    label="New Category",
                    severity=RiskSeverity.LOW,
                    points=RULE_POINTS_MAP["LOW"],
                    description=f"First transaction observed in category '{cat_str}'.",
                    value_numeric=Decimal(0),
                    value_text=cat_str,
                    evidence={
                        "category": cat_str,
                        "is_new_category": 1,
                    },
                )
            )

        return fired

    def calculate_rule_score(self, fired_rules: list[FiredRule]) -> float:
        """Compute aggregate deterministic rule score bounded in [0.0, 100.0]."""
        total_points = sum(r.points for r in fired_rules)
        return min(100.0, float(total_points))
