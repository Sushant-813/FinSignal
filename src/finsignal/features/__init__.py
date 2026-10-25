"""FinSignal Phase 6 Feature Engineering package."""

from finsignal.features.constants import FEATURE_VERSION, MIN_BASELINE_OBSERVATIONS
from finsignal.features.repository import FeatureRepository
from finsignal.features.schemas import (
    AccountProfileDTO,
    EvaluatedTransactionDTO,
    EvaluationContext,
    FeatureEvaluationResult,
    FeatureMetadata,
    FeatureVector,
    HistoricalTransactionDTO,
    LifetimeBaselineSummary,
)
from finsignal.features.service import FeatureService

__all__ = [
    "FEATURE_VERSION",
    "MIN_BASELINE_OBSERVATIONS",
    "AccountProfileDTO",
    "EvaluatedTransactionDTO",
    "EvaluationContext",
    "FeatureEvaluationResult",
    "FeatureMetadata",
    "FeatureRepository",
    "FeatureService",
    "FeatureVector",
    "HistoricalTransactionDTO",
    "LifetimeBaselineSummary",
]
