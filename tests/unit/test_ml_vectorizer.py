"""Unit tests for Stage 1 FeatureVectorizer and CANONICAL_FEATURE_NAMES."""

from typing import Any

import numpy as np
import pytest

from finsignal.features.schemas import FeatureVector
from finsignal.ml.constants import CANONICAL_FEATURE_NAMES
from finsignal.ml.exceptions import SchemaValidationError
from finsignal.ml.vectorizer import FeatureVectorizer


def _make_sample_vector(**overrides: Any) -> FeatureVector:
    """Helper to create a valid FeatureVector with default values."""
    data: dict[str, Any] = {
        "amount": 150.0,
        "amount_log": 5.017,
        "account_age_days": 12.5,
        "velocity_5m_count": 1,
        "velocity_1h_count": 2,
        "velocity_24h_count": 5,
        "velocity_5m_amount": 150.0,
        "velocity_1h_amount": 300.0,
        "velocity_24h_amount": 750.0,
        "amount_vs_mean_ratio": 1.2,
        "amount_vs_median_ratio": 1.1,
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
        "location_frequency": 0.8,
        "has_category": 1,
        "is_new_category": 0,
        "category_spend_share_30d": 0.45,
        "hour_of_day": 14,
        "day_of_week": 2,
        "is_weekend": 0,
        "is_unusual_hour": 0,
    }
    data.update(overrides)
    return FeatureVector(**data)


def test_canonical_feature_names_matches_feature_vector() -> None:
    """Verify that CANONICAL_FEATURE_NAMES exactly matches FeatureVector field declaration order."""
    assert len(CANONICAL_FEATURE_NAMES) == 34
    assert tuple(FeatureVector.model_fields.keys()) == CANONICAL_FEATURE_NAMES


def test_vectorizer_output_shape_and_dtype() -> None:
    """Verify that vectorizer produces (N, 34) array with float64 dtype."""
    vec1 = _make_sample_vector(amount=100.0)
    vec2 = _make_sample_vector(amount=200.0)

    matrix = FeatureVectorizer.to_numpy([vec1, vec2])

    assert isinstance(matrix, np.ndarray)
    assert matrix.shape == (2, 34)
    assert matrix.dtype == np.float64
    assert matrix[0, 0] == 100.0
    assert matrix[1, 0] == 200.0


def test_vectorizer_preserves_canonical_order() -> None:
    """Verify that vectorizer maps every feature accurately to its canonical column index."""
    vec = _make_sample_vector(
        amount=99.99,
        velocity_24h_count=10,
        hour_of_day=23,
        is_unusual_hour=1,
    )
    matrix = FeatureVectorizer.to_numpy([vec])

    amount_idx = CANONICAL_FEATURE_NAMES.index("amount")
    v24_idx = CANONICAL_FEATURE_NAMES.index("velocity_24h_count")
    hour_idx = CANONICAL_FEATURE_NAMES.index("hour_of_day")
    unusual_idx = CANONICAL_FEATURE_NAMES.index("is_unusual_hour")

    assert matrix[0, amount_idx] == 99.99
    assert matrix[0, v24_idx] == 10.0
    assert matrix[0, hour_idx] == 23.0
    assert matrix[0, unusual_idx] == 1.0


def test_vectorizer_empty_sequence() -> None:
    """Verify that empty sequence produces (0, 34) array."""
    matrix = FeatureVectorizer.to_numpy([])
    assert matrix.shape == (0, 34)
    assert matrix.dtype == np.float64


def test_vectorizer_rejects_incompatible_input() -> None:
    """Verify that passing non-FeatureVector elements raises TypeError."""
    with pytest.raises(TypeError, match="Expected FeatureVector at index 1"):
        FeatureVectorizer.to_numpy([_make_sample_vector(), "not_a_vector"])  # type: ignore[list-item]


def test_validate_feature_names() -> None:
    """Verify feature schema validation succeeds on exact match and raises SchemaValidationError on mismatch."""
    # Exact match succeeds
    FeatureVectorizer.validate_feature_names(CANONICAL_FEATURE_NAMES)

    # Shuffled or altered raises
    altered = list(CANONICAL_FEATURE_NAMES)
    altered[0], altered[1] = altered[1], altered[0]
    with pytest.raises(SchemaValidationError) as exc_info:
        FeatureVectorizer.validate_feature_names(altered)
    assert exc_info.value.code == "SCHEMA_VALIDATION_ERROR"


def test_detect_constant_columns() -> None:
    """Verify that zero-variance columns are accurately detected."""
    vec1 = _make_sample_vector(is_weekend=0)
    vec2 = _make_sample_vector(is_weekend=0)
    matrix = FeatureVectorizer.to_numpy([vec1, vec2])

    constant_cols = FeatureVectorizer.detect_constant_columns(matrix)
    assert "is_weekend" in constant_cols
