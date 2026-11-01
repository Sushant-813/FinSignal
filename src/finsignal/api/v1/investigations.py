"""Investigation & Evidence API v1 router and endpoint handlers."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.dependencies import require_roles
from finsignal.core.database import get_db_session
from finsignal.investigations.schemas import (
    InvestigationCreateRequest,
    InvestigationDetailResponse,
    InvestigationEvidenceCreateRequest,
    InvestigationEvidenceListResponse,
    InvestigationEvidenceResponse,
    InvestigationListResponse,
    InvestigationPatchRequest,
    InvestigationPriority,
    InvestigationRelatedTransactionAddRequest,
    InvestigationResolveRequest,
    InvestigationStatus,
    InvestigationTransactionItem,
    InvestigationTransactionsListResponse,
)
from finsignal.investigations.service import InvestigationService
from finsignal.users.models import User

router = APIRouter(prefix="/investigations", tags=["Investigations"])


def get_investigation_service() -> InvestigationService:
    """Dependency provider returning an InvestigationService instance."""
    return InvestigationService()


@router.get(
    "",
    response_model=InvestigationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter investigations with deterministic ordering",
)
async def list_investigations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 25,
    status_filter: Annotated[
        InvestigationStatus | None,
        Query(alias="status", description="Filter by operational status"),
    ] = None,
    priority: Annotated[
        InvestigationPriority | None,
        Query(description="Filter by triage priority"),
    ] = None,
    assigned_to: Annotated[
        uuid.UUID | None,
        Query(description="Filter by assigned user UUID"),
    ] = None,
    unassigned: Annotated[
        bool | None,
        Query(description="Filter for unassigned investigations"),
    ] = None,
) -> InvestigationListResponse:
    """List investigations matching query criteria with pagination envelope."""
    return await service.list_investigations(
        session=session,
        page=page,
        page_size=page_size,
        status=status_filter,
        priority=priority,
        assigned_to=assigned_to,
        unassigned=unassigned,
        current_user=current_user,
    )


@router.post(
    "",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new unassigned investigation case",
)
async def create_investigation(
    payload: InvestigationCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationDetailResponse:
    """Atomically create an investigation with a PRIMARY transaction association and audit event."""
    result = await service.create_investigation(
        session=session,
        request=payload,
        current_user=current_user,
    )
    await session.commit()
    return result


@router.get(
    "/{id}",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complete investigation workspace context",
)
async def get_investigation(
    id: Annotated[uuid.UUID, Path(description="Investigation UUID identifier")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationDetailResponse:
    """Retrieve full workspace context for an investigation avoiding N+1 query loops."""
    return await service.get_investigation_workspace(
        session=session,
        investigation_id=id,
        current_user=current_user,
    )


@router.patch(
    "/{id}",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update investigation assignment, priority, or permitted status transition",
)
async def patch_investigation(
    id: Annotated[uuid.UUID, Path(description="Investigation UUID identifier")],
    payload: InvestigationPatchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationDetailResponse:
    """Apply mutable attributes with row-level concurrency lock (FOR UPDATE)."""
    result = await service.patch_investigation(
        session=session,
        investigation_id=id,
        patch=payload,
        current_user=current_user,
    )
    await session.commit()
    return result


@router.post(
    "/{id}/resolve",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicitly resolve an investigation",
)
async def resolve_investigation(
    id: Annotated[uuid.UUID, Path(description="Investigation UUID identifier")],
    payload: InvestigationResolveRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationDetailResponse:
    """Resolve an investigation in UNDER_REVIEW status and render it permanently immutable."""
    result = await service.resolve_investigation(
        session=session,
        investigation_id=id,
        request=payload,
        current_user=current_user,
    )
    await session.commit()
    return result


@router.get(
    "/{id}/transactions",
    response_model=InvestigationTransactionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all transactions associated with an investigation",
)
async def list_investigation_transactions(
    id: Annotated[uuid.UUID, Path(description="Investigation UUID identifier")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationTransactionsListResponse:
    """Retrieve primary and related transaction associations in deterministic order."""
    return await service.get_investigation_transactions(
        session=session,
        investigation_id=id,
        current_user=current_user,
    )


@router.post(
    "/{id}/transactions",
    response_model=InvestigationTransactionItem,
    status_code=status.HTTP_201_CREATED,
    summary="Link a related transaction satisfying the 4-way 1-hop scope",
)
async def add_related_transaction(
    id: Annotated[uuid.UUID, Path(description="Investigation UUID identifier")],
    payload: InvestigationRelatedTransactionAddRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationTransactionItem:
    """Associate a RELATED transaction and atomically create an audit event."""
    result = await service.add_related_transaction(
        session=session,
        investigation_id=id,
        request=payload,
        current_user=current_user,
    )
    await session.commit()
    return result


@router.get(
    "/{id}/evidence",
    response_model=InvestigationEvidenceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List append-only evidence items for an investigation",
)
async def list_investigation_evidence(
    id: Annotated[uuid.UUID, Path(description="Investigation UUID identifier")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
) -> InvestigationEvidenceListResponse:
    """Retrieve evidence items ordered deterministically by created_at ASC, id ASC."""
    return await service.list_evidence(
        session=session,
        investigation_id=id,
        page=page,
        page_size=page_size,
        current_user=current_user,
    )


@router.post(
    "/{id}/evidence",
    response_model=InvestigationEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach authoritative append-only evidence",
)
async def attach_evidence(
    id: Annotated[uuid.UUID, Path(description="Investigation UUID identifier")],
    payload: InvestigationEvidenceCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "INVESTIGATOR")),
    ],
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationEvidenceResponse:
    """Validate source authority, construct immutable snapshot, and persist evidence."""
    result = await service.attach_evidence(
        session=session,
        investigation_id=id,
        request=payload,
        current_user=current_user,
    )
    await session.commit()
    return result
