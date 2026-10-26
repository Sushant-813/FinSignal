"""Domain schemas for ML partitioning, threshold tuning, and model evaluation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScenarioMetric(BaseModel):
    """Evaluation metrics for an individual fraud scenario (e.g., F001-F007)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_code: str
    total_instances: int = Field(ge=0)
    detected_instances: int = Field(ge=0)
    recall: float = Field(ge=0.0, le=1.0)


class ClusterRecallMetric(BaseModel):
    """Cluster-level or scenario-instance-level detection metric."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_clusters: int = Field(ge=0)
    detected_clusters: int = Field(ge=0)
    cluster_recall: float = Field(ge=0.0, le=1.0)


class EvaluationMetrics(BaseModel):
    """Evaluation metrics computed on a partition using ground-truth labels."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    threshold: float
    total_samples: int = Field(ge=0)
    total_positives: int = Field(ge=0)
    total_alerts: int = Field(ge=0)
    alert_rate: float = Field(ge=0.0, le=1.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    pr_auc: float = Field(ge=0.0, le=1.0)
    scenario_metrics: dict[str, ScenarioMetric] = Field(default_factory=dict)
    cluster_metrics: ClusterRecallMetric | None = None


class ThresholdSelectionResult(BaseModel):
    """Result of label-informed validation threshold tuning."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    selected_threshold: float
    achieved_alert_rate: float = Field(ge=0.0, le=1.0)
    target_max_alert_rate: float = Field(ge=0.0, le=1.0)
    budget_shortfall: float = Field(
        ge=0.0,
        description="Amount by which achieved alert rate exceeds target, if unattainable (0.0 otherwise).",
    )
    validation_f1: float = Field(ge=0.0, le=1.0)
    validation_precision: float = Field(ge=0.0, le=1.0)
    validation_recall: float = Field(ge=0.0, le=1.0)
    candidate_thresholds_evaluated: int = Field(ge=0)


class TemporalSplitResult(BaseModel):
    """Metadata describing a deterministic chronological split."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_records: int
    train_count: int
    val_count: int
    test_count: int
    train_ratio: float
    val_ratio: float
    test_ratio: float
    train_start: datetime | None
    train_end: datetime | None
    val_start: datetime | None
    val_end: datetime | None
    test_start: datetime | None
    test_end: datetime | None
    unique_timestamps: int


class AnomalyPrediction(BaseModel):
    """Inference output for a single scored transaction."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    transaction_id: uuid.UUID | str
    model_id: uuid.UUID
    model_version: str
    anomaly_score: float
    threshold: float
    is_anomaly: bool
