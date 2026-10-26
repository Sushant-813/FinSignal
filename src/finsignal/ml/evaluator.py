"""Evaluation metrics and label-informed validation threshold selection."""

from collections import defaultdict
from collections.abc import Sequence

import numpy as np
from sklearn.metrics import average_precision_score

from finsignal.ml.exceptions import MLDomainError
from finsignal.ml.schemas import (
    ClusterRecallMetric,
    EvaluationMetrics,
    ScenarioMetric,
    ThresholdSelectionResult,
)


class ModelEvaluator:
    """Computes fraud detection evaluation metrics and selects operating thresholds.

    Rules:
    - Positive alert decision: score >= threshold.
    - Zero-division safety: undefined rates return 0.0 rather than raising or returning NaN.
    - Threshold tuning: performed exclusively on validation data, optimizing F1 within max alert rate budget.
    """

    @staticmethod
    def evaluate(
        scores: Sequence[float] | np.ndarray,
        y_true: Sequence[int | bool] | np.ndarray,
        threshold: float,
        scenarios: Sequence[str | None] | None = None,
        scenario_instance_ids: Sequence[str | None] | None = None,
    ) -> EvaluationMetrics:
        """Compute comprehensive evaluation metrics for a scored partition.

        Parameters:
            scores: Continuous anomaly scores (higher = more anomalous).
            y_true: Binary ground-truth labels (1/True = fraud, 0/False = normal).
            threshold: Operating decision threshold.
            scenarios: Optional sequence of scenario codes (e.g., 'F001', 'F002').
            scenario_instance_ids: Optional sequence of cluster/instance IDs for cluster recall.
        """
        scores_arr = np.asarray(scores, dtype=np.float64)
        y_true_arr = np.asarray(y_true, dtype=np.int32)

        if scores_arr.shape[0] != y_true_arr.shape[0]:
            raise MLDomainError(
                f"Scores length {scores_arr.shape[0]} does not match labels length {y_true_arr.shape[0]}."
            )

        n = scores_arr.shape[0]
        if n == 0:
            raise MLDomainError("Cannot evaluate empty predictions.")

        y_pred = (scores_arr >= threshold).astype(np.int32)

        tp = int(np.sum((y_true_arr == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true_arr == 0) & (y_pred == 1)))
        tn = int(np.sum((y_true_arr == 0) & (y_pred == 0)))
        fn = int(np.sum((y_true_arr == 1) & (y_pred == 0)))

        total_positives = int(np.sum(y_true_arr == 1))
        total_alerts = tp + fp
        alert_rate = total_alerts / n if n > 0 else 0.0

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        # PR-AUC / Average Precision
        pr_auc = 0.0
        if total_positives > 0 and total_positives < n:
            try:
                pr_auc = float(average_precision_score(y_true_arr, scores_arr))
            except Exception:
                pr_auc = 0.0
        elif total_positives == n:
            pr_auc = 1.0

        # Per-scenario breakdown
        scenario_metrics: dict[str, ScenarioMetric] = {}
        if scenarios is not None:
            if len(scenarios) != n:
                raise MLDomainError("Scenarios length must match scores length.")

            scenario_totals: dict[str, int] = defaultdict(int)
            scenario_detected: dict[str, int] = defaultdict(int)

            for i, sc in enumerate(scenarios):
                if sc and y_true_arr[i] == 1:
                    scenario_totals[sc] += 1
                    if y_pred[i] == 1:
                        scenario_detected[sc] += 1

            for sc, total in scenario_totals.items():
                det = scenario_detected[sc]
                rec = det / total if total > 0 else 0.0
                scenario_metrics[sc] = ScenarioMetric(
                    scenario_code=sc,
                    total_instances=total,
                    detected_instances=det,
                    recall=rec,
                )

        # Scenario instance / cluster recall
        cluster_metric: ClusterRecallMetric | None = None
        if scenario_instance_ids is not None:
            if len(scenario_instance_ids) != n:
                raise MLDomainError(
                    "Scenario instance IDs length must match scores length."
                )

            cluster_flags: dict[str, bool] = defaultdict(bool)
            for i, cluster_id in enumerate(scenario_instance_ids):
                if cluster_id and y_true_arr[i] == 1:
                    if cluster_id not in cluster_flags:
                        cluster_flags[cluster_id] = False
                    if y_pred[i] == 1:
                        cluster_flags[cluster_id] = True

            total_clusters = len(cluster_flags)
            detected_clusters = sum(1 for flagged in cluster_flags.values() if flagged)
            cluster_rec = (
                detected_clusters / total_clusters if total_clusters > 0 else 0.0
            )
            cluster_metric = ClusterRecallMetric(
                total_clusters=total_clusters,
                detected_clusters=detected_clusters,
                cluster_recall=cluster_rec,
            )

        return EvaluationMetrics(
            threshold=float(threshold),
            total_samples=n,
            total_positives=total_positives,
            total_alerts=total_alerts,
            alert_rate=float(alert_rate),
            false_positive_rate=float(fpr),
            precision=float(precision),
            recall=float(recall),
            f1=float(f1),
            pr_auc=float(pr_auc),
            scenario_metrics=scenario_metrics,
            cluster_metrics=cluster_metric,
        )

    @classmethod
    def tune_threshold(
        cls,
        val_scores: Sequence[float] | np.ndarray,
        val_labels: Sequence[int | bool] | np.ndarray,
        max_alert_rate: float = 0.05,
    ) -> ThresholdSelectionResult:
        """Select operating threshold maximizing validation F1 subject to alert rate budget.

        Parameters:
            val_scores: Continuous anomaly scores on validation partition.
            val_labels: Ground-truth fraud labels on validation partition.
            max_alert_rate: Maximum permitted alert rate (e.g. 0.05 for 5%).

        Tie-breaking rule:
            When multiple thresholds yield the same maximum F1, choose the higher threshold
            (producing fewer or equal alerts, more conservative).
        """
        scores_arr = np.asarray(val_scores, dtype=np.float64)
        labels_arr = np.asarray(val_labels, dtype=np.int32)

        n = scores_arr.shape[0]
        if n == 0:
            raise MLDomainError("Validation partition is empty; cannot tune threshold.")
        if labels_arr.shape[0] != n:
            raise MLDomainError("Validation scores and labels length mismatch.")

        # Candidate thresholds from observed scores plus boundaries
        unique_scores = np.unique(scores_arr)
        max_score = float(unique_scores[-1])

        # Candidate thresholds: observed scores plus boundary where no alert is produced
        candidate_thresholds = np.concatenate(
            [
                unique_scores,
                np.array([max_score + 1e-6], dtype=np.float64),
            ]
        )
        candidate_thresholds.sort()

        best_threshold: float | None = None
        best_f1 = -1.0
        best_metrics: tuple[float, float, float] = (
            0.0,
            0.0,
            0.0,
        )  # (precision, recall, alert_rate)

        # Budget-fallback tracking: candidate with lowest alert rate
        min_alert_rate_seen = 2.0
        fallback_threshold = max_score + 1e-6
        fallback_metrics = (0.0, 0.0, 0.0)

        for thresh in candidate_thresholds:
            t = float(thresh)
            y_pred = (scores_arr >= t).astype(np.int32)
            total_alerts = int(np.sum(y_pred))
            alert_rate = total_alerts / n

            tp = int(np.sum((labels_arr == 1) & (y_pred == 1)))
            fp = int(np.sum((labels_arr == 0) & (y_pred == 1)))
            fn = int(np.sum((labels_arr == 1) & (y_pred == 0)))

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

            if alert_rate < min_alert_rate_seen:
                min_alert_rate_seen = alert_rate
                fallback_threshold = t
                fallback_metrics = (prec, rec, alert_rate)

            # Within budget
            if alert_rate <= max_alert_rate + 1e-9 and (
                f1 > best_f1
                or (abs(f1 - best_f1) < 1e-9 and t > (best_threshold or -float("inf")))
            ):
                best_f1 = f1
                best_threshold = t
                best_metrics = (prec, rec, alert_rate)

        if best_threshold is not None:
            return ThresholdSelectionResult(
                selected_threshold=best_threshold,
                achieved_alert_rate=best_metrics[2],
                target_max_alert_rate=max_alert_rate,
                budget_shortfall=0.0,
                validation_f1=best_f1,
                validation_precision=best_metrics[0],
                validation_recall=best_metrics[1],
                candidate_thresholds_evaluated=len(candidate_thresholds),
            )

        # Budget unattainable
        achieved_rate = fallback_metrics[2]
        shortfall = max(0.0, achieved_rate - max_alert_rate)
        return ThresholdSelectionResult(
            selected_threshold=fallback_threshold,
            achieved_alert_rate=achieved_rate,
            target_max_alert_rate=max_alert_rate,
            budget_shortfall=shortfall,
            validation_f1=0.0,
            validation_precision=fallback_metrics[0],
            validation_recall=fallback_metrics[1],
            candidate_thresholds_evaluated=len(candidate_thresholds),
        )
