"""API contract and authorization tests for /api/v1/analytics endpoints (Phase 5)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from finsignal.analytics.schemas import (
    AccountActivityResponse,
    AccountSummaryItem,
    CategoryAnalyticsResponse,
    MerchantAnalyticsResponse,
    OverviewAnalyticsResponse,
    TrendAnalyticsResponse,
    TrendBucketItem,
    UnusualSpendingResponse,
)
from finsignal.analytics.service import AnalyticsService
from finsignal.api.v1.analytics import get_analytics_service
from finsignal.auth.dependencies import get_current_user
from finsignal.common.exceptions import NotFoundError
from finsignal.users.models import User


@pytest.fixture
def mock_analytics_service() -> AsyncMock:
    """Mock AnalyticsService returning compliant response models."""
    mock = AsyncMock(spec=AnalyticsService)

    # 1. Overview mock
    mock.get_overview.return_value = OverviewAnalyticsResponse(
        source_namespace="SYNTHETIC",
        currency="INR",
        from_time=None,
        to_time=None,
        total_transaction_count=10,
        debit_transaction_count=8,
        credit_transaction_count=2,
        total_volume_amount=Decimal("5000.00"),
        total_debit_amount=Decimal("3000.00"),
        total_credit_amount=Decimal("2000.00"),
        net_cash_flow=Decimal("-1000.00"),
        average_transaction_amount=Decimal("500.00"),
        median_transaction_amount=Decimal("400.00"),
        debit_average_amount=Decimal("375.00"),
        debit_median_amount=Decimal("350.00"),
        credit_average_amount=Decimal("1000.00"),
        credit_median_amount=Decimal("1000.00"),
        min_transaction_amount=Decimal("50.00"),
        max_transaction_amount=Decimal("1500.00"),
    )

    # 2. Trends mock
    mock.get_trends.return_value = TrendAnalyticsResponse(
        source_namespace="SYNTHETIC",
        currency="INR",
        interval="day",
        timezone="UTC",
        from_time=datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC),
        to_time=datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC),
        total_buckets=1,
        buckets=[
            TrendBucketItem(
                bucket_start=datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC),
                transaction_count=1,
                debit_count=1,
                credit_count=0,
                total_debit_amount=Decimal("100.00"),
                total_credit_amount=Decimal("0.00"),
                net_cash_flow=Decimal("-100.00"),
            )
        ],
    )

    # 3. Categories mock
    mock.get_categories.return_value = CategoryAnalyticsResponse(
        source_namespace="SYNTHETIC",
        currency="INR",
        direction="DEBIT",
        total_directional_amount=Decimal("1000.00"),
        categories=[],
    )

    # 4. Merchants mock
    mock.get_merchants.return_value = MerchantAnalyticsResponse(
        source_namespace="SYNTHETIC",
        currency="INR",
        total_debit_amount=Decimal("1000.00"),
        total_merchant_debit_amount=Decimal("800.00"),
        non_merchant_debit_amount=Decimal("200.00"),
        returned_merchant_count=0,
        merchants=[],
    )

    # 5. Account Activity mock
    acc_id = uuid.uuid4()
    mock.get_account_activity.return_value = AccountActivityResponse(
        account_id=acc_id,
        external_account_id="ACC_001",
        source_namespace="SYNTHETIC",
        account_type="CHECKING",
        status="ACTIVE",
        currency="INR",
        available_currencies=["INR"],
        first_transaction_at=None,
        last_transaction_at=None,
        active_days_count=0,
        summary=AccountSummaryItem(
            total_transaction_count=0,
            debit_transaction_count=0,
            credit_transaction_count=0,
            total_volume_amount=Decimal("0.00"),
            total_debit_amount=Decimal("0.00"),
            total_credit_amount=Decimal("0.00"),
            net_cash_flow=Decimal("0.00"),
            average_transaction_amount=Decimal("0.00"),
            median_transaction_amount=None,
            debit_average_amount=Decimal("0.00"),
            debit_median_amount=None,
            credit_average_amount=Decimal("0.00"),
            credit_median_amount=None,
            min_transaction_amount=None,
            max_transaction_amount=None,
        ),
        top_categories=[],
        top_merchants=[],
    )

    # 6. Unusual Spending mock
    mock.get_unusual_spending.return_value = UnusualSpendingResponse(
        account_id=acc_id,
        currency="INR",
        account_median_debit=None,
        multiplier="3.0",
        outlier_threshold_amount=None,
        unusual_transaction_count=0,
        returned_count=0,
        transactions=[],
    )

    return mock


def _make_mock_user(role: str) -> User:
    """Helper to construct mock User object with specified role."""
    user = User()
    user.id = uuid.uuid4()
    user.role = role
    user.email = f"{role.lower()}@example.com"
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_analytics_unauthenticated_returns_401(async_client: AsyncClient) -> None:
    """Verify all analytics endpoints reject unauthenticated requests with 401."""
    random_id = str(uuid.uuid4())
    endpoints = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/trends?from_time=2026-09-01T00:00:00Z&to_time=2026-09-02T00:00:00Z",
        "/api/v1/analytics/categories",
        "/api/v1/analytics/merchants",
        f"/api/v1/analytics/accounts/{random_id}",
        f"/api/v1/analytics/accounts/{random_id}/unusual-spending",
    ]
    for url in endpoints:
        resp = await async_client.get(url)
        assert resp.status_code == 401, (
            f"Expected 401 for {url}, got {resp.status_code}"
        )
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ADMIN", "ANALYST", "INVESTIGATOR"])
async def test_analytics_permitted_roles_allowed(
    app: FastAPI,
    async_client: AsyncClient,
    mock_analytics_service: AsyncMock,
    role: str,
) -> None:
    """Verify all 3 approved roles (ADMIN, ANALYST, INVESTIGATOR) can access analytics."""
    user = _make_mock_user(role)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    try:
        resp = await async_client.get("/api/v1/analytics/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_namespace"] == "SYNTHETIC"
        assert data["currency"] == "INR"
        assert data["total_transaction_count"] == 10
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_analytics_unauthorized_role_forbidden(
    app: FastAPI,
    async_client: AsyncClient,
    mock_analytics_service: AsyncMock,
) -> None:
    """Verify users with non-permitted roles (e.g. AUDITOR) receive 403 Forbidden."""
    user = _make_mock_user("AUDITOR")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    try:
        resp = await async_client.get("/api/v1/analytics/overview")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trends_endpoint_validation_errors(
    app: FastAPI,
    async_client: AsyncClient,
    mock_analytics_service: AsyncMock,
) -> None:
    """Verify trends endpoint rejects missing bounds and invalid intervals with 422."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    try:
        # Missing from_time and to_time
        resp = await async_client.get("/api/v1/analytics/trends")
        assert resp.status_code == 422

        # Invalid interval
        resp = await async_client.get(
            "/api/v1/analytics/trends?from_time=2026-09-01T00:00:00Z&to_time=2026-09-02T00:00:00Z&interval=yearly"
        )
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_merchants_endpoint_pagination_validation(
    app: FastAPI,
    async_client: AsyncClient,
    mock_analytics_service: AsyncMock,
) -> None:
    """Verify merchants endpoint enforces pagination bounds."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    try:
        # Limit > 100
        resp = await async_client.get("/api/v1/analytics/merchants?limit=101")
        assert resp.status_code == 422

        # Offset < 0
        resp = await async_client.get("/api/v1/analytics/merchants?offset=-1")
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unusual_spending_multiplier_validation(
    app: FastAPI,
    async_client: AsyncClient,
    mock_analytics_service: AsyncMock,
) -> None:
    """Verify unusual spending endpoint enforces 1.5 <= multiplier <= 10.0."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    random_id = str(uuid.uuid4())
    try:
        # Multiplier < 1.5
        resp = await async_client.get(
            f"/api/v1/analytics/accounts/{random_id}/unusual-spending?multiplier=1.2"
        )
        assert resp.status_code == 422

        # Multiplier > 10.0
        resp = await async_client.get(
            f"/api/v1/analytics/accounts/{random_id}/unusual-spending?multiplier=15.0"
        )
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_analytics_namespace_not_found(
    app: FastAPI,
    async_client: AsyncClient,
    mock_analytics_service: AsyncMock,
) -> None:
    """Verify nonexistent namespace produces 404 with NAMESPACE_NOT_FOUND."""
    user = _make_mock_user("ADMIN")
    mock_analytics_service.get_overview.side_effect = NotFoundError(
        message="Target namespace 'GHOST_NS' does not exist.",
        code="NAMESPACE_NOT_FOUND",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    try:
        resp = await async_client.get(
            "/api/v1/analytics/overview?source_namespace=GHOST_NS"
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NAMESPACE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_analytics_account_not_found(
    app: FastAPI,
    async_client: AsyncClient,
    mock_analytics_service: AsyncMock,
) -> None:
    """Verify nonexistent account produces 404 with RESOURCE_NOT_FOUND."""
    user = _make_mock_user("ADMIN")
    random_id = str(uuid.uuid4())
    mock_analytics_service.get_account_activity.side_effect = NotFoundError(
        message=f"Account with ID '{random_id}' was not found.",
        code="RESOURCE_NOT_FOUND",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service

    try:
        resp = await async_client.get(f"/api/v1/analytics/accounts/{random_id}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
