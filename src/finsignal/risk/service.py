"""Domain service orchestrating point-in-time risk analysis, explainability, and persistence."""

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.audit.models import AuditEvent
from finsignal.common.exceptions import AuthorizationError, NotFoundError
from finsignal.features.engine import compute_feature_vector
from finsignal.features.repository import FeatureRepository
from finsignal.ml.constants import MODEL_FAMILY
from finsignal.ml.exceptions import ModelNotFoundError, NoActiveModelError
from finsignal.ml.repository import ModelRepository
from finsignal.ml.service import MLService
from finsignal.ml.vectorizer import FeatureVectorizer
from finsignal.risk.exceptions import (
    IneligibleModelStatusError,
    RiskAnalysisNotFoundError,
)
from finsignal.risk.factors import RiskFactorGenerator
from finsignal.risk.fingerprint import compute_feature_fingerprint
from finsignal.risk.models import RiskAnalysis, RiskFactor
from finsignal.risk.normalization import (
    normalize_ml_score,
    resolve_normalization_bounds,
)
from finsignal.risk.repository import RiskRepository, is_risk_identity_conflict
from finsignal.risk.rules import RiskRuleEngine
from finsignal.risk.schemas import (
    RiskAnalysisResponse,
    RiskFactorCode,
    RiskFactorDTO,
    RiskLevel,
    RiskScoringConfig,
    RiskSeverity,
)
from finsignal.users.models import User


class RiskService:
    """Coordinates risk analysis workflow, model eligibility, factor explainability, and persistence."""

    def __init__(
        self,
        risk_repo: RiskRepository | None = None,
        feature_repo: FeatureRepository | None = None,
        model_repo: ModelRepository | None = None,
        ml_service: MLService | None = None,
        rule_engine: RiskRuleEngine | None = None,
        factor_generator: RiskFactorGenerator | None = None,
        config: RiskScoringConfig | None = None,
    ) -> None:
        self.risk_repo = risk_repo or RiskRepository()
        self.feature_repo = feature_repo or FeatureRepository()
        self.model_repo = model_repo or ModelRepository()
        self.ml_service = ml_service or MLService()
        self.rule_engine = rule_engine or RiskRuleEngine()
        self.factor_generator = factor_generator or RiskFactorGenerator()
        self.config = config or RiskScoringConfig()

        from finsignal.risk.scoring import HybridScoringEngine

        self.scoring_engine = HybridScoringEngine(self.config)

    async def get_latest_analysis(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
    ) -> RiskAnalysisResponse:
        """Retrieve the latest persisted risk analysis for a transaction without triggering inference."""
        eval_tx = await self.feature_repo.get_transaction_by_id(session, transaction_id)
        if eval_tx is None:
            raise NotFoundError(
                message=f"Transaction '{transaction_id}' was not found.",
                code="TRANSACTION_NOT_FOUND",
                details={"transaction_id": str(transaction_id)},
            )

        analysis = await self.risk_repo.get_latest_for_transaction(
            session, transaction_id
        )
        if analysis is None:
            raise RiskAnalysisNotFoundError(
                message=f"No risk analysis found for transaction '{transaction_id}'.",
                details={"transaction_id": str(transaction_id)},
            )

        return self._to_response_dto(analysis)

    async def analyze_transaction(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
        model_version_id: uuid.UUID | None = None,
        current_user: User | None = None,
    ) -> RiskAnalysisResponse:
        """Evaluate and persist point-in-time risk analysis for a transaction.

        Guarantees:
        - Resolves eligible model adhering strictly to lifecycle policy.
        - Calculates deterministic feature fingerprint over all result-affecting inputs.
        - Idempotently returns existing matching analysis if identical 4-tuple identity exists.
        - Persists parent analysis and child factors atomically.
        - Emits success audit event within the same database transaction.
        """
        # 1. Assemble evaluation context & compute features point-in-time
        context = await self.feature_repo.assemble_evaluation_context(
            session, transaction_id
        )
        features = compute_feature_vector(context)

        # 2. Resolve model and validate eligibility
        if model_version_id is not None:
            model = await self.model_repo.get_by_id(session, model_version_id)
            if model is None:
                raise ModelNotFoundError(
                    message=f"Requested model '{model_version_id}' was not found.",
                    details={"model_id": str(model_version_id)},
                )

            if model.status == "EXPERIMENTAL":
                raise IneligibleModelStatusError(
                    message="EXPERIMENTAL models are ineligible for transaction risk analysis.",
                    details={"model_id": str(model_version_id), "status": model.status},
                )
            if model.status == "VALIDATED":
                user_role = getattr(current_user, "role", None)
                if user_role != "ADMIN":
                    raise AuthorizationError(
                        message="Only administrators may evaluate transactions using VALIDATED models.",
                        details={
                            "model_id": str(model_version_id),
                            "status": model.status,
                        },
                    )
        else:
            model = await self.model_repo.get_active_model(session, MODEL_FAMILY)
            if model is None:
                raise NoActiveModelError(
                    "No active machine learning model exists for inference."
                )

        # 3. Compute canonical feature fingerprint
        feature_hash = compute_feature_fingerprint(
            features, context.evaluated_transaction
        )

        # 4. Check for existing identical analysis (idempotent reuse)
        effective_cfg_ver = self.config.effective_config_version
        existing = await self.risk_repo.get_by_identity(
            session=session,
            transaction_id=transaction_id,
            model_version_id=model.id,
            config_version=effective_cfg_ver,
            feature_vector_hash=feature_hash,
        )
        if existing is not None:
            return self._to_response_dto(existing)

        # 5. Execute ML Anomaly Scoring and Normalization
        (
            model_record,
            loaded_model,
            threshold,
        ) = await self.ml_service.resolve_and_load_model(
            session=session,
            model_id=model.id,
        )
        X = FeatureVectorizer.to_numpy([features])
        scores = loaded_model.score(X)
        raw_ml_score = float(scores[0])

        s_min, s_max = resolve_normalization_bounds(threshold, model_record.metrics)
        normalized_ml_score, norm_params = normalize_ml_score(
            raw_score=raw_ml_score,
            threshold=threshold,
            s_min=s_min,
            s_max=s_max,
        )

        # 6. Evaluate Deterministic Rules & Generate Factors
        fired_rules = self.rule_engine.evaluate(features, context.evaluated_transaction)
        factors_dto = self.factor_generator.generate(fired_rules)
        rule_score = self.rule_engine.calculate_rule_score(fired_rules)

        # 7. Compute Composite Score and Risk Level
        score, risk_level = self.scoring_engine.calculate_score(
            normalized_ml_score=normalized_ml_score,
            rule_score=rule_score,
            factors=factors_dto,
        )

        # 8. Build ORM Entities
        analysis_orm = RiskAnalysis(
            id=uuid.uuid4(),
            transaction_id=transaction_id,
            model_version_id=model.id,
            config_version=effective_cfg_ver,
            feature_vector_hash=feature_hash,
            score=Decimal(str(score)),
            risk_level=risk_level.value,
            ml_anomaly_score=raw_ml_score,
            ml_threshold=threshold,
            normalized_ml_score=normalized_ml_score,
            rule_score=rule_score,
            normalization_params=norm_params.model_dump(),
        )

        factors_orm = [
            RiskFactor(
                id=uuid.uuid4(),
                risk_analysis_id=analysis_orm.id,
                factor_code=f.code.value,
                factor_label=f.label,
                severity=f.severity.value,
                description=f.description,
                value_numeric=f.value_numeric,
                value_text=f.value_text,
                evidence=f.evidence,
            )
            for f in factors_dto
        ]

        # 9. Persist Atomically with Concurrent Race Safety
        try:
            persisted = await self.risk_repo.save_atomic(
                session, analysis_orm, factors_orm
            )
        except IntegrityError as exc:
            # Only treat failure as idempotent race if it specifically conflicts on identity uniqueness
            if is_risk_identity_conflict(exc):
                existing_after_race = await self.risk_repo.get_by_identity(
                    session=session,
                    transaction_id=transaction_id,
                    model_version_id=model.id,
                    config_version=effective_cfg_ver,
                    feature_vector_hash=feature_hash,
                )
                if existing_after_race is not None:
                    return self._to_response_dto(existing_after_race)
            raise

        # 10. Persist Success Audit Event
        audit_event = AuditEvent(
            id=uuid.uuid4(),
            actor_user_id=getattr(current_user, "id", None),
            action="TRANSACTION_RISK_ANALYZED",
            entity_type="risk_analysis",
            entity_id=persisted.id,
            metadata_={
                "transaction_id": str(transaction_id),
                "score": float(score),
                "risk_level": risk_level.value,
                "model_version": model.version,
                "config_version": effective_cfg_ver,
            },
        )
        session.add(audit_event)
        await session.flush()

        # Reload with relations for response
        loaded_persisted = await self.risk_repo.get_by_id(session, persisted.id)
        if loaded_persisted is None:
            return self._to_response_dto(
                persisted, model_version_str=model.version, factors_dto=factors_dto
            )
        return self._to_response_dto(loaded_persisted, model_version_str=model.version)

    def _to_response_dto(
        self,
        analysis: RiskAnalysis,
        model_version_str: str | None = None,
        factors_dto: list[RiskFactorDTO] | None = None,
    ) -> RiskAnalysisResponse:
        """Convert ORM RiskAnalysis entity to public response DTO."""
        if factors_dto is not None:
            factors = factors_dto
        else:
            factors = [
                RiskFactorDTO(
                    code=RiskFactorCode(f.factor_code),
                    label=f.factor_label,
                    severity=RiskSeverity(f.severity),
                    description=f.description,
                    value_numeric=f.value_numeric,
                    value_text=f.value_text,
                    evidence=f.evidence or {},
                )
                for f in (analysis.factors or [])
            ]

        version = model_version_str
        if not version and analysis.model_version:
            version = analysis.model_version.version
        if not version:
            version = "unknown"

        return RiskAnalysisResponse(
            id=analysis.id,
            transaction_id=analysis.transaction_id,
            model_version_id=analysis.model_version_id,
            model_version=version,
            config_version=analysis.config_version,
            feature_vector_hash=analysis.feature_vector_hash,
            score=float(analysis.score),
            risk_level=RiskLevel(analysis.risk_level),
            ml_anomaly_score=analysis.ml_anomaly_score,
            ml_threshold=analysis.ml_threshold,
            normalized_ml_score=analysis.normalized_ml_score,
            rule_score=analysis.rule_score,
            normalization_params=analysis.normalization_params,
            factors=factors,
            created_at=analysis.created_at,
        )
