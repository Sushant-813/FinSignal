"""Analytics API v1 router and endpoint handlers."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.analytics.schemas import (
    AccountActivityResponse,
    CategoryAnalyticsResponse,
    MerchantAnalyticsResponse,
    OverviewAnalyticsResponse,
    TrendAnalyticsResponse,
    TrendInterval,
    UnusualSpendingResponse,
)
from finsignal.analytics.service import AnalyticsService
from finsignal.auth.dependencies import require_roles
from finsignal.core.database import get_db_session
from finsignal.users.models import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_service() -> AnalyticsService:
    """Dependency provider for AnalyticsService."""
    return AnalyticsService()


@router.get(
    "/overview",
    response_model=OverviewAnalyticsResponse,
    summary="Get global transaction metrics overview",
)
async def get_overview_analytics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR"))
    ],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    source_namespace: Annotated[
        str,
        Query(
            description="Target namespace partition",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = "SYNTHETIC",
    namespace: Annotated[
        str | None,
        Query(
            description="Alias for source_namespace",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = None,
    currency: Annotated[
        str,
        Query(
            description="ISO 4217 currency code",
            min_length=3,
            max_length=3,
        ),
    ] = "INR",
    from_time: Annotated[
        datetime | None,
        Query(description="Start boundary (inclusive)"),
    ] = None,
    to_time: Annotated[
        datetime | None,
        Query(description="End boundary (exclusive)"),
    ] = None,
    timezone: Annotated[
        str,
        Query(description="Reporting timezone (informational)"),
    ] = "UTC",
) -> OverviewAnalyticsResponse:
    """Retrieve global financial metrics for a namespace and currency over a half-open window."""
    target_ns = namespace if namespace is not None else source_namespace
    return await service.get_overview(
        session=session,
        user=current_user,
        namespace=target_ns,
        currency=currency,
        from_time=from_time,
        to_time=to_time,
    )


@router.get(
    "/trends",
    response_model=TrendAnalyticsResponse,
    summary="Get periodic financial trend buckets",
)
async def get_trend_analytics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR"))
    ],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    from_time: Annotated[
        datetime,
        Query(description="Start boundary (inclusive)"),
    ],
    to_time: Annotated[
        datetime,
        Query(description="End boundary (exclusive)"),
    ],
    source_namespace: Annotated[
        str,
        Query(
            description="Target namespace partition",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = "SYNTHETIC",
    namespace: Annotated[
        str | None,
        Query(
            description="Alias for source_namespace",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = None,
    currency: Annotated[
        str,
        Query(
            description="ISO 4217 currency code",
            min_length=3,
            max_length=3,
        ),
    ] = "INR",
    interval: Annotated[
        TrendInterval,
        Query(description="Trend aggregation interval (day or month)"),
    ] = TrendInterval.DAY,
    timezone: Annotated[
        str,
        Query(description="IANA timezone identifier or UTC"),
    ] = "UTC",
) -> TrendAnalyticsResponse:
    """Retrieve zero-filled financial trends grouped by day or month."""
    target_ns = namespace if namespace is not None else source_namespace
    return await service.get_trends(
        session=session,
        user=current_user,
        from_time=from_time,
        to_time=to_time,
        namespace=target_ns,
        currency=currency,
        interval=interval.value
        if isinstance(interval, TrendInterval)
        else str(interval),
        timezone=timezone,
    )


@router.get(
    "/categories",
    response_model=CategoryAnalyticsResponse,
    summary="Get spending breakdown by category",
)
async def get_category_analytics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR"))
    ],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    source_namespace: Annotated[
        str,
        Query(
            description="Target namespace partition",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = "SYNTHETIC",
    namespace: Annotated[
        str | None,
        Query(
            description="Alias for source_namespace",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = None,
    currency: Annotated[
        str,
        Query(
            description="ISO 4217 currency code",
            min_length=3,
            max_length=3,
        ),
    ] = "INR",
    direction: Annotated[
        str,
        Query(
            description="Transaction direction (DEBIT or CREDIT)",
            pattern=r"^(DEBIT|CREDIT)$",
        ),
    ] = "DEBIT",
    from_time: Annotated[
        datetime | None,
        Query(description="Start boundary (inclusive)"),
    ] = None,
    to_time: Annotated[
        datetime | None,
        Query(description="End boundary (exclusive)"),
    ] = None,
    timezone: Annotated[
        str,
        Query(description="Reporting timezone (informational)"),
    ] = "UTC",
) -> CategoryAnalyticsResponse:
    """Retrieve spending aggregated by category."""
    target_ns = namespace if namespace is not None else source_namespace
    return await service.get_categories(
        session=session,
        user=current_user,
        namespace=target_ns,
        currency=currency,
        direction=direction,
        from_time=from_time,
        to_time=to_time,
    )


@router.get(
    "/merchants",
    response_model=MerchantAnalyticsResponse,
    summary="Get spending breakdown by merchant",
)
async def get_merchant_analytics(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR"))
    ],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    source_namespace: Annotated[
        str,
        Query(
            description="Target namespace partition",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = "SYNTHETIC",
    namespace: Annotated[
        str | None,
        Query(
            description="Alias for source_namespace",
            pattern=r"^[A-Z0-9_]{3,64}$",
        ),
    ] = None,
    currency: Annotated[
        str,
        Query(
            description="ISO 4217 currency code",
            min_length=3,
            max_length=3,
        ),
    ] = "INR",
    from_time: Annotated[
        datetime | None,
        Query(description="Start boundary (inclusive)"),
    ] = None,
    to_time: Annotated[
        datetime | None,
        Query(description="End boundary (exclusive)"),
    ] = None,
    sort_by: Annotated[
        str,
        Query(
            description="Sort criterion (amount or count)",
            pattern=r"^(amount|count)$",
        ),
    ] = "amount",
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Max merchants to return"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of merchants to skip"),
    ] = 0,
    timezone: Annotated[
        str,
        Query(description="Reporting timezone (informational)"),
    ] = "UTC",
) -> MerchantAnalyticsResponse:
    """Retrieve spending aggregated by merchant."""
    target_ns = namespace if namespace is not None else source_namespace
    return await service.get_merchants(
        session=session,
        user=current_user,
        namespace=target_ns,
        currency=currency,
        from_time=from_time,
        to_time=to_time,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/accounts/{account_id}",
    response_model=AccountActivityResponse,
    summary="Get account-specific financial activity metrics",
)
async def get_account_activity(
    account_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR"))
    ],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    currency: Annotated[
        str,
        Query(
            description="ISO 4217 currency code",
            min_length=3,
            max_length=3,
        ),
    ] = "INR",
    from_time: Annotated[
        datetime | None,
        Query(description="Start boundary (inclusive)"),
    ] = None,
    to_time: Annotated[
        datetime | None,
        Query(description="End boundary (exclusive)"),
    ] = None,
    timezone: Annotated[
        str,
        Query(description="IANA timezone identifier or UTC"),
    ] = "UTC",
) -> AccountActivityResponse:
    """Retrieve account-specific metrics scoped to authoritative namespace."""
    return await service.get_account_activity(
        session=session,
        user=current_user,
        account_id=account_id,
        currency=currency,
        timezone=timezone,
        from_time=from_time,
        to_time=to_time,
    )


@router.get(
    "/accounts/{account_id}/unusual-spending",
    response_model=UnusualSpendingResponse,
    summary="Detect unusual debit spending outliers for an account",
)
async def get_unusual_spending(
    account_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR"))
    ],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    currency: Annotated[
        str,
        Query(
            description="ISO 4217 currency code",
            min_length=3,
            max_length=3,
        ),
    ] = "INR",
    from_time: Annotated[
        datetime | None,
        Query(description="Start boundary (inclusive)"),
    ] = None,
    to_time: Annotated[
        datetime | None,
        Query(description="End boundary (exclusive)"),
    ] = None,
    timezone: Annotated[
        str,
        Query(description="Reporting timezone (informational)"),
    ] = "UTC",
    multiplier: Annotated[
        Decimal | None,
        Query(
            ge=Decimal("1.5"),
            le=Decimal("10.0"),
            description="Multiplier applied to median debit amount",
        ),
    ] = None,
    threshold_multiplier: Annotated[
        Decimal | None,
        Query(
            ge=Decimal("1.5"),
            le=Decimal("10.0"),
            description="Alias for multiplier",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Max outlier transactions to return"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of outlier transactions to skip"),
    ] = 0,
) -> UnusualSpendingResponse:
    """Detect unusual debit transactions exceeding multiplier * median."""
    effective_mult = (
        multiplier
        if multiplier is not None
        else (
            threshold_multiplier if threshold_multiplier is not None else Decimal("3.0")
        )
    )
    return await service.get_unusual_spending(
        session=session,
        user=current_user,
        account_id=account_id,
        currency=currency,
        multiplier=effective_mult,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset,
    )
