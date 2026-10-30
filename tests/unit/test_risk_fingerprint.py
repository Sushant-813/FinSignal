"""Unit tests for canonical feature fingerprinting."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from finsignal.features.schemas import EvaluatedTransactionDTO, FeatureVector
from finsignal.risk.fingerprint import compute_feature_fingerprint


def _make_dummy_features(**kwargs: object) -> FeatureVector:
    """Create a valid FeatureVector with configurable overrides."""
    base: dict[str, object] = {
        "amount": 100.0,
        "amount_log": 4.605,
        "account_age_days": 45.0,
        "velocity_5m_count": 0,
        "velocity_1h_count": 1,
        "velocity_24h_count": 3,
        "velocity_5m_amount": 0.0,
        "velocity_1h_amount": 100.0,
        "velocity_24h_amount": 300.0,
        "amount_vs_mean_ratio": 1.0,
        "amount_vs_median_ratio": 1.0,
        "amount_zscore": 0.0,
        "is_amount_different_from_constant_baseline": 0,
        "has_direction_baseline": 1,
        "has_zero_variance_baseline": 0,
        "is_cold_start": 0,
        "has_device": 1,
        "is_new_device": 0,
        "device_tx_count": 5,
        "has_merchant": 1,
        "is_new_merchant": 0,
        "merchant_tx_count": 3,
        "has_location": 1,
        "is_home_location": 1,
        "is_new_location": 0,
        "location_tx_count": 4,
        "location_frequency": 0.8,
        "has_category": 1,
        "is_new_category": 0,
        "category_spend_share_30d": 0.35,
        "hour_of_day": 14,
        "day_of_week": 2,
        "is_weekend": 0,
        "is_unusual_hour": 0,
    }
    base.update(kwargs)
    return FeatureVector.model_validate(base)


def _make_dummy_tx(**kwargs: object) -> EvaluatedTransactionDTO:
    """Create a valid EvaluatedTransactionDTO with configurable overrides."""
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "account_id": uuid.uuid4(),
        "occurred_at": datetime(2026, 10, 27, 14, 0, 0, tzinfo=UTC),
        "amount": Decimal("100.00"),
        "currency": "USD",
        "direction": "DEBIT",
        "transaction_type": "PURCHASE",
        "source_namespace": "SYNTHETIC",
        "merchant_id": uuid.uuid4(),
        "device_id": uuid.uuid4(),
        "location_id": uuid.uuid4(),
        "category": "RETAIL",
    }
    base.update(kwargs)
    return EvaluatedTransactionDTO(**base)  # type: ignore[arg-type]


def test_fingerprint_determinism() -> None:
    """Verify that identical inputs produce bitwise identical 64-character SHA-256 digests."""
    tx_id = uuid.uuid4()
    merch_id = uuid.uuid4()
    dev_id = uuid.uuid4()
    loc_id = uuid.uuid4()

    tx = _make_dummy_tx(
        id=tx_id, merchant_id=merch_id, device_id=dev_id, location_id=loc_id
    )
    features = _make_dummy_features()

    fp1 = compute_feature_fingerprint(features, tx)
    fp2 = compute_feature_fingerprint(features, tx)

    assert len(fp1) == 64
    assert fp1 == fp2


def test_fingerprint_sensitivity_to_features() -> None:
    """Verify that changing any numeric feature changes the fingerprint."""
    tx = _make_dummy_tx()
    f1 = _make_dummy_features(amount=100.0)
    f2 = _make_dummy_features(amount=101.0)
    f3 = _make_dummy_features(velocity_5m_count=2)

    assert compute_feature_fingerprint(f1, tx) != compute_feature_fingerprint(f2, tx)
    assert compute_feature_fingerprint(f1, tx) != compute_feature_fingerprint(f3, tx)


def test_fingerprint_sensitivity_to_context() -> None:
    """Verify that changing contextual transaction facts changes the fingerprint."""
    features = _make_dummy_features()
    tx1 = _make_dummy_tx(amount=Decimal("100.00"), category="RETAIL")
    tx2 = _make_dummy_tx(amount=Decimal("100.00"), category="ELECTRONICS")
    tx3 = _make_dummy_tx(amount=Decimal("100.00"), device_id=uuid.uuid4())
    tx4 = _make_dummy_tx(amount=Decimal("100.00"), currency="EUR")

    fp1 = compute_feature_fingerprint(features, tx1)
    fp2 = compute_feature_fingerprint(features, tx2)
    fp3 = compute_feature_fingerprint(features, tx3)
    fp4 = compute_feature_fingerprint(features, tx4)

    assert fp1 != fp2
    assert fp1 != fp3
    assert fp1 != fp4
