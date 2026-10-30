"""Unit tests for piecewise linear ML anomaly score normalization."""

import pytest

from finsignal.risk.exceptions import RiskConfigurationError, RiskDomainError
from finsignal.risk.normalization import (
    normalize_ml_score,
    resolve_normalization_bounds,
)


def test_normalization_anchors() -> None:
    """Verify exact anchor mappings: s_min -> 0.0, tau -> 50.0, s_max -> 100.0."""
    s_min, tau, s_max = 0.30, 0.55, 0.80

    norm_min, _ = normalize_ml_score(
        raw_score=s_min, threshold=tau, s_min=s_min, s_max=s_max
    )
    assert norm_min == 0.0

    norm_tau, _ = normalize_ml_score(
        raw_score=tau, threshold=tau, s_min=s_min, s_max=s_max
    )
    assert norm_tau == 50.0

    norm_max, _ = normalize_ml_score(
        raw_score=s_max, threshold=tau, s_min=s_min, s_max=s_max
    )
    assert norm_max == 100.0


def test_normalization_sub_and_super_threshold() -> None:
    """Verify linear scaling in sub-threshold [0, 50] and super-threshold [50, 100] regions."""
    s_min, tau, s_max = 0.30, 0.50, 0.70

    # Midpoint of sub-threshold: 0.40 -> 25.0
    norm_mid_sub, params_sub = normalize_ml_score(0.40, tau, s_min, s_max)
    assert norm_mid_sub == 25.0
    assert params_sub.tau == 0.50

    # Midpoint of super-threshold: 0.60 -> 75.0
    norm_mid_super, _ = normalize_ml_score(0.60, tau, s_min, s_max)
    assert norm_mid_super == 75.0


def test_normalization_monotonicity() -> None:
    """Verify that normalized output is strictly monotonic with respect to input."""
    s_min, tau, s_max = 0.20, 0.50, 0.80
    raw_inputs = [0.20, 0.25, 0.35, 0.50, 0.55, 0.65, 0.75, 0.80]

    outputs = [normalize_ml_score(x, tau, s_min, s_max)[0] for x in raw_inputs]
    for i in range(len(outputs) - 1):
        assert outputs[i] <= outputs[i + 1]


def test_normalization_clamping_extreme_outliers() -> None:
    """Verify that extreme outliers below s_min or above s_max are clamped to [0, 100]."""
    s_min, tau, s_max = 0.30, 0.50, 0.70

    # Outlier below s_min
    norm_low, _ = normalize_ml_score(0.10, tau, s_min, s_max)
    assert norm_low == 0.0

    # Outlier above s_max
    norm_high, _ = normalize_ml_score(0.99, tau, s_min, s_max)
    assert norm_high == 100.0


def test_normalization_non_finite_rejection() -> None:
    """Verify that NaN and +/-Inf raw scores raise RiskDomainError."""
    with pytest.raises(RiskDomainError, match="Non-finite anomaly score"):
        normalize_ml_score(float("nan"), 0.50, 0.30, 0.70)

    with pytest.raises(RiskDomainError, match="Non-finite anomaly score"):
        normalize_ml_score(float("inf"), 0.50, 0.30, 0.70)

    with pytest.raises(RiskDomainError, match="Non-finite anomaly score"):
        normalize_ml_score(float("-inf"), 0.50, 0.30, 0.70)


def test_normalization_invalid_calibration_invariants() -> None:
    """Verify that invalid calibration order raises RiskConfigurationError."""
    # tau <= s_min
    with pytest.raises(
        RiskConfigurationError, match="requires s_min < threshold < s_max"
    ):
        normalize_ml_score(0.50, threshold=0.30, s_min=0.40, s_max=0.70)

    # s_max <= tau
    with pytest.raises(
        RiskConfigurationError, match="requires s_min < threshold < s_max"
    ):
        normalize_ml_score(0.50, threshold=0.60, s_min=0.30, s_max=0.55)


def test_resolve_normalization_bounds_empirical() -> None:
    """Verify resolve_normalization_bounds extracts genuine empirical metrics."""
    metrics = {"score_min": 0.25, "score_max": 0.85}
    s_min, s_max = resolve_normalization_bounds(0.50, metrics)
    assert s_min == 0.25
    assert s_max == 0.85


def test_resolve_normalization_bounds_missing_raises_error() -> None:
    """Verify resolve_normalization_bounds rejects missing metrics when allow_fallback=False."""
    with pytest.raises(
        RiskConfigurationError, match="lacks empirical calibration bounds"
    ):
        resolve_normalization_bounds(0.50, None, allow_fallback=False)

    with pytest.raises(
        RiskConfigurationError, match="lacks empirical calibration bounds"
    ):
        resolve_normalization_bounds(0.50, {"score_min": 0.20}, allow_fallback=False)


def test_resolve_normalization_bounds_invariant_violations_raise_error() -> None:
    """Verify invariant violations (s_min >= threshold or s_max <= threshold) raise error."""
    # s_min >= threshold
    with pytest.raises(RiskConfigurationError, match="requires score_min < threshold"):
        resolve_normalization_bounds(0.40, {"score_min": 0.45, "score_max": 0.80})

    # s_max <= threshold
    with pytest.raises(RiskConfigurationError, match="requires threshold < score_max"):
        resolve_normalization_bounds(0.85, {"score_min": 0.20, "score_max": 0.80})


def test_resolve_normalization_bounds_explicit_fallback() -> None:
    """Verify controlled legacy model support when allow_fallback=True."""
    s_min, s_max = resolve_normalization_bounds(0.50, None, allow_fallback=True)
    assert s_min < 0.50 < s_max

    # Out-of-order fallback adjustment
    s_min2, s_max2 = resolve_normalization_bounds(0.20, None, allow_fallback=True)
    assert s_min2 < 0.20 < s_max2
