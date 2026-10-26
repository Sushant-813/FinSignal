"""ML orchestration service for dataset training, validation tuning, artifact management, and inference."""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.core.config import Settings, get_settings
from finsignal.features.constants import FEATURE_VERSION
from finsignal.features.schemas import AccountProfileDTO, FeatureVector
from finsignal.features.service import FeatureService
from finsignal.ml.constants import (
    DEFAULT_MAX_ALERT_RATE,
    DEFAULT_RANDOM_SEED,
    MODEL_FAMILY,
)
from finsignal.ml.evaluator import ModelEvaluator
from finsignal.ml.exceptions import (
    NoActiveModelError,
    SchemaValidationError,
)
from finsignal.ml.model import IsolationForestModel
from finsignal.ml.models import ModelVersion
from finsignal.ml.registry import ModelArtifactStore
from finsignal.ml.repository import ModelRepository
from finsignal.ml.schemas import (
    AnomalyPrediction,
    ThresholdSelectionResult,
)
from finsignal.ml.split import ChronologicalSplitter
from finsignal.ml.vectorizer import FeatureVectorizer


class MLService:
    """Coordinates ML lifecycle: training, evaluation, threshold tuning, artifact security, and inference."""

    def __init__(
        self,
        repository: ModelRepository | None = None,
        artifact_store: ModelArtifactStore | None = None,
        feature_service: FeatureService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or ModelRepository()
        self.artifact_store = artifact_store or ModelArtifactStore(
            base_dir=self.settings.model_artifacts_dir
        )
        self.feature_service = feature_service or FeatureService()

        # In-memory model cache: model_id -> (artifact_hash, IsolationForestModel, threshold)
        self._model_cache: dict[uuid.UUID, tuple[str, IsolationForestModel, float]] = {}

    async def train_and_register(
        self,
        session: AsyncSession,
        dataset_version_id: uuid.UUID,
        version: str,
        transactions: Sequence[Any] | None = None,
        accounts_map: Mapping[uuid.UUID, AccountProfileDTO] | None = None,
        feature_vectors: Sequence[FeatureVector] | None = None,
        timestamps: Sequence[Any] | None = None,
        record_ids: Sequence[Any] | None = None,
        ground_truth_by_tx_id: Mapping[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        max_alert_rate: float | None = None,
    ) -> ModelVersion:
        """Execute end-to-end model training, validation threshold selection, test evaluation, and registration.

        Guarantees:
        - Isolation Forest training is strictly unsupervised (zero label leakage).
        - Threshold selection is performed exclusively on the validation partition using validation labels.
        - Sealed test partition is evaluated once and never tuned against.
        - Training never activates a model implicitly (model registered with status 'VALIDATED').
        """
        params = dict(parameters or {})
        random_state = params.get("random_state", DEFAULT_RANDOM_SEED)
        n_estimators = params.get("n_estimators", 100)
        target_alert_rate = (
            max_alert_rate
            if max_alert_rate is not None
            else self.settings.ml_max_validation_alert_rate or DEFAULT_MAX_ALERT_RATE
        )

        # 1. Obtain feature vectors, timestamps, and record IDs
        vectors: list[FeatureVector] = []
        ts_list: list[Any] = []
        ids_list: list[Any] = []

        if (
            feature_vectors is not None
            and timestamps is not None
            and record_ids is not None
        ):
            vectors = list(feature_vectors)
            ts_list = list(timestamps)
            ids_list = list(record_ids)
        elif transactions is not None and accounts_map is not None:
            extraction_results = self.feature_service.extract_batch(
                transactions=transactions,
                accounts_map=accounts_map,
            )
            vectors = [res.features for res in extraction_results]
            ts_list = [tx.occurred_at for tx in transactions]
            ids_list = [tx.id for tx in transactions]
        else:
            raise SchemaValidationError(
                "Must provide either (feature_vectors, timestamps, record_ids) or (transactions, accounts_map)."
            )

        # 2. Chronological split
        splitter = ChronologicalSplitter(
            train_ratio=0.60, val_ratio=0.20, test_ratio=0.20
        )
        train_idx, val_idx, test_idx, split_metadata = splitter.split(ts_list, ids_list)

        # 3. Vectorization into canonical (N, 34) numpy float64 matrices
        X_train = FeatureVectorizer.to_numpy([vectors[i] for i in train_idx])
        X_val = FeatureVectorizer.to_numpy([vectors[i] for i in val_idx])
        X_test = FeatureVectorizer.to_numpy([vectors[i] for i in test_idx])

        # 4. Unsupervised training on train partition only
        model = IsolationForestModel(
            random_state=random_state,
            n_estimators=n_estimators,
            contamination="auto",
        )
        model.fit(X_train)

        # 5. Label-informed validation threshold tuning
        val_scores = model.score(X_val)

        val_labels = [0] * len(val_idx)
        if ground_truth_by_tx_id is not None:
            for j, orig_i in enumerate(val_idx):
                tx_id_str = str(ids_list[orig_i])
                gt = ground_truth_by_tx_id.get(tx_id_str)
                if gt is not None and getattr(gt, "is_fraud", False):
                    val_labels[j] = 1

        tuning_result: ThresholdSelectionResult = ModelEvaluator.tune_threshold(
            val_scores=val_scores,
            val_labels=val_labels,
            max_alert_rate=target_alert_rate,
        )
        selected_threshold = tuning_result.selected_threshold

        # 6. Sealed test evaluation (evaluated once on test partition)
        test_scores = model.score(X_test)
        test_labels = [0] * len(test_idx)
        test_scenarios: list[str | None] = [None] * len(test_idx)
        test_clusters: list[str | None] = [None] * len(test_idx)

        if ground_truth_by_tx_id is not None:
            for k, orig_i in enumerate(test_idx):
                tx_id_str = str(ids_list[orig_i])
                gt = ground_truth_by_tx_id.get(tx_id_str)
                if gt is not None and getattr(gt, "is_fraud", False):
                    test_labels[k] = 1
                    test_scenarios[k] = getattr(gt, "fraud_scenario", None)
                    test_clusters[k] = getattr(gt, "scenario_instance_id", None)

        test_metrics = ModelEvaluator.evaluate(
            scores=test_scores,
            y_true=test_labels,
            threshold=selected_threshold,
            scenarios=test_scenarios,
            scenario_instance_ids=test_clusters,
        )

        # 7. Secure artifact persistence
        model_id = uuid.uuid4()
        artifact_uri, artifact_hash = self.artifact_store.save(
            model_id=model_id,
            model=model,
            metadata={"version": version},
        )

        # 8. Record metrics payload
        metrics_payload = {
            "threshold": selected_threshold,
            "target_alert_rate": target_alert_rate,
            "validation": tuning_result.model_dump(mode="json"),
            "test": test_metrics.model_dump(mode="json"),
            "split": split_metadata.model_dump(mode="json"),
        }

        # 9. Register in PostgreSQL database
        model_record = await self.repository.register(
            session=session,
            name=MODEL_FAMILY,
            version=version,
            algorithm="isolation_forest",
            feature_version=FEATURE_VERSION,
            dataset_version_id=dataset_version_id,
            parameters={
                "n_estimators": n_estimators,
                "random_state": random_state,
                "contamination": "auto",
                "max_alert_rate": target_alert_rate,
            },
            metrics=metrics_payload,
            artifact_uri=artifact_uri,
            artifact_hash=artifact_hash,
            status="VALIDATED",
        )

        # Prime in-memory cache
        self._model_cache[model_record.id] = (artifact_hash, model, selected_threshold)

        return model_record

    async def promote_to_active(
        self,
        session: AsyncSession,
        model_id: uuid.UUID,
    ) -> ModelVersion:
        """Promote a validated model to active status."""
        return await self.repository.promote_to_active(session, model_id)

    async def _resolve_and_load_model(
        self,
        session: AsyncSession,
        model_id: uuid.UUID | None = None,
    ) -> tuple[ModelVersion, IsolationForestModel, float]:
        """Resolve requested or active model, verify SHA-256 integrity, and load."""
        if model_id is not None:
            model = await self.repository.get_by_id(session, model_id)
            if model is None:
                raise NoActiveModelError(f"Requested model '{model_id}' was not found.")
        else:
            model = await self.repository.get_active_model(session, MODEL_FAMILY)
            if model is None:
                raise NoActiveModelError("No active model found in registry.")

        if model.feature_version != FEATURE_VERSION:
            raise SchemaValidationError(
                f"Model feature version '{model.feature_version}' does not match system feature version '{FEATURE_VERSION}'."
            )

        if not model.artifact_uri or not model.artifact_hash:
            raise SchemaValidationError(
                f"Model '{model.id}' lacks artifact URI or SHA-256 hash."
            )

        threshold = 0.5
        if model.metrics and "threshold" in model.metrics:
            threshold = float(model.metrics["threshold"])

        # Check in-memory cache
        cached = self._model_cache.get(model.id)
        if cached is not None and cached[0] == model.artifact_hash:
            return model, cached[1], cached[2]

        # Load from disk with pre-deserialization SHA-256 integrity verification
        loaded = self.artifact_store.load(
            artifact_uri=model.artifact_uri,
            expected_hash=model.artifact_hash,
        )
        self._model_cache[model.id] = (model.artifact_hash, loaded, threshold)
        return model, loaded, threshold

    async def score_transaction(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
        model_id: uuid.UUID | None = None,
    ) -> AnomalyPrediction:
        """Perform on-demand point-in-time anomaly scoring for a single transaction."""
        model_record, loaded_model, threshold = await self._resolve_and_load_model(
            session=session,
            model_id=model_id,
        )

        eval_res = await self.feature_service.evaluate_transaction(
            session, transaction_id
        )
        matrix = FeatureVectorizer.to_numpy([eval_res.features])
        scores = loaded_model.score(matrix)
        anomaly_score = float(scores[0])

        return AnomalyPrediction(
            transaction_id=transaction_id,
            model_id=model_record.id,
            model_version=model_record.version,
            anomaly_score=anomaly_score,
            threshold=threshold,
            is_anomaly=bool(anomaly_score >= threshold),
        )

    async def score_batch(
        self,
        session: AsyncSession,
        transaction_ids: Sequence[uuid.UUID],
        model_id: uuid.UUID | None = None,
    ) -> list[AnomalyPrediction]:
        """Score a collection of transactions sequentially or in batch."""
        model_record, loaded_model, threshold = await self._resolve_and_load_model(
            session=session,
            model_id=model_id,
        )

        predictions: list[AnomalyPrediction] = []
        for tx_id in transaction_ids:
            eval_res = await self.feature_service.evaluate_transaction(session, tx_id)
            matrix = FeatureVectorizer.to_numpy([eval_res.features])
            scores = loaded_model.score(matrix)
            score = float(scores[0])
            predictions.append(
                AnomalyPrediction(
                    transaction_id=tx_id,
                    model_id=model_record.id,
                    model_version=model_record.version,
                    anomaly_score=score,
                    threshold=threshold,
                    is_anomaly=bool(score >= threshold),
                )
            )
        return predictions

    def score_feature_matrix(
        self,
        X: Any,
        model_id: uuid.UUID,
        model_version: str,
        threshold: float,
        record_ids: Sequence[Any],
    ) -> list[AnomalyPrediction]:
        """Ultra-fast in-memory batch scoring without database lookups for benchmarking."""
        cached = self._model_cache.get(model_id)
        if cached is None:
            raise NoActiveModelError(f"Model {model_id} not loaded in cache.")
        loaded_model = cached[1]
        scores = loaded_model.score(X)

        return [
            AnomalyPrediction(
                transaction_id=record_ids[i],
                model_id=model_id,
                model_version=model_version,
                anomaly_score=float(scores[i]),
                threshold=threshold,
                is_anomaly=bool(scores[i] >= threshold),
            )
            for i in range(len(scores))
        ]
