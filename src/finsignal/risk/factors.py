"""Explainability factor generator producing evidence-grounded risk factors."""

from finsignal.risk.rules import FiredRule
from finsignal.risk.schemas import RiskFactorDTO, RiskSeverity

SEVERITY_ORDER: dict[RiskSeverity, int] = {
    RiskSeverity.CRITICAL: 5,
    RiskSeverity.HIGH: 4,
    RiskSeverity.MEDIUM: 3,
    RiskSeverity.LOW: 2,
    RiskSeverity.INFO: 1,
}


class RiskFactorGenerator:
    """Transforms fired deterministic rules into structured, investigator-facing explainability factors."""

    def generate(self, fired_rules: list[FiredRule]) -> list[RiskFactorDTO]:
        """Generate structured risk factors sorted deterministically by severity descending, then factor code."""
        factors: list[RiskFactorDTO] = []

        for rule in fired_rules:
            factor = RiskFactorDTO(
                code=rule.code,
                label=rule.label,
                severity=rule.severity,
                description=rule.description,
                value_numeric=rule.value_numeric,
                value_text=rule.value_text,
                evidence=rule.evidence,
            )
            factors.append(factor)

        # Deterministic sorting: severity descending, then code ascending
        factors.sort(key=lambda f: (-SEVERITY_ORDER.get(f.severity, 0), f.code.value))
        return factors
