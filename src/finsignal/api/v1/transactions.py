"""Transaction exploration and detail API v1 router (Phase F0.2)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.dependencies import require_roles
from finsignal.core.database import get_db_session
from finsignal.transactions.schemas import (
    TransactionDetailResponse,
    TransactionListResponse,
)
from finsignal.transactions.service import TransactionService
from finsignal.users.models import User

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def get_transaction_service() -> TransactionService:
    """Dependency provider for TransactionService."""
    return TransactionService()


@router.get(
    "",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter transactions with deterministic ordering",
)
async def list_transactions(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Items per page (max 100)")
    ] = 50,
    source_namespace: Annotated[
        str, Query(description="Mandatory source namespace partition")
    ] = "SYNTHETIC",
    account_id: Annotated[
        uuid.UUID | None, Query(description="Filter by canonical account UUID")
    ] = None,
    merchant_id: Annotated[
        uuid.UUID | None, Query(description="Filter by merchant UUID")
    ] = None,
    device_id: Annotated[
        uuid.UUID | None, Query(description="Filter by device UUID")
    ] = None,
    location_id: Annotated[
        uuid.UUID | None, Query(description="Filter by location UUID")
    ] = None,
    transaction_type: Annotated[
        str | None,
        Query(min_length=1, max_length=32, description="Filter by transaction type"),
    ] = None,
    direction: Annotated[
        str | None,
        Query(pattern=r"^(DEBIT|CREDIT)$", description="Filter by flow direction"),
    ] = None,
    category: Annotated[
        str | None,
        Query(min_length=1, max_length=64, description="Filter by category"),
    ] = None,
    currency: Annotated[
        str | None,
        Query(pattern=r"^[A-Z]{3}$", description="ISO 4217 uppercase currency code"),
    ] = None,
    from_time: Annotated[
        datetime | None,
        Query(description="Start boundary (inclusive, timezone-aware ISO 8601)"),
    ] = None,
    to_time: Annotated[
        datetime | None,
        Query(description="End boundary (exclusive, timezone-aware ISO 8601)"),
    ] = None,
    min_amount: Annotated[
        Decimal | None,
        Query(description="Minimum transaction amount (inclusive, >= 0.01)"),
    ] = None,
    max_amount: Annotated[
        Decimal | None,
        Query(description="Maximum transaction amount (inclusive, >= 0.01)"),
    ] = None,
    risk_level: Annotated[
        str | None,
        Query(
            pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$",
            description="Filter by latest persisted risk tier",
        ),
    ] = None,
    sort_by: Annotated[
        str,
        Query(description="Sort field (occurred_at, amount, created_at)"),
    ] = "occurred_at",
    sort_order: Annotated[
        str,
        Query(description="Sort direction (asc or desc, case-insensitive)"),
    ] = "desc",
) -> TransactionListResponse:
    """List and filter transactions within a verified namespace."""
    return await service.list_transactions(
        session=session,
        page=page,
        page_size=page_size,
        source_namespace=source_namespace,
        account_id=account_id,
        merchant_id=merchant_id,
        device_id=device_id,
        location_id=location_id,
        transaction_type=transaction_type,
        direction=direction,
        category=category,
        currency=currency,
        from_time=from_time,
        to_time=to_time,
        min_amount=min_amount,
        max_amount=max_amount,
        risk_level=risk_level,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complete transaction fact context",
)
async def get_transaction_detail(
    transaction_id: Annotated[
        uuid.UUID,
        Path(description="Target transaction UUID identifier"),
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User,
        Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR")),
    ],
    service: Annotated[TransactionService, Depends(get_transaction_service)],
    source_namespace: Annotated[
        str | None,
        Query(description="Optional namespace scope fence"),
    ] = None,
) -> TransactionDetailResponse:
    """Retrieve complete authoritative transaction facts and relational reference context."""
    return await service.get_transaction_detail(
        session=session,
        transaction_id=transaction_id,
        source_namespace=source_namespace,
    )
