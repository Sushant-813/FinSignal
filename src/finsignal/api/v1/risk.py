"""Risk Analysis & Explainability API v1 router and endpoint handlers."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.dependencies import require_roles
from finsignal.core.config import Settings, get_settings
from finsignal.core.database import get_db_session
from finsignal.risk.schemas import (
    RiskAnalysisResponse,
    RiskAnalyzeRequest,
    RiskScoringConfig,
)
from finsignal.risk.service import RiskService
from finsignal.users.models import User

router = APIRouter(prefix="/transactions", tags=["Risk Analysis"])


def get_risk_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RiskService:
    """Dependency provider for RiskService configured from application settings."""
    config = RiskScoringConfig(
        config_version=settings.risk_config_version,
        w_ml=settings.risk_weight_ml,
        w_rule=settings.risk_weight_rule,
        escalation_floor_enabled=settings.risk_escalation_floor_enabled,
    )
    return RiskService(config=config)


@router.get(
    "/{transaction_id}/risk",
    response_model=RiskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest risk analysis for a transaction",
)
async def get_transaction_risk(
    transaction_id: Annotated[
        uuid.UUID,
        Path(description="Target transaction UUID identifier"),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[RiskService, Depends(get_risk_service)],
) -> RiskAnalysisResponse:
    """Retrieve the latest successfully persisted risk analysis and explainability factors.

    Guarantees:
    - Pure query: does not trigger ML inference or create new records.
    - Historical accessibility: returns results even if the originating model is now retired.
    - Deterministic ordering: latest analysis resolved by (created_at DESC, id DESC).
    """
    return await service.get_latest_analysis(
        session=session, transaction_id=transaction_id
    )


@router.post(
    "/{transaction_id}/risk/analyze",
    response_model=RiskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate transaction risk or return existing identical analysis",
)
async def analyze_transaction_risk(
    transaction_id: Annotated[
        uuid.UUID,
        Path(description="Target transaction UUID identifier"),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[RiskService, Depends(get_risk_service)],
    payload: Annotated[
        RiskAnalyzeRequest | None,
        Body(description="Optional model version selection"),
    ] = None,
) -> RiskAnalysisResponse:
    """Evaluate point-in-time transaction risk, generate factors, and persist results.

    Guarantees:
    - Default analysis resolves the current ACTIVE model.
    - Explicit model selection validates model lifecycle eligibility (ACTIVE or RETIRED; VALIDATED requires ADMIN).
    - Idempotent: returns existing analysis if canonical identity (tx + model + config + feature_hash) matches.
    - Creates and persists an immutable analysis when inputs or configuration differ.
    - Atomic persistence: analysis, factors, and audit event commit together.
    """
    req = payload or RiskAnalyzeRequest()
    result = await service.analyze_transaction(
        session=session,
        transaction_id=transaction_id,
        model_version_id=req.model_version_id,
        current_user=current_user,
    )
    await session.commit()
    return result
