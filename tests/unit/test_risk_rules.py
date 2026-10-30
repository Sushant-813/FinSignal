"""Unit tests for deterministic risk rule evaluation and factor generation."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from finsignal.features.schemas import EvaluatedTransactionDTO, FeatureVector
from finsignal.risk.factors import RiskFactorGenerator
from finsignal.risk.rules import RiskRuleEngine
from finsignal.risk.schemas import RiskFactorCode, RiskSeverity


def _make_features(**kwargs: object) -> FeatureVector:
    base: dict[str, object] = {
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
    base.update(kwargs)
    return FeatureVector.model_validate(base)


def _make_tx(**kwargs: object) -> EvaluatedTransactionDTO:
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "account_id": uuid.uuid4(),
        "occurred_at": datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC),
        "amount": Decimal("50.00"),
        "currency": "USD",
        "direction": "DEBIT",
        "transaction_type": "PURCHASE",
        "source_namespace": "SYNTHETIC",
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "location_id": uuid.uuid4(),
        "category": "GROCERY",
    }
    base.update(kwargs)
    return EvaluatedTransactionDTO(**base)  # type: ignore[arg-type]


def test_no_rules_fired_for_routine_transaction() -> None:
    """Verify that a normal routine transaction fires zero risk rules."""
    engine = RiskRuleEngine()
    features = _make_features()
    tx = _make_tx()

    fired = engine.evaluate(features, tx)
    assert len(fired) == 0
    assert engine.calculate_rule_score(fired) == 0.0


def test_velocity_rule_severities() -> None:
    """Verify velocity rule fires with CRITICAL, HIGH, or MEDIUM severity."""
    engine = RiskRuleEngine()
    tx = _make_tx()

    # CRITICAL: 5m count >= 5
    f_crit = _make_features(velocity_5m_count=5, velocity_1h_count=8)
    rules_crit = engine.evaluate(f_crit, tx)
    assert any(
        r.code == RiskFactorCode.HIGH_VELOCITY and r.severity == RiskSeverity.CRITICAL
        for r in rules_crit
    )

    # HIGH: 5m count >= 3
    f_high = _make_features(velocity_5m_count=3, velocity_1h_count=4)
    rules_high = engine.evaluate(f_high, tx)
    assert any(
        r.code == RiskFactorCode.HIGH_VELOCITY and r.severity == RiskSeverity.HIGH
        for r in rules_high
    )

    # MEDIUM: 1h count >= 5 (5m count < 3)
    f_med = _make_features(velocity_5m_count=1, velocity_1h_count=6)
    rules_med = engine.evaluate(f_med, tx)
    assert any(
        r.code == RiskFactorCode.HIGH_VELOCITY and r.severity == RiskSeverity.MEDIUM
        for r in rules_med
    )


def test_large_amount_deviation_severities_and_cold_start_suppression() -> None:
    """Verify large amount deviation severities and suppression for cold-start accounts."""
    engine = RiskRuleEngine()
    tx = _make_tx()

    # Normal account: amount ratio 12.0x -> CRITICAL
    f_crit = _make_features(
        amount_vs_median_ratio=12.0, has_direction_baseline=1, is_cold_start=0
    )
    rules_crit = engine.evaluate(f_crit, tx)
    assert any(
        r.code == RiskFactorCode.LARGE_AMOUNT_DEVIATION
        and r.severity == RiskSeverity.CRITICAL
        for r in rules_crit
    )

    # Normal account: amount ratio 6.0x -> HIGH
    f_high = _make_features(
        amount_vs_median_ratio=6.0, has_direction_baseline=1, is_cold_start=0
    )
    rules_high = engine.evaluate(f_high, tx)
    assert any(
        r.code == RiskFactorCode.LARGE_AMOUNT_DEVIATION
        and r.severity == RiskSeverity.HIGH
        for r in rules_high
    )

    # Cold start account: deviation rule must NOT fire even if ratio is large
    f_cold = _make_features(
        amount_vs_median_ratio=15.0, has_direction_baseline=0, is_cold_start=1
    )
    rules_cold = engine.evaluate(f_cold, tx)
    assert not any(r.code == RiskFactorCode.LARGE_AMOUNT_DEVIATION for r in rules_cold)
    assert any(
        r.code == RiskFactorCode.COLD_START_ACCOUNT and r.severity == RiskSeverity.INFO
        for r in rules_cold
    )


def test_behavioral_shift_deduplication_with_new_category() -> None:
    """Verify BEHAVIORAL_SHIFT suppresses duplicate NEW_CATEGORY factor."""
    engine = RiskRuleEngine()
    tx = _make_tx(category="LUXURY")

    # Shift condition: new category, spend share < 0.05, amount ratio >= 2.0
    f_shift = _make_features(
        has_category=1,
        is_new_category=1,
        category_spend_share_30d=0.01,
        amount_vs_mean_ratio=3.5,
        is_cold_start=0,
    )
    rules = engine.evaluate(f_shift, tx)
    codes = [r.code for r in rules]

    assert RiskFactorCode.BEHAVIORAL_SHIFT in codes
    # NEW_CATEGORY must be deduplicated
    assert RiskFactorCode.NEW_CATEGORY not in codes


def test_deterministic_factor_ordering_and_evidence_fidelity() -> None:
    """Verify factor generator sorts by severity descending and preserves factual evidence."""
    engine = RiskRuleEngine()
    generator = RiskFactorGenerator()

    dev_id = uuid.uuid4()
    merch_id = uuid.uuid4()
    tx = _make_tx(device_id=dev_id, merchant_id=merch_id)

    # Multi-rule features: velocity (CRITICAL), new device (HIGH due to 1h velocity), new merchant (LOW)
    features = _make_features(
        velocity_5m_count=6,
        velocity_1h_count=3,
        has_device=1,
        is_new_device=1,
        amount_vs_median_ratio=1.0,
        has_merchant=1,
        is_new_merchant=1,
    )
    fired = engine.evaluate(features, tx)
    factors = generator.generate(fired)

    assert len(factors) == 3
    # Severity order: CRITICAL > HIGH > LOW
    assert factors[0].severity == RiskSeverity.CRITICAL
    assert factors[0].code == RiskFactorCode.HIGH_VELOCITY
    assert factors[1].severity == RiskSeverity.HIGH
    assert factors[1].code == RiskFactorCode.NEW_DEVICE
    assert factors[2].severity == RiskSeverity.LOW
    assert factors[2].code == RiskFactorCode.NEW_MERCHANT

    # Evidence fidelity: device_id and merchant_id match input exactly
    assert factors[1].value_text == str(dev_id)
    assert factors[1].evidence["device_id"] == str(dev_id)
    assert factors[2].value_text == str(merch_id)
    assert factors[2].evidence["merchant_id"] == str(merch_id)
