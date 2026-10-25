"""Unit tests for Phase 6 feature schemas, validation, and immutability."""

import math
import uuid
from datetime import UTC, datetime

import pydantic
import pytest

from finsignal.features.constants import FEATURE_VERSION
from finsignal.features.schemas import (
    FeatureMetadata,
    FeatureVector,
)


def _make_sample_vector(**overrides: object) -> FeatureVector:
    """Helper to generate a valid FeatureVector with default values."""
    data: dict[str, object] = {
        "amount": 500.0,
        "amount_log": math.log1p(500.0),
        "account_age_days": 45.5,
        "velocity_5m_count": 1,
        "velocity_1h_count": 2,
        "velocity_24h_count": 5,
        "velocity_5m_amount": 500.0,
        "velocity_1h_amount": 800.0,
        "velocity_24h_amount": 2500.0,
        "amount_vs_mean_ratio": 1.25,
        "amount_vs_median_ratio": 1.20,
        "amount_zscore": 0.5,
        "is_amount_different_from_constant_baseline": 0,
        "has_direction_baseline": 1,
        "has_zero_variance_baseline": 0,
        "is_cold_start": 0,
        "has_device": 1,
        "is_new_device": 0,
        "device_tx_count": 4,
        "has_merchant": 1,
        "is_new_merchant": 0,
        "merchant_tx_count": 3,
        "has_location": 1,
        "is_home_location": 1,
        "is_new_location": 0,
        "location_tx_count": 5,
        "location_frequency": 1.0,
        "has_category": 1,
        "is_new_category": 0,
        "category_spend_share_30d": 0.35,
        "hour_of_day": 14,
        "day_of_week": 2,
        "is_weekend": 0,
        "is_unusual_hour": 0,
    }
    data.update(overrides)
    return FeatureVector(**data)


def test_feature_vector_contains_exactly_34_features() -> None:
    """Verify that FeatureVector model schema defines exactly 34 model input features."""
    fields = FeatureVector.model_fields
    assert len(fields) == 34, f"Expected exactly 34 features, found {len(fields)}"


def test_feature_vector_immutability_raises_pydantic_validation_error() -> None:
    """Verify that attempting to mutate a frozen FeatureVector raises pydantic.ValidationError."""
    vector = _make_sample_vector()
    with pytest.raises(pydantic.ValidationError) as exc_info:
        vector.amount = 999.0  # type: ignore[misc]

    assert "Instance is frozen" in str(exc_info.value)


def test_feature_vector_extra_fields_forbidden() -> None:
    """Verify that extra unknown fields are rejected."""
    with pytest.raises(pydantic.ValidationError):
        _make_sample_vector(unknown_feature_field=123.45)


def test_feature_vector_rejects_non_finite_floats() -> None:
    """Verify that NaN and +/-Inf are rejected by finite-value validation."""
    with pytest.raises(pydantic.ValidationError) as exc_nan:
        _make_sample_vector(amount_zscore=float("nan"))
    assert "non-finite float value" in str(exc_nan.value)

    with pytest.raises(pydantic.ValidationError) as exc_inf:
        _make_sample_vector(amount_vs_mean_ratio=float("inf"))
    assert "non-finite float value" in str(exc_inf.value)

    with pytest.raises(pydantic.ValidationError) as exc_ninf:
        _make_sample_vector(amount_log=float("-inf"))
    assert "non-finite float value" in str(exc_ninf.value)


def test_feature_vector_serialization_round_trip() -> None:
    """Verify JSON serialization and deserialization round-trip."""
    vector = _make_sample_vector()
    json_data = vector.model_dump_json()
    restored = FeatureVector.model_validate_json(json_data)
    assert vector == restored


def test_feature_metadata_immutability_and_diagnostics() -> None:
    """Verify FeatureMetadata immutability and diagnostic fields."""
    acc_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    now = datetime.now(UTC)

    meta = FeatureMetadata(
        account_id=acc_id,
        transaction_id=tx_id,
        occurred_at=now,
        calculated_at=now,
        is_account_created_after_txn=False,
        diagnostics={"namespace": "SYNTHETIC"},
    )
    assert meta.feature_version == FEATURE_VERSION
    assert meta.is_account_created_after_txn is False
    assert meta.diagnostics["namespace"] == "SYNTHETIC"

    with pytest.raises(pydantic.ValidationError):
        meta.is_account_created_after_txn = True  # type: ignore[misc]
