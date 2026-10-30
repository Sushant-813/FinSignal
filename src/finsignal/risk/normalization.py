"""Deterministic piecewise linear normalization of Isolation Forest anomaly scores."""

import math
from collections.abc import Mapping
from typing import Any

from finsignal.risk.constants import (
    DEFAULT_FALLBACK_SCORE_MAX,
    DEFAULT_FALLBACK_SCORE_MIN,
)
from finsignal.risk.exceptions import RiskConfigurationError, RiskDomainError
from finsignal.risk.schemas import NormalizationParams


def resolve_normalization_bounds(
    threshold: float,
    metrics: Mapping[str, Any] | None = None,
    allow_fallback: bool = False,
) -> tuple[float, float]:
    """Resolve and validate empirical score bounds (s_min, s_max) from model metrics.

    Calibration Contract:
    - Normalization bounds must be derived empirically from the validation partition during training.
    - Missing, non-finite, or degenerate bounds raise RiskConfigurationError unless allow_fallback=True.
    - Enforces invariant: s_min < threshold < s_max.
    """
    if not math.isfinite(threshold):
        msg = f"Model threshold must be a finite real number; received {threshold}."
        raise RiskConfigurationError(message=msg)

    s_min: float | None = None
    s_max: float | None = None

    if metrics is not None:
        raw_min = metrics.get("score_min")
        raw_max = metrics.get("score_max")
        if isinstance(raw_min, (int, float)) and math.isfinite(float(raw_min)):
            s_min = float(raw_min)
        if isinstance(raw_max, (int, float)) and math.isfinite(float(raw_max)):
            s_max = float(raw_max)

    if s_min is None or s_max is None:
        if not allow_fallback:
            msg = (
                "Registered model lacks empirical calibration bounds ('score_min', 'score_max') "
                "in its metrics payload. Inference requires a calibrated model."
            )
            raise RiskConfigurationError(
                message=msg, code="UNAUTHENTICATED_CALIBRATION_BOUNDS"
            )
        s_min = DEFAULT_FALLBACK_SCORE_MIN
        s_max = DEFAULT_FALLBACK_SCORE_MAX

    # Invariant verification: s_min < threshold < s_max
    if s_min >= threshold:
        if not allow_fallback:
            msg = (
                f"Empirical calibration lower bound violated: requires score_min < threshold. "
                f"Received score_min={s_min}, threshold={threshold}."
            )
            raise RiskConfigurationError(message=msg)
        s_min = max(0.0, threshold - 0.25)

    if s_max <= threshold:
        if not allow_fallback:
            msg = (
                f"Empirical calibration upper bound violated: requires threshold < score_max. "
                f"Received threshold={threshold}, score_max={s_max}."
            )
            raise RiskConfigurationError(message=msg)
        s_max = threshold + 0.25

    return s_min, s_max


def normalize_ml_score(
    raw_score: float,
    threshold: float,
    s_min: float,
    s_max: float,
) -> tuple[float, NormalizationParams]:
    """Normalize continuous Isolation Forest anomaly score into a version-specific [0.0, 100.0] index.

    Guarantees:
    - Anchors: s_min -> 0.0, threshold -> 50.0, s_max -> 100.0.
    - Sub-threshold: linearly scaled in [0.0, 50.0].
    - Super-threshold: linearly scaled in [50.0, 100.0].
    - Monotonic: higher raw anomaly score yields higher normalized signal.
    - Clamping: output is strictly in [0.0, 100.0].
    - Non-finite rejection: NaN and +/-Inf immediately raise RiskDomainError.
    """
    if not math.isfinite(raw_score):
        msg = f"Non-finite anomaly score encountered: {raw_score}"
        raise RiskDomainError(message=msg, code="NON_FINITE_ANOMALY_SCORE")

    if (
        not math.isfinite(threshold)
        or not math.isfinite(s_min)
        or not math.isfinite(s_max)
    ):
        msg = "Normalization bounds and threshold must be finite real numbers."
        raise RiskConfigurationError(message=msg)

    if not (s_min < threshold < s_max):
        msg = (
            f"Invalid normalization calibration invariants: requires s_min < threshold < s_max. "
            f"Received s_min={s_min}, threshold={threshold}, s_max={s_max}."
        )
        raise RiskConfigurationError(message=msg)

    if raw_score <= threshold:
        scaled = 50.0 * (raw_score - s_min) / (threshold - s_min)
        norm_score = max(0.0, min(50.0, scaled))
    else:
        scaled = 50.0 + 50.0 * (raw_score - threshold) / (s_max - threshold)
        norm_score = max(50.0, min(100.0, scaled))

    params = NormalizationParams(
        method="piecewise_linear_anchored_v1",
        s_min=s_min,
        tau=threshold,
        s_max=s_max,
    )
    return round(norm_score, 4), params
