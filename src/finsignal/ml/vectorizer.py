"""Vectorization of FeatureVector instances to NumPy float64 matrices."""

import logging
from collections.abc import Sequence

import numpy as np

from finsignal.features.schemas import FeatureVector
from finsignal.ml.constants import CANONICAL_FEATURE_NAMES
from finsignal.ml.exceptions import SchemaValidationError

logger = logging.getLogger(__name__)


class FeatureVectorizer:
    """Converts Phase 6 FeatureVector sequences into 2D NumPy float64 arrays.

    Guarantees:
    - Exactly 34 features in strict canonical order matching CANONICAL_FEATURE_NAMES.
    - Output dtype is float64.
    - Empty sequence produces shape (0, 34).
    - Incompatible types raise TypeError.
    - Schema validation raises SchemaValidationError.
    """

    FEATURE_NAMES: tuple[str, ...] = CANONICAL_FEATURE_NAMES

    @classmethod
    def to_numpy(cls, vectors: Sequence[FeatureVector]) -> np.ndarray:
        """Convert a sequence of FeatureVector instances into an (N, 34) float64 NumPy array."""
        n = len(vectors)
        if n == 0:
            return np.empty((0, len(cls.FEATURE_NAMES)), dtype=np.float64)

        matrix = np.empty((n, len(cls.FEATURE_NAMES)), dtype=np.float64)
        feature_names = cls.FEATURE_NAMES

        for i, vec in enumerate(vectors):
            if not isinstance(vec, FeatureVector):
                msg = f"Expected FeatureVector at index {i}, got {type(vec).__name__}"
                raise TypeError(msg)

            for j, name in enumerate(feature_names):
                val = getattr(vec, name)
                matrix[i, j] = float(val)

        return matrix

    @classmethod
    def validate_feature_names(cls, names: Sequence[str]) -> None:
        """Validate that a sequence of feature names matches CANONICAL_FEATURE_NAMES exactly."""
        if tuple(names) != cls.FEATURE_NAMES:
            msg = (
                f"Feature schema mismatch. Expected canonical 34 features: {cls.FEATURE_NAMES}, "
                f"got: {tuple(names)}"
            )
            raise SchemaValidationError(
                message=msg,
                details={
                    "expected": list(cls.FEATURE_NAMES),
                    "received": list(names),
                },
            )

    @classmethod
    def detect_constant_columns(cls, X: np.ndarray) -> list[str]:
        """Detect columns with zero sample variance in the feature matrix for diagnostics."""
        if X.shape[0] < 2:
            return []

        variances = np.var(X, axis=0)
        constant_indices = np.where(variances == 0.0)[0]
        constant_names = [cls.FEATURE_NAMES[idx] for idx in constant_indices]
        if constant_names:
            logger.warning(
                "Detected zero-variance constant features in matrix: %s",
                constant_names,
            )
        return constant_names
