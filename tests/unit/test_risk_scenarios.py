"""Unit and scenario tests for FinSignal Phase 8 Risk Prioritization & Explainability.

Verifies:
1. Ordinary transaction (no risk signals).
2. Anomaly-only transaction (high ML, 0 rules).
3. Rule-only transaction (low ML, deterministic rules).
4. Multiple corroborating signals (high ML + multiple rules).
5. High-severity and Critical-severity rule escalation floor behavior.
6. Cold-start account handling and suppression of historical deviation rules.
7. Missing/incomplete historical context.
8. Exact boundary cases: 25.0, 50.0, 75.0, 100.0.
9. Comparative evaluation of baseline vs severity-floor variant under 5% alert budget.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from finsignal.features.schemas import EvaluatedTransactionDTO, FeatureVector
from finsignal.risk.factors import RiskFactorGenerator
from finsignal.risk.rules import RiskRuleEngine
from finsignal.risk.schemas import (
    RiskFactorCode,
    RiskLevel,
    RiskScoringConfig,
    RiskSeverity,
)
from finsignal.risk.scoring import HybridScoringEngine


def _make_feature_vector(**kwargs: object) -> FeatureVector:
    """Helper creating FeatureVector with default benign zero values."""
    defaults: dict[str, object] = {
        "amount": 50.0,
        "amount_log": 3.91,
        "account_age_days": 100.0,
        "velocity_5m_count": 0,
        "velocity_1h_count": 0,
        "velocity_24h_count": 1,
        "velocity_5m_amount": 0.0,
        "velocity_1h_amount": 0.0,
        "velocity_24h_amount": 50.0,
        "amount_vs_mean_ratio": 1.0,
        "amount_vs_median_ratio": 1.0,
        "amount_zscore": 0.0,
        "is_amount_different_from_constant_baseline": 0,
        "has_direction_baseline": 1,
        "has_zero_variance_baseline": 0,
        "is_cold_start": 0,
        "has_device": 1,
        "is_new_device": 0,
        "device_tx_count": 10,
        "has_merchant": 1,
        "is_new_merchant": 0,
        "merchant_tx_count": 5,
        "has_location": 1,
        "is_home_location": 1,
        "is_new_location": 0,
        "location_tx_count": 8,
        "location_frequency": 0.9,
        "has_category": 1,
        "is_new_category": 0,
        "category_spend_share_30d": 0.40,
        "hour_of_day": 12,
        "day_of_week": 3,
        "is_weekend": 0,
        "is_unusual_hour": 0,
    }
    defaults.update(kwargs)
    return FeatureVector.model_validate(defaults)


def _make_tx_dto(
    amount: Decimal = Decimal("100.00"),
    category: str = "GROCERIES",
    device_id: uuid.UUID | None = None,
    merchant_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
) -> EvaluatedTransactionDTO:
    """Helper creating basic EvaluatedTransactionDTO."""
    return EvaluatedTransactionDTO(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        account_id=uuid.uuid4(),
        occurred_at=datetime.now(UTC),
        amount=amount,
        currency="USD",
        direction="DEBIT",
        transaction_type="PURCHASE",
        category=category,
        device_id=device_id or uuid.uuid4(),
        merchant_id=merchant_id or uuid.uuid4(),
        location_id=location_id or uuid.uuid4(),
    )


def test_scenario_1_ordinary_transaction_no_risk() -> None:
    """Scenario 1: Ordinary transaction with no risk signals maps to LOW risk tier."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()
    scoring_engine = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )

    features = _make_feature_vector()
    tx = _make_tx_dto()

    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)
    rule_score = rule_engine.calculate_rule_score(fired_rules)

    # Benign ML normalized score (e.g. 15.0 out of 100)
    normalized_ml_score = 15.0

    score, risk_level = scoring_engine.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )

    # 0.60 * 15.0 + 0.40 * 0.0 = 9.0
    assert score == 9.0
    assert risk_level == RiskLevel.LOW
    assert len(factors) == 0


def test_scenario_2_anomaly_only_transaction() -> None:
    """Scenario 2: Anomaly-only transaction (high ML, 0 rules) maps to MEDIUM risk tier."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()
    scoring_engine = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )

    features = _make_feature_vector()
    tx = _make_tx_dto()

    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)
    rule_score = rule_engine.calculate_rule_score(fired_rules)
    assert rule_score == 0.0

    # Strong ML signal: normalized ML score = 80.0
    normalized_ml_score = 80.0

    score, risk_level = scoring_engine.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )

    # 0.60 * 80.0 + 0.40 * 0.0 = 48.0 -> [25, 50) is MEDIUM
    assert score == 48.0
    assert risk_level == RiskLevel.MEDIUM


def test_scenario_3_rule_only_transaction() -> None:
    """Scenario 3: Rule-only transaction (benign ML 0.0, moderate rules) maps correctly."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()
    scoring_engine = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )

    features = _make_feature_vector(
        velocity_1h_count=5,  # MEDIUM velocity (+15)
        is_new_device=1,  # NEW_DEVICE (+15)
        amount_vs_median_ratio=1.0,
    )
    tx = _make_tx_dto()

    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)
    rule_score = rule_engine.calculate_rule_score(fired_rules)
    assert rule_score == 40.0  # 15 (velocity) + 25 (new device with velocity >= 3)

    # Completely normal ML signal = 0.0
    normalized_ml_score = 0.0

    score, risk_level = scoring_engine.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )

    # 0.60 * 0.0 + 0.40 * 40.0 = 16.0 -> LOW
    assert score == 16.0
    assert risk_level == RiskLevel.LOW
    assert len(factors) == 2


def test_scenario_4_multiple_corroborating_signals() -> None:
    """Scenario 4: High ML + multiple high rules results in HIGH/CRITICAL prioritization."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()
    scoring_engine = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )

    features = _make_feature_vector(
        velocity_5m_count=3,  # HIGH velocity (+25)
        is_new_device=1,  # NEW_DEVICE (HIGH since velocity >= 3, +25)
        amount_vs_median_ratio=5.0,  # LARGE_AMOUNT_DEVIATION (HIGH, +25)
    )
    tx = _make_tx_dto()

    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)
    rule_score = rule_engine.calculate_rule_score(fired_rules)
    assert rule_score == 75.0  # 25 + 25 + 25

    # High ML score = 75.0
    normalized_ml_score = 75.0

    score, risk_level = scoring_engine.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )

    # 0.60 * 75.0 + 0.40 * 75.0 = 75.0 -> CRITICAL
    assert score == 75.0
    assert risk_level == RiskLevel.CRITICAL
    assert len(factors) == 3


def test_scenario_5_severity_floor_comparison() -> None:
    """Scenario 5: High-severity rule comparison between baseline and severity floor variant."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()

    # Rule producing HIGH severity factor
    features = _make_feature_vector(
        velocity_5m_count=3,  # HIGH velocity
        amount_vs_median_ratio=1.0,
    )
    tx = _make_tx_dto()
    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)
    rule_score = rule_engine.calculate_rule_score(fired_rules)
    assert any(f.severity == RiskSeverity.HIGH for f in factors)

    # Low ML score = 20.0
    normalized_ml_score = 20.0

    # 1. Baseline scoring (escalation_floor_enabled=False)
    engine_baseline = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )
    score_baseline, level_baseline = engine_baseline.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )
    # 0.60 * 20.0 + 0.40 * 25.0 = 12.0 + 10.0 = 22.0 -> LOW
    assert score_baseline == 22.0
    assert level_baseline == RiskLevel.LOW

    # 2. Floor variant scoring (escalation_floor_enabled=True)
    engine_floor = HybridScoringEngine(RiskScoringConfig(escalation_floor_enabled=True))
    score_floor, level_floor = engine_floor.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )
    # Floor for HIGH factor is 50.0 -> score escalated from 22.0 to 50.0 -> HIGH tier
    assert score_floor == 50.0
    assert level_floor == RiskLevel.HIGH


def test_scenario_6_critical_severity_floor() -> None:
    """Scenario 6: Critical-severity rule imposes 75.0 floor when enabled."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()

    # Velocity 5m count >= 5 produces CRITICAL severity
    features = _make_feature_vector(
        velocity_5m_count=5,
        amount_vs_median_ratio=1.0,
    )
    tx = _make_tx_dto()
    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)
    rule_score = rule_engine.calculate_rule_score(fired_rules)
    assert any(f.severity == RiskSeverity.CRITICAL for f in factors)

    # ML score = 30.0
    normalized_ml_score = 30.0

    # Baseline (no floor)
    engine_baseline = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )
    score_base, level_base = engine_baseline.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )
    # 0.60 * 30 + 0.40 * 40 = 18 + 16 = 34.0 -> MEDIUM
    assert score_base == 34.0
    assert level_base == RiskLevel.MEDIUM

    # Floor enabled
    engine_floor = HybridScoringEngine(RiskScoringConfig(escalation_floor_enabled=True))
    score_floor, level_floor = engine_floor.calculate_score(
        normalized_ml_score=normalized_ml_score,
        rule_score=rule_score,
        factors=factors,
    )
    # Floor for CRITICAL factor is 75.0 -> CRITICAL tier
    assert score_floor == 75.0
    assert level_floor == RiskLevel.CRITICAL


def test_scenario_7_cold_start_account_handling() -> None:
    """Scenario 7: Cold-start account emits COLD_START_ACCOUNT and suppresses LARGE_AMOUNT_DEVIATION."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()

    features = _make_feature_vector(
        is_cold_start=1,  # Cold start
        amount_vs_median_ratio=10.0,  # Would normally trigger LARGE_AMOUNT_DEVIATION
    )
    tx = _make_tx_dto()

    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)

    codes = [f.code.value for f in factors]
    assert RiskFactorCode.COLD_START_ACCOUNT.value in codes
    assert RiskFactorCode.LARGE_AMOUNT_DEVIATION.value not in codes

    # COLD_START factor severity is INFO (0 rule points)
    cold_start_factor = next(
        f for f in factors if f.code == RiskFactorCode.COLD_START_ACCOUNT
    )
    assert cold_start_factor.severity == RiskSeverity.INFO


def test_scenario_8_missing_or_incomplete_history() -> None:
    """Scenario 8: Missing historical counts/amounts gracefully evaluated without errors."""
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()
    scoring_engine = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )

    # All historical counters are 0, ratios default to 1.0
    features = _make_feature_vector(
        velocity_5m_count=0,
        velocity_1h_count=0,
        amount_vs_median_ratio=1.0,
    )
    tx = _make_tx_dto()

    fired_rules = rule_engine.evaluate(features, tx)
    factors = factor_gen.generate(fired_rules)
    rule_score = rule_engine.calculate_rule_score(fired_rules)

    score, level = scoring_engine.calculate_score(
        normalized_ml_score=20.0,
        rule_score=rule_score,
        factors=factors,
    )

    assert score == 12.0  # 0.6 * 20.0
    assert level == RiskLevel.LOW


def test_scenario_9_exact_tier_boundaries() -> None:
    """Scenario 9: Boundary tests at exactly 25.0, 50.0, 75.0, and 100.0."""
    engine = HybridScoringEngine(RiskScoringConfig(escalation_floor_enabled=False))

    # Score 24.99 -> LOW [0, 25)
    s1, l1 = engine.calculate_score(24.99, 24.99, [])
    assert abs(s1 - 24.99) < 1e-4
    assert l1 == RiskLevel.LOW

    # Score exactly 25.0 -> MEDIUM [25, 50)
    s2, l2 = engine.calculate_score(25.0, 25.0, [])
    assert s2 == 25.0
    assert l2 == RiskLevel.MEDIUM

    # Score 49.99 -> MEDIUM [25, 50)
    s3, l3 = engine.calculate_score(49.99, 49.99, [])
    assert abs(s3 - 49.99) < 1e-4
    assert l3 == RiskLevel.MEDIUM

    # Score exactly 50.0 -> HIGH [50, 75)
    s4, l4 = engine.calculate_score(50.0, 50.0, [])
    assert s4 == 50.0
    assert l4 == RiskLevel.HIGH

    # Score 74.99 -> HIGH [50, 75)
    s5, l5 = engine.calculate_score(74.99, 74.99, [])
    assert abs(s5 - 74.99) < 1e-4
    assert l5 == RiskLevel.HIGH

    # Score exactly 75.0 -> CRITICAL [75, 100]
    s6, l6 = engine.calculate_score(75.0, 75.0, [])
    assert s6 == 75.0
    assert l6 == RiskLevel.CRITICAL

    # Score exactly 100.0 -> CRITICAL [75, 100]
    s7, l7 = engine.calculate_score(100.0, 100.0, [])
    assert s7 == 100.0
    assert l7 == RiskLevel.CRITICAL


def test_validation_split_alert_rate_budget_comparison() -> None:
    """Evaluate alert rate (score >= 50.0) under baseline vs severity floor on a representative cohort.

    Demonstrates compliance with:
    - Alert-rate budget <= 5.0%
    - Evidence-gated decision: floor escalation causes excessive alerts if rules trigger often on normal cohort.
    """
    rule_engine = RiskRuleEngine()
    factor_gen = RiskFactorGenerator()

    # Synthetic validation cohort: 200 transactions
    # 190 ordinary/benign transactions (ML score ~ 5 to 35, few or no rules)
    # 8 suspicious transactions (ML score ~ 60 to 80, rules present)
    # 2 high-velocity bursts (ML score ~ 40, velocity rule fires)
    cohort: list[tuple[float, FeatureVector]] = []

    # 190 benign
    for i in range(190):
        ml_score = 5.0 + (i % 25)
        is_new_dev = 1 if i % 20 == 0 else 0
        fv = _make_feature_vector(
            velocity_1h_count=1 if i % 10 == 0 else 0,
            is_new_device=is_new_dev,
            amount_vs_median_ratio=1.0 + (i % 5) * 0.2,
        )
        cohort.append((ml_score, fv))

    # 8 clearly anomalous transactions
    for i in range(8):
        ml_score = 75.0 + i * 2.0
        fv = _make_feature_vector(
            velocity_5m_count=3,
            is_new_device=1,
            amount_vs_median_ratio=5.0,
        )
        cohort.append((ml_score, fv))

    # 2 borderline transactions with high velocity
    for _ in range(2):
        ml_score = 35.0
        fv = _make_feature_vector(
            velocity_5m_count=3,  # Triggers HIGH velocity rule
            is_new_device=0,
            amount_vs_median_ratio=1.0,
        )
        cohort.append((ml_score, fv))

    total_samples = len(cohort)
    assert total_samples == 200

    # 1. Evaluate baseline (no severity floor)
    engine_baseline = HybridScoringEngine(
        RiskScoringConfig(escalation_floor_enabled=False)
    )
    baseline_alerts = 0

    for ml_score, fv in cohort:
        tx = _make_tx_dto()
        fired = rule_engine.evaluate(fv, tx)
        factors = factor_gen.generate(fired)
        rule_sc = rule_engine.calculate_rule_score(fired)
        score, _ = engine_baseline.calculate_score(ml_score, rule_sc, factors)
        if score >= 50.0:  # Alert threshold (HIGH or CRITICAL)
            baseline_alerts += 1

    baseline_alert_rate = (baseline_alerts / total_samples) * 100.0

    # 2. Evaluate floor variant
    engine_floor = HybridScoringEngine(RiskScoringConfig(escalation_floor_enabled=True))
    floor_alerts = 0

    for ml_score, fv in cohort:
        tx = _make_tx_dto()
        fired = rule_engine.evaluate(fv, tx)
        factors = factor_gen.generate(fired)
        rule_sc = rule_engine.calculate_rule_score(fired)
        score, _ = engine_floor.calculate_score(ml_score, rule_sc, factors)
        if score >= 50.0:
            floor_alerts += 1

    floor_alert_rate = (floor_alerts / total_samples) * 100.0

    # Verification:
    # 8 anomalous / 200 = 4.0% alert rate <= 5.0%
    assert baseline_alert_rate == 4.0
    assert baseline_alert_rate <= 5.0

    # Floor variant escalates the 2 borderline cases to HIGH (50.0 floor), increasing alert rate to 5.0%
    assert floor_alert_rate == 5.0
    assert floor_alert_rate <= 5.0

    # Both satisfy the 5.0% budget; baseline is preserved as default per Decision 2 Option A.
