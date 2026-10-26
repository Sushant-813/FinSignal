"""Machine Learning and Anomaly Detection subsystem for FinSignal Phase 7."""

from finsignal.ml.constants import (
    CANONICAL_FEATURE_NAMES,
    DEFAULT_MAX_ALERT_RATE,
    DEFAULT_RANDOM_SEED,
    FEATURE_VERSION,
    MODEL_FAMILY,
)
from finsignal.ml.evaluator import ModelEvaluator
from finsignal.ml.exceptions import (
    MLDomainError,
    ModelIntegrityError,
    ModelLifecycleError,
    ModelNotFoundError,
    NoActiveModelError,
    SchemaValidationError,
)
from finsignal.ml.model import AnomalyModel, IsolationForestModel
from finsignal.ml.models import ModelVersion
from finsignal.ml.registry import ModelArtifactStore
from finsignal.ml.repository import ModelRepository
from finsignal.ml.schemas import (
    AnomalyPrediction,
    ClusterRecallMetric,
    EvaluationMetrics,
    ScenarioMetric,
    TemporalSplitResult,
    ThresholdSelectionResult,
)
from finsignal.ml.service import MLService
from finsignal.ml.split import ChronologicalSplitter
from finsignal.ml.vectorizer import FeatureVectorizer

__all__ = [
    "AnomalyModel",
    "AnomalyPrediction",
    "CANONICAL_FEATURE_NAMES",
    "ChronologicalSplitter",
    "ClusterRecallMetric",
    "DEFAULT_MAX_ALERT_RATE",
    "DEFAULT_RANDOM_SEED",
    "EvaluationMetrics",
    "FEATURE_VERSION",
    "FeatureVectorizer",
    "IsolationForestModel",
    "MLDomainError",
    "MODEL_FAMILY",
    "MLService",
    "ModelArtifactStore",
    "ModelEvaluator",
    "ModelIntegrityError",
    "ModelLifecycleError",
    "ModelNotFoundError",
    "ModelRepository",
    "ModelVersion",
    "NoActiveModelError",
    "ScenarioMetric",
    "SchemaValidationError",
    "TemporalSplitResult",
    "ThresholdSelectionResult",
]
