"""Unit tests for Stage 2 IsolationForestModel wrapper and AnomalyModel protocol."""

import numpy as np
import pytest

from finsignal.ml.exceptions import MLDomainError, SchemaValidationError
from finsignal.ml.model import AnomalyModel, IsolationForestModel


def _make_dummy_matrix(rows: int = 100, anomaly_rows: int = 5) -> np.ndarray:
    """Generate deterministic (rows, 34) synthetic feature matrix."""
    rng = np.random.default_rng(seed=42)
    # Normal data centered around 0 with small variance
    data = rng.normal(loc=0.0, scale=1.0, size=(rows, 34)).astype(np.float64)
    # Anomalous data with extreme values
    if anomaly_rows > 0:
        data[:anomaly_rows, :] = rng.normal(
            loc=15.0, scale=3.0, size=(anomaly_rows, 34)
        )
    return data


def test_isolation_forest_implements_protocol() -> None:
    """Verify that IsolationForestModel satisfies AnomalyModel protocol."""
    model = IsolationForestModel()
    assert isinstance(model, AnomalyModel)
    assert not model.is_fitted
    assert model.feature_version == "v1.0"


def test_unfitted_model_raises_on_scoring() -> None:
    """Verify that score_samples raises MLDomainError when model is not fitted."""
    model = IsolationForestModel()
    X = _make_dummy_matrix(rows=10)
    with pytest.raises(MLDomainError, match="Model is not fitted"):
        model.score_samples(X)


def test_fit_and_score_shape_and_range() -> None:
    """Verify that fit and score_samples produce valid finite 1D scores."""
    X = _make_dummy_matrix(rows=100)
    model = IsolationForestModel(random_state=42)
    model.fit(X)
    assert model.is_fitted

    scores = model.score_samples(X)
    assert isinstance(scores, np.ndarray)
    assert scores.shape == (100,)
    assert scores.dtype == np.float64
    assert np.all(np.isfinite(scores))


def test_score_orientation_anomalies_higher_than_normals() -> None:
    """Verify positive score orientation: extreme anomalies score higher than typical inliers."""
    X = _make_dummy_matrix(rows=100, anomaly_rows=5)
    model = IsolationForestModel(random_state=42)
    model.fit(X)

    scores = model.score_samples(X)
    anomaly_scores = scores[:5]
    normal_scores = scores[5:]

    # Mean score of anomalies should be substantially higher than normal points
    assert np.mean(anomaly_scores) > np.mean(normal_scores)


def test_predict_binary_thresholding() -> None:
    """Verify predict produces binary 0/1 array based on threshold."""
    X = _make_dummy_matrix(rows=20)
    model = IsolationForestModel(random_state=42)
    model.fit(X)

    scores = model.score_samples(X)
    threshold = float(np.median(scores))
    preds = model.predict(X, threshold=threshold)

    assert preds.shape == (20,)
    assert set(np.unique(preds)).issubset({0, 1})
    expected = (scores >= threshold).astype(np.int64)
    np.testing.assert_array_equal(preds, expected)


def test_fit_rejects_invalid_dimensions() -> None:
    """Verify that feature matrices not matching (N, 34) are rejected."""
    model = IsolationForestModel()
    X_bad_cols = np.ones((50, 33), dtype=np.float64)
    with pytest.raises(
        SchemaValidationError, match="Expected exactly 34 feature columns"
    ):
        model.fit(X_bad_cols)

    X_1d = np.ones((50,), dtype=np.float64)
    with pytest.raises(
        SchemaValidationError, match="Expected 2-dimensional feature matrix"
    ):
        model.fit(X_1d)


def test_fit_rejects_non_finite_values() -> None:
    """Verify that NaN and Inf are rejected during fit and score."""
    model = IsolationForestModel()
    X = _make_dummy_matrix(rows=20)
    X[5, 5] = np.nan

    with pytest.raises(SchemaValidationError, match="contains non-finite values"):
        model.fit(X)


def test_fit_and_score_empty_matrix() -> None:
    """Verify empty matrix behavior on fit and score."""
    model = IsolationForestModel()
    X_empty = np.empty((0, 34), dtype=np.float64)

    with pytest.raises(ValueError, match="Cannot fit model on an empty feature matrix"):
        model.fit(X_empty)

    # Fit valid data first
    model.fit(_make_dummy_matrix(rows=10))
    empty_scores = model.score_samples(X_empty)
    assert empty_scores.shape == (0,)


def test_determinism_across_runs() -> None:
    """Verify identical scores across two independent models trained with the same seed."""
    X = _make_dummy_matrix(rows=50)
    m1 = IsolationForestModel(random_state=12345).fit(X)
    m2 = IsolationForestModel(random_state=12345).fit(X)

    s1 = m1.score_samples(X)
    s2 = m2.score_samples(X)
    np.testing.assert_array_almost_equal(s1, s2)
