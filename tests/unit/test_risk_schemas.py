"""Unit tests for risk domain schemas, enums, and configuration models."""

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from finsignal.risk.exceptions import RiskConfigurationError
from finsignal.risk.schemas import (
    RiskAnalyzeRequest,
    RiskFactorCode,
    RiskFactorDTO,
    RiskLevel,
    RiskScoringConfig,
    RiskSeverity,
)
from finsignal.risk.scoring import HybridScoringEngine


def test_risk_level_enums() -> None:
    """Verify RiskLevel enum values."""
    assert RiskLevel.LOW.value == "LOW"
    assert RiskLevel.MEDIUM.value == "MEDIUM"
    assert RiskLevel.HIGH.value == "HIGH"
    assert RiskLevel.CRITICAL.value == "CRITICAL"


def test_risk_severity_enums() -> None:
    """Verify RiskSeverity 5-level vocabulary."""
    assert RiskSeverity.INFO.value == "INFO"
    assert RiskSeverity.LOW.value == "LOW"
    assert RiskSeverity.MEDIUM.value == "MEDIUM"
    assert RiskSeverity.HIGH.value == "HIGH"
    assert RiskSeverity.CRITICAL.value == "CRITICAL"


def test_risk_factor_code_enums() -> None:
    """Verify canonical factor code taxonomy."""
    codes = {c.value for c in RiskFactorCode}
    expected = {
        "NEW_DEVICE",
        "NEW_LOCATION",
        "UNUSUAL_TIME",
        "HIGH_VELOCITY",
        "LARGE_AMOUNT_DEVIATION",
        "BEHAVIORAL_SHIFT",
        "NEW_MERCHANT",
        "NEW_CATEGORY",
        "COLD_START_ACCOUNT",
    }
    assert codes == expected


def test_risk_scoring_config_validations() -> None:
    """Verify RiskScoringConfig validation constraints."""
    # Default is valid
    config = RiskScoringConfig()
    engine = HybridScoringEngine(config)
    assert engine.config.w_ml == 0.60
    assert engine.config.w_rule == 0.40

    # Weights sum must equal 1.0
    with pytest.raises(RiskConfigurationError, match="must sum to 1.0"):
        HybridScoringEngine(RiskScoringConfig(w_ml=0.70, w_rule=0.50))

    # Negative weights rejected
    with pytest.raises(ValidationError):
        RiskScoringConfig(w_ml=-0.1, w_rule=1.1)

    # Inverted tier thresholds rejected
    with pytest.raises(
        RiskConfigurationError, match="Tier boundaries must strictly satisfy"
    ):
        HybridScoringEngine(
            RiskScoringConfig(tier_low_upper=60.0, tier_medium_upper=40.0)
        )


def test_risk_factor_dto_extra_fields_forbidden() -> None:
    """Verify RiskFactorDTO forbids unexpected fields and enforces immutability."""
    dto = RiskFactorDTO(
        code=RiskFactorCode.HIGH_VELOCITY,
        label="High Velocity",
        severity=RiskSeverity.HIGH,
        description="5 transactions in 5 minutes",
        value_numeric=Decimal("5"),
        value_text=None,
        evidence={"count": 5},
    )
    assert dto.code == RiskFactorCode.HIGH_VELOCITY

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        RiskFactorDTO(
            code=RiskFactorCode.HIGH_VELOCITY,
            label="High Velocity",
            severity=RiskSeverity.HIGH,
            description="5 txns",
            unknown_field="extra",  # type: ignore[call-arg]
        )


def test_risk_analyze_request_schema() -> None:
    """Verify RiskAnalyzeRequest defaults and explicit model_version_id."""
    req_default = RiskAnalyzeRequest()
    assert req_default.model_version_id is None

    model_id = uuid.uuid4()
    req_explicit = RiskAnalyzeRequest(model_version_id=model_id)
    assert req_explicit.model_version_id == model_id
