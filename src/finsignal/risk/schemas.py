"""Pydantic schemas and domain contracts for Phase 8 Risk Analysis & Explainability."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from finsignal.risk.constants import (
    DEFAULT_RISK_CONFIG_VERSION,
    DEFAULT_TIER_HIGH_UPPER,
    DEFAULT_TIER_LOW_UPPER,
    DEFAULT_TIER_MEDIUM_UPPER,
    DEFAULT_WEIGHT_ML,
    DEFAULT_WEIGHT_RULE,
)


class RiskLevel(StrEnum):
    """Categorical risk tiers for investigation prioritization."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskSeverity(StrEnum):
    """Severity classification for individual risk factors."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskFactorCode(StrEnum):
    """Canonical machine-readable risk factor identifiers."""

    NEW_DEVICE = "NEW_DEVICE"
    NEW_LOCATION = "NEW_LOCATION"
    UNUSUAL_TIME = "UNUSUAL_TIME"
    HIGH_VELOCITY = "HIGH_VELOCITY"
    LARGE_AMOUNT_DEVIATION = "LARGE_AMOUNT_DEVIATION"
    BEHAVIORAL_SHIFT = "BEHAVIORAL_SHIFT"
    NEW_MERCHANT = "NEW_MERCHANT"
    NEW_CATEGORY = "NEW_CATEGORY"
    COLD_START_ACCOUNT = "COLD_START_ACCOUNT"


class RiskFactorDTO(BaseModel):
    """Structured, verifiable reason supporting a risk analysis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: RiskFactorCode
    label: str = Field(description="Human-readable title of the risk factor")
    severity: RiskSeverity
    description: str = Field(description="Investigator-facing factual explanation")
    value_numeric: Decimal | None = Field(
        default=None, description="Measured quantitative value (e.g. ratio, count)"
    )
    value_text: str | None = Field(
        default=None, description="Measured qualitative value (e.g. entity identifier)"
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="Verifiable point-in-time feature snapshot"
    )


class RiskScoringConfig(BaseModel):
    """Immutable, versioned configuration contract for hybrid scoring and thresholds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    config_version: str = Field(
        default=DEFAULT_RISK_CONFIG_VERSION,
        min_length=1,
        max_length=18,
        description="Base configuration version tag. Max length 18 ensures effective_config_version fits in VARCHAR(32).",
    )
    rule_policy_version: str = Field(default="rp_v1.0", min_length=1, max_length=16)
    scoring_algorithm_version: str = Field(
        default="hybrid_linear_v1", min_length=1, max_length=24
    )
    normalization_policy: str = Field(
        default="anchored_piecewise_v1", min_length=1, max_length=24
    )
    w_ml: float = Field(default=DEFAULT_WEIGHT_ML, ge=0.0, le=1.0)
    w_rule: float = Field(default=DEFAULT_WEIGHT_RULE, ge=0.0, le=1.0)
    tier_low_upper: float = Field(default=DEFAULT_TIER_LOW_UPPER, ge=0.0, le=100.0)
    tier_medium_upper: float = Field(
        default=DEFAULT_TIER_MEDIUM_UPPER, ge=0.0, le=100.0
    )
    tier_high_upper: float = Field(default=DEFAULT_TIER_HIGH_UPPER, ge=0.0, le=100.0)
    escalation_floor_enabled: bool = False
    critical_factor_escalation: bool = False

    @property
    def effective_config_version(self) -> str:
        """Deterministic effective configuration identity incorporating all result-affecting settings.

        Computes a stable 12-char SHA-256 fingerprint of weights, tiers, floor flags, rule policy,
        scoring algorithm, and normalization policy versions, appending it to config_version.
        Uses repr() for exact float representation to prevent lossy float formatting collisions.
        Total length is <= 32 chars (e.g. 'rc_v1.0#a1b2c3d4e5f6').
        """
        import hashlib

        payload = (
            f"v={self.config_version}|"
            f"rp={self.rule_policy_version}|"
            f"algo={self.scoring_algorithm_version}|"
            f"norm={self.normalization_policy}|"
            f"w_ml={repr(self.w_ml)}|w_rule={repr(self.w_rule)}|"
            f"tiers={repr(self.tier_low_upper)},{repr(self.tier_medium_upper)},{repr(self.tier_high_upper)}|"
            f"floor={int(self.escalation_floor_enabled)}|"
            f"crit={int(self.critical_factor_escalation)}"
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"{self.config_version}#{digest}"


class NormalizationParams(BaseModel):
    """Documented parameters and metadata for ML score normalization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    method: str = "piecewise_linear_anchored_v1"
    s_min: float
    tau: float
    s_max: float


class RiskAnalysisResponse(BaseModel):
    """Complete risk assessment response for a transaction."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: uuid.UUID
    transaction_id: uuid.UUID
    model_version_id: uuid.UUID
    model_version: str = Field(description="Semantic model version (e.g. 1.0.0)")
    config_version: str = Field(description="Scoring configuration version identifier")
    feature_vector_hash: str = Field(
        description="SHA-256 fingerprint of input features and context"
    )
    score: float = Field(
        ge=0.0,
        le=100.0,
        description="Prioritization risk score strictly within [0.0, 100.0]",
    )
    risk_level: RiskLevel
    ml_anomaly_score: float = Field(
        description="Raw Isolation Forest anomaly score S(X)"
    )
    ml_threshold: float = Field(description="Model operating decision threshold tau*")
    normalized_ml_score: float = Field(
        description="Normalized version-specific ML anomaly signal [0, 100]"
    )
    rule_score: float = Field(description="Deterministic rule signal score [0, 100]")
    normalization_params: dict[str, Any] = Field(
        description="Normalization parameters metadata"
    )
    factors: list[RiskFactorDTO]
    created_at: datetime


class RiskAnalyzeRequest(BaseModel):
    """Payload for requesting on-demand transaction risk analysis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_version_id: uuid.UUID | None = Field(
        default=None,
        description="Optional explicit model version UUID. If omitted, uses active model.",
    )
