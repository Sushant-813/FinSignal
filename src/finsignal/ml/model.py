"""Isolation Forest model implementation and AnomalyModel protocol for Phase 7."""

from typing import Any, Protocol, runtime_checkable

import numpy as np
from sklearn.ensemble import IsolationForest

from finsignal.ml.constants import DEFAULT_RANDOM_SEED, FEATURE_VERSION
from finsignal.ml.exceptions import MLDomainError, SchemaValidationError


@runtime_checkable
class AnomalyModel(Protocol):
    """Protocol defining the interface for unsupervised anomaly detection models."""

    @property
    def is_fitted(self) -> bool:
        """Return whether the model has been fitted."""
        ...

    @property
    def feature_version(self) -> str:
        """Return the feature contract version the model was built for."""
        ...

    def fit(self, X: np.ndarray) -> "AnomalyModel":
        """Fit the anomaly model on an (N, 34) feature matrix."""
        ...

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Compute continuous uncalibrated anomaly scores for an (N, 34) feature matrix.

        Higher score indicates a greater degree of anomaly.
        """
        ...

    def score(self, X: np.ndarray) -> np.ndarray:
        """Compute continuous uncalibrated anomaly scores (alias for score_samples)."""
        ...

    def predict(self, X: np.ndarray, threshold: float) -> np.ndarray:
        """Predict binary anomaly decisions (1 for anomaly, 0 for normal) using threshold."""
        ...

    def get_params(self) -> dict[str, Any]:
        """Return model hyperparameter dictionary."""
        ...


class IsolationForestModel:
    """Scikit-learn Isolation Forest model wrapper with positive score orientation.

    Enforces:
    - Fixed random_state for reproducible tree construction.
    - Default contamination="auto".
    - Score orientation: score = -score_samples(X). Higher values mean more isolated (more anomalous).
    - Uncalibrated anomaly score semantics: scores represent path-length anomaly depth,
      NOT calibrated fraud probabilities.
    - Strict input shape (N, 34) and finite float validation.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_samples: int | float | str = "auto",
        contamination: float | str = "auto",
        random_state: int = DEFAULT_RANDOM_SEED,
        feature_version: str = FEATURE_VERSION,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_state = random_state
        self._feature_version = feature_version

        self.estimator: IsolationForest | None = None
        self._is_fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        """Return whether the estimator is fitted."""
        return self._is_fitted

    @property
    def feature_version(self) -> str:
        """Return the feature contract version."""
        return self._feature_version

    def _validate_input_matrix(self, X: np.ndarray) -> None:
        """Validate that X is a 2D float64 array of shape (N, 34) with finite values."""
        if not isinstance(X, np.ndarray):
            msg = f"Expected numpy.ndarray, got {type(X).__name__}"
            raise TypeError(msg)

        if X.ndim != 2:
            msg = f"Expected 2-dimensional feature matrix, got dimension {X.ndim}"
            raise SchemaValidationError(message=msg, details={"ndim": X.ndim})

        if X.shape[1] != 34:
            msg = f"Expected exactly 34 feature columns, got {X.shape[1]}"
            raise SchemaValidationError(
                message=msg,
                details={"expected_features": 34, "received_features": X.shape[1]},
            )

        if not np.all(np.isfinite(X)):
            msg = "Feature matrix contains non-finite values (NaN, +Inf, or -Inf)"
            raise SchemaValidationError(message=msg)

    def fit(self, X: np.ndarray) -> "IsolationForestModel":
        """Fit Isolation Forest on training feature matrix without labels."""
        self._validate_input_matrix(X)

        if X.shape[0] == 0:
            msg = "Cannot fit model on an empty feature matrix (0 rows)."
            raise ValueError(msg)

        self.estimator = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self.estimator.fit(X)
        self._is_fitted = True
        return self

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Compute uncalibrated anomaly scores for feature matrix X.

        Orientation:
            score = -estimator.score_samples(X)
            Higher score corresponds to more anomalous (shorter average tree path length).
        """
        if not self._is_fitted or self.estimator is None:
            msg = "Model is not fitted. Call fit() before score_samples()."
            raise MLDomainError(message=msg, code="MODEL_NOT_FITTED")

        self._validate_input_matrix(X)

        if X.shape[0] == 0:
            return np.empty((0,), dtype=np.float64)

        raw_scores = self.estimator.score_samples(X)
        # Score orientation: negate so higher scores mean more anomalous
        anomaly_scores: np.ndarray = -raw_scores
        return anomaly_scores

    def score(self, X: np.ndarray) -> np.ndarray:
        """Compute continuous anomaly scores for an (N, 34) feature matrix (alias for score_samples)."""
        return self.score_samples(X)

    def predict(self, X: np.ndarray, threshold: float) -> np.ndarray:
        """Predict binary anomaly decisions (1=anomaly, 0=normal) using decision threshold."""
        scores = self.score_samples(X)
        return (scores >= threshold).astype(np.int64)

    def get_params(self) -> dict[str, Any]:
        """Return model parameters for serialization and registry tracking."""
        return {
            "n_estimators": self.n_estimators,
            "max_samples": self.max_samples,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "feature_version": self._feature_version,
            "is_fitted": self._is_fitted,
        }
