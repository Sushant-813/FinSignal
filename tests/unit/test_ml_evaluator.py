"""Unit tests for ModelEvaluator metrics and label-informed threshold selection."""

import numpy as np
import pytest

from finsignal.ml.evaluator import ModelEvaluator
from finsignal.ml.exceptions import MLDomainError


def test_evaluator_hand_calculated_metrics() -> None:
    # 5 samples:
    # y_true = [1,    1,    0,    0,    0   ]
    # scores = [0.85, 0.65, 0.70, 0.40, 0.20]
    # threshold = 0.65 (rule: score >= threshold)
    # y_pred = [1,    1,    1,    0,    0   ]
    # TP: idx 0, 1 = 2
    # FP: idx 2 = 1
    # TN: idx 3, 4 = 2
    # FN: 0
    # precision = 2 / 3 = 0.666666...
    # recall = 2 / 2 = 1.0
    # f1 = 2 * (2/3) * 1 / (5/3) = 0.8
    # alert_rate = 3 / 5 = 0.6
    # fpr = 1 / 3 = 0.333333...

    scores = [0.85, 0.65, 0.70, 0.40, 0.20]
    y_true = [1, 1, 0, 0, 0]
    scenarios = ["F001", "F002", None, None, None]
    clusters = ["c1", "c1", None, None, None]

    metrics = ModelEvaluator.evaluate(
        scores=scores,
        y_true=y_true,
        threshold=0.65,
        scenarios=scenarios,
        scenario_instance_ids=clusters,
    )

    assert metrics.total_samples == 5
    assert metrics.total_positives == 2
    assert metrics.total_alerts == 3
    assert abs(metrics.precision - 2 / 3) < 1e-5
    assert abs(metrics.recall - 1.0) < 1e-5
    assert abs(metrics.f1 - 0.8) < 1e-5
    assert abs(metrics.alert_rate - 0.6) < 1e-5
    assert abs(metrics.false_positive_rate - 1 / 3) < 1e-5

    # Check scenario metrics
    assert "F001" in metrics.scenario_metrics
    assert metrics.scenario_metrics["F001"].total_instances == 1
    assert metrics.scenario_metrics["F001"].detected_instances == 1
    assert metrics.scenario_metrics["F001"].recall == 1.0

    assert "F002" in metrics.scenario_metrics
    assert metrics.scenario_metrics["F002"].total_instances == 1
    assert metrics.scenario_metrics["F002"].detected_instances == 1
    assert metrics.scenario_metrics["F002"].recall == 1.0

    # Check cluster metrics
    assert metrics.cluster_metrics is not None
    assert metrics.cluster_metrics.total_clusters == 1
    assert metrics.cluster_metrics.detected_clusters == 1
    assert metrics.cluster_metrics.cluster_recall == 1.0


def test_evaluator_zero_division_safety() -> None:
    # No alerts produced (all scores below threshold)
    scores = [0.1, 0.2, 0.3]
    y_true = [1, 0, 0]

    metrics = ModelEvaluator.evaluate(scores=scores, y_true=y_true, threshold=0.9)
    assert metrics.total_alerts == 0
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.alert_rate == 0.0

    # No positive ground truth labels in partition
    scores_no_pos = [0.9, 0.8, 0.7]
    y_true_no_pos = [0, 0, 0]

    metrics_no_pos = ModelEvaluator.evaluate(
        scores=scores_no_pos,
        y_true=y_true_no_pos,
        threshold=0.75,
    )
    assert metrics_no_pos.total_positives == 0
    assert metrics_no_pos.precision == 0.0
    assert metrics_no_pos.recall == 0.0
    assert metrics_no_pos.f1 == 0.0
    assert metrics_no_pos.pr_auc == 0.0


def test_tune_threshold_within_budget() -> None:
    # 20 samples: 2 positive, 18 negative
    # Scores for positives: 0.90, 0.80
    # Scores for negatives: 0.10, 0.15, ..., 0.70
    np.random.seed(42)
    val_scores = [0.90, 0.80] + [0.10 + 0.03 * i for i in range(18)]
    val_labels = [1, 1] + [0] * 18

    # max_alert_rate = 0.15 -> max alerts allowed: 20 * 0.15 = 3
    result = ModelEvaluator.tune_threshold(
        val_scores=val_scores,
        val_labels=val_labels,
        max_alert_rate=0.15,
    )

    assert result.achieved_alert_rate <= 0.15
    assert result.budget_shortfall == 0.0
    assert result.validation_f1 > 0.5
    # The selected threshold should catch the positive items with high score
    assert result.selected_threshold >= 0.70


def test_tune_threshold_tie_breaking_prefers_higher_threshold() -> None:
    # If two thresholds produce identical F1 within budget, higher threshold is preferred
    val_scores = [0.90, 0.80, 0.70, 0.60, 0.10]
    val_labels = [1, 1, 0, 0, 0]

    # Threshold 0.80 -> alerts: 0.90, 0.80 (2 alerts) -> TP=2, FP=0 -> F1=1.0, alert_rate=2/5=0.40
    # Threshold 0.75 -> alerts: 0.90, 0.80 (2 alerts) -> TP=2, FP=0 -> F1=1.0, alert_rate=2/5=0.40
    result = ModelEvaluator.tune_threshold(
        val_scores=val_scores,
        val_labels=val_labels,
        max_alert_rate=0.50,
    )

    assert result.validation_f1 == 1.0
    # Higher threshold (0.80) should be chosen over lower ones that give same F1
    assert result.selected_threshold >= 0.80


def test_tune_threshold_unattainable_budget() -> None:
    # All scores are tied at 0.90
    val_scores = [0.90] * 10
    val_labels = [1] + [0] * 9

    # Budget is 0.05 (5%), but any threshold <= 0.90 yields 100% alert rate.
    # A threshold > 0.90 yields 0% alert rate (0 alerts, alert_rate 0.0 <= 0.05).
    result = ModelEvaluator.tune_threshold(
        val_scores=val_scores,
        val_labels=val_labels,
        max_alert_rate=0.05,
    )

    assert result.achieved_alert_rate <= 0.05
    assert result.budget_shortfall == 0.0


def test_tune_threshold_empty_raises() -> None:
    with pytest.raises(MLDomainError, match="Validation partition is empty"):
        ModelEvaluator.tune_threshold([], [])
