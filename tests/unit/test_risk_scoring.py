"""Unit tests for hybrid risk scoring engine, tier mappings, and severity floors."""

from decimal import Decimal

from finsignal.risk.schemas import (
    RiskFactorCode,
    RiskFactorDTO,
    RiskLevel,
    RiskScoringConfig,
    RiskSeverity,
)
from finsignal.risk.scoring import HybridScoringEngine


def _make_dummy_factor(code: RiskFactorCode, severity: RiskSeverity) -> RiskFactorDTO:
    return RiskFactorDTO(
        code=code,
        label=code.value,
        severity=severity,
        description="test",
        value_numeric=Decimal("1"),
        value_text=None,
        evidence={},
    )


def test_baseline_linear_combination() -> None:
    """Verify linear combination S_composite = 0.60 * S_ml + 0.40 * S_rule."""
    engine = HybridScoringEngine(RiskScoringConfig(w_ml=0.60, w_rule=0.40))

    # ML = 50.0, Rule = 50.0 -> Composite = 50.0
    score, level = engine.calculate_score(50.0, 50.0, [])
    assert score == 50.0
    assert level == RiskLevel.HIGH  # 50.0 is lower boundary of HIGH

    # ML = 20.0, Rule = 10.0 -> Composite = 0.60*20 + 0.40*10 = 16.0
    score2, level2 = engine.calculate_score(20.0, 10.0, [])
    assert score2 == 16.0
    assert level2 == RiskLevel.LOW

    # ML = 90.0, Rule = 80.0 -> Composite = 0.60*90 + 0.40*80 = 86.0
    score3, level3 = engine.calculate_score(90.0, 80.0, [])
    assert score3 == 86.0
    assert level3 == RiskLevel.CRITICAL


def test_exact_risk_tier_boundaries() -> None:
    """Verify exact tier cutoffs: [0, 25) LOW, [25, 50) MEDIUM, [50, 75) HIGH, [75, 100] CRITICAL."""
    engine = HybridScoringEngine(
        RiskScoringConfig(
            tier_low_upper=25.0,
            tier_medium_upper=50.0,
            tier_high_upper=75.0,
            escalation_floor_enabled=False,
        )
    )

    # 24.99 -> LOW; 25.00 -> MEDIUM
    _, l1 = engine.calculate_score(24.99, 24.99, [])
    _, l2 = engine.calculate_score(25.00, 25.00, [])
    assert l1 == RiskLevel.LOW
    assert l2 == RiskLevel.MEDIUM

    # 49.99 -> MEDIUM; 50.00 -> HIGH
    _, l3 = engine.calculate_score(49.99, 49.99, [])
    _, l4 = engine.calculate_score(50.00, 50.00, [])
    assert l3 == RiskLevel.MEDIUM
    assert l4 == RiskLevel.HIGH

    # 74.99 -> HIGH; 75.00 -> CRITICAL
    _, l5 = engine.calculate_score(74.99, 74.99, [])
    _, l6 = engine.calculate_score(75.00, 75.00, [])
    assert l5 == RiskLevel.HIGH
    assert l6 == RiskLevel.CRITICAL


def test_severity_floor_candidate_escalation() -> None:
    """Verify Option A evidence-gated severity floor behavior when enabled."""
    config_disabled = RiskScoringConfig(escalation_floor_enabled=False)
    config_enabled = RiskScoringConfig(escalation_floor_enabled=True)

    engine_disabled = HybridScoringEngine(config_disabled)
    engine_enabled = HybridScoringEngine(config_enabled)

    crit_factor = _make_dummy_factor(
        RiskFactorCode.HIGH_VELOCITY, RiskSeverity.CRITICAL
    )
    high_factor = _make_dummy_factor(
        RiskFactorCode.LARGE_AMOUNT_DEVIATION, RiskSeverity.HIGH
    )

    # Mild ML and rule: raw linear = 0.60*10 + 0.40*10 = 10.0 (LOW)
    score_dis, lvl_dis = engine_disabled.calculate_score(10.0, 10.0, [crit_factor])
    assert score_dis == 10.0
    assert lvl_dis == RiskLevel.LOW

    # With floor enabled: CRITICAL factor elevates score to at least 75.0 (CRITICAL tier)
    score_en, lvl_en = engine_enabled.calculate_score(10.0, 10.0, [crit_factor])
    assert score_en == 75.0
    assert lvl_en == RiskLevel.CRITICAL

    # With floor enabled: HIGH factor elevates score to at least 50.0 (HIGH tier)
    score_high, lvl_high = engine_enabled.calculate_score(10.0, 10.0, [high_factor])
    assert score_high == 50.0
    assert lvl_high == RiskLevel.HIGH


def test_scoring_determinism() -> None:
    """Verify that identical inputs produce bitwise identical scores over 500 repetitions."""
    engine = HybridScoringEngine()
    factor = _make_dummy_factor(RiskFactorCode.NEW_DEVICE, RiskSeverity.MEDIUM)

    first_score, first_level = engine.calculate_score(62.345, 45.0, [factor])
    for _ in range(500):
        s, lvl = engine.calculate_score(62.345, 45.0, [factor])
        assert s == first_score
        assert lvl == first_level


def test_effective_config_version_sensitivity() -> None:
    """Verify that changing any result-affecting parameter alters effective_config_version."""
    base = RiskScoringConfig()
    base_ver = base.effective_config_version

    # Identical config produces identical effective identity
    same = RiskScoringConfig()
    assert same.effective_config_version == base_ver

    # Changing weights changes effective identity
    diff_weights = RiskScoringConfig(w_ml=0.70, w_rule=0.30)
    assert diff_weights.effective_config_version != base_ver

    # Changing escalation floor changes effective identity
    diff_floor = RiskScoringConfig(escalation_floor_enabled=True)
    assert diff_floor.effective_config_version != base_ver

    # Changing tier boundaries changes effective identity
    diff_tier = RiskScoringConfig(tier_low_upper=20.0)
    assert diff_tier.effective_config_version != base_ver

    # Changing base config_version string changes effective identity
    diff_base_str = RiskScoringConfig(config_version="rc_v2.0")
    assert diff_base_str.effective_config_version != base_ver

    # Changing rule_policy_version changes effective identity
    diff_rp = RiskScoringConfig(rule_policy_version="rp_v2.0")
    assert diff_rp.effective_config_version != base_ver

    # Changing scoring_algorithm_version changes effective identity
    diff_algo = RiskScoringConfig(scoring_algorithm_version="hybrid_linear_v2")
    assert diff_algo.effective_config_version != base_ver

    # Changing normalization_policy changes effective identity
    diff_norm = RiskScoringConfig(normalization_policy="anchored_piecewise_v2")
    assert diff_norm.effective_config_version != base_ver

    # Check length constraint (must fit in String(32))
    assert len(base_ver) <= 32
    assert len(diff_weights.effective_config_version) <= 32
    assert len(diff_rp.effective_config_version) <= 32
    assert len(diff_algo.effective_config_version) <= 32

    # Verify max length enforcement on base config_version (max 18 chars to guarantee <= 32 total)
    max_base_str = RiskScoringConfig(config_version="x" * 18)
    assert len(max_base_str.effective_config_version) == 18 + 1 + 12  # exactly 31 <= 32

    # Exceeding 18 chars raises ValidationError
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="at most 18 characters"):
        RiskScoringConfig(config_version="x" * 19)

    # Verify that minute floating point differences do not collapse through lossy rounding
    cfg_f1 = RiskScoringConfig(tier_low_upper=25.0001)
    cfg_f2 = RiskScoringConfig(tier_low_upper=25.0002)
    assert cfg_f1.effective_config_version != cfg_f2.effective_config_version
