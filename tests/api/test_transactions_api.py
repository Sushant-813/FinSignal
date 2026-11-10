"""API contract, validation, RBAC, and OpenAPI tests for /api/v1/transactions (Phase F0.2)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from finsignal.api.v1.transactions import get_transaction_service
from finsignal.auth.dependencies import get_current_user
from finsignal.transactions.repository import TransactionRepository
from finsignal.transactions.schemas import (
    TransactionAccountDTO,
    TransactionDetailResponse,
    TransactionListResponse,
    TransactionSummaryItem,
)
from finsignal.transactions.service import TransactionService
from finsignal.users.models import User


def _make_mock_user(role: str) -> User:
    user = User()
    user.id = uuid.uuid4()
    user.role = role
    user.email = f"{role.lower()}@example.com"
    user.is_active = True
    return user


def _make_sample_list_response() -> TransactionListResponse:
    now = datetime(2026, 9, 15, 14, 30, 0, tzinfo=UTC)
    return TransactionListResponse(
        items=[
            TransactionSummaryItem(
                id=uuid.uuid4(),
                source_namespace="SYNTHETIC",
                external_transaction_id="TXN_00012345",
                account_id=uuid.uuid4(),
                occurred_at=now,
                amount=Decimal("75000.00"),
                currency="INR",
                transaction_type="TRANSFER",
                direction="DEBIT",
                created_at=now,
            )
        ],
        page=1,
        page_size=50,
        total=1,
        total_pages=1,
    )


def _make_sample_detail_response(
    tx_id: uuid.UUID | None = None,
) -> TransactionDetailResponse:
    now = datetime(2026, 9, 15, 14, 30, 0, tzinfo=UTC)
    acc_id = uuid.uuid4()
    return TransactionDetailResponse(
        id=tx_id or uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_transaction_id="TXN_00012345",
        account_id=acc_id,
        occurred_at=now,
        amount=Decimal("75000.00"),
        currency="INR",
        transaction_type="PURCHASE",
        direction="DEBIT",
        created_at=now,
        account=TransactionAccountDTO(
            id=acc_id,
            external_account_id="ACC_001",
            account_type="CHECKING",
            status="ACTIVE",
        ),
    )


@pytest.mark.asyncio
async def test_transactions_unauthenticated_returns_401(
    async_client: AsyncClient,
) -> None:
    """Verify both list and detail endpoints reject anonymous callers with 401 UNAUTHORIZED."""
    tx_id = str(uuid.uuid4())
    for url in ("/api/v1/transactions", f"/api/v1/transactions/{tx_id}"):
        resp = await async_client.get(url)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ADMIN", "ANALYST", "INVESTIGATOR"])
async def test_transactions_permitted_roles_allowed(
    app: FastAPI,
    async_client: AsyncClient,
    role: str,
) -> None:
    """Verify ADMIN, ANALYST, and INVESTIGATOR can access transaction list and detail."""
    user = _make_mock_user(role)
    mock_service = AsyncMock(spec=TransactionService)
    mock_service.list_transactions.return_value = _make_sample_list_response()
    tx_id = uuid.uuid4()
    mock_service.get_transaction_detail.return_value = _make_sample_detail_response(
        tx_id
    )

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_transaction_service] = lambda: mock_service

    try:
        list_resp = await async_client.get("/api/v1/transactions")
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 50
        assert isinstance(body["items"][0]["amount"], str)
        assert body["items"][0]["amount"] == "75000.00"

        call_kwargs = mock_service.list_transactions.call_args.kwargs
        assert call_kwargs["page"] == 1
        assert call_kwargs["page_size"] == 50
        assert call_kwargs["source_namespace"] == "SYNTHETIC"
        assert call_kwargs["sort_by"] == "occurred_at"
        assert call_kwargs["sort_order"] == "desc"

        detail_resp = await async_client.get(f"/api/v1/transactions/{tx_id}")
        assert detail_resp.status_code == 200
        detail_body = detail_resp.json()
        assert detail_body["id"] == str(tx_id)
        assert detail_body["amount"] == "75000.00"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_transactions_unauthorized_role_forbidden(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """Verify non-permitted role returns 403 FORBIDDEN."""
    user = _make_mock_user("AUDITOR")
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        resp_list = await async_client.get("/api/v1/transactions")
        assert resp_list.status_code == 403
        assert resp_list.json()["error"]["code"] == "FORBIDDEN"

        resp_detail = await async_client.get(f"/api/v1/transactions/{uuid.uuid4()}")
        assert resp_detail.status_code == 403
        assert resp_detail.json()["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_transactions_structural_validation_422(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """Verify FastAPI structural parsing failures return 422 VALIDATION_ERROR."""
    user = _make_mock_user("ANALYST")
    mock_service = AsyncMock(spec=TransactionService)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_transaction_service] = lambda: mock_service

    bad_urls = [
        "/api/v1/transactions?page=0",
        "/api/v1/transactions?page_size=0",
        "/api/v1/transactions?page_size=101",
        "/api/v1/transactions?account_id=not-a-uuid",
        "/api/v1/transactions?direction=SIDEWAYS",
        "/api/v1/transactions?currency=inr",
        "/api/v1/transactions?risk_level=EXTREME",
        "/api/v1/transactions?from_time=not-a-date",
        "/api/v1/transactions/not-a-uuid",
    ]
    try:
        for url in bad_urls:
            resp = await async_client.get(url)
            assert resp.status_code == 422, (
                f"Expected 422 for {url}, got {resp.status_code}"
            )
            assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_transactions_service_error_codes_reachable_over_http(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """Verify real TransactionService validation & not-found error codes surface over HTTP."""
    user = _make_mock_user("ANALYST")
    mock_repo = AsyncMock(spec=TransactionRepository)
    mock_repo.verify_namespace_exists.return_value = True
    mock_repo.list_transactions.return_value = ([], 0, 0)
    mock_repo.get_transaction_detail.return_value = None
    real_service = TransactionService(repo=mock_repo)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_transaction_service] = lambda: real_service

    try:
        cases = [
            (
                "/api/v1/transactions?source_namespace=bad-ns",
                422,
                "INVALID_NAMESPACE_FORMAT",
            ),
            (
                "/api/v1/transactions?from_time=2026-09-01T00:00:00",
                422,
                "INVALID_TIMEZONE",
            ),
            (
                "/api/v1/transactions?from_time=2026-09-02T00:00:00Z&to_time=2026-09-01T00:00:00Z",
                422,
                "INVALID_DATE_RANGE",
            ),
            (
                "/api/v1/transactions?min_amount=500.00&max_amount=100.00",
                422,
                "INVALID_AMOUNT_RANGE",
            ),
            ("/api/v1/transactions?min_amount=0.00", 422, "INVALID_AMOUNT_RANGE"),
            ("/api/v1/transactions?sort_by=currency", 422, "UNSUPPORTED_SORT_FIELD"),
            ("/api/v1/transactions?sort_order=sideways", 422, "INVALID_SORT_ORDER"),
        ]
        for url, expected_status, expected_code in cases:
            resp = await async_client.get(url)
            assert resp.status_code == expected_status, f"{url} -> {resp.text}"
            assert resp.json()["error"]["code"] == expected_code

        # Case-insensitive sort_order=ASC succeeds
        resp_asc = await async_client.get("/api/v1/transactions?sort_order=ASC")
        assert resp_asc.status_code == 200
        assert mock_repo.list_transactions.call_args.kwargs["sort_order"] == "asc"

        # Nonexistent namespace -> 404 NAMESPACE_NOT_FOUND
        mock_repo.verify_namespace_exists.return_value = False
        resp_ns = await async_client.get(
            "/api/v1/transactions?source_namespace=GHOST_NS"
        )
        assert resp_ns.status_code == 404
        assert resp_ns.json()["error"]["code"] == "NAMESPACE_NOT_FOUND"

        # Missing transaction detail -> 404 TRANSACTION_NOT_FOUND
        resp_tx = await async_client.get(f"/api/v1/transactions/{uuid.uuid4()}")
        assert resp_tx.status_code == 404
        assert resp_tx.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_f0_endpoints_present_in_openapi_schema(
    async_client: AsyncClient,
) -> None:
    """Verify all three Phase F0.2 endpoints and key schema constraints appear in /openapi.json."""
    resp = await async_client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()

    paths = spec["paths"]
    assert "/api/v1/transactions" in paths
    assert "get" in paths["/api/v1/transactions"]
    assert "/api/v1/transactions/{transaction_id}" in paths
    assert "get" in paths["/api/v1/transactions/{transaction_id}"]
    assert "/api/v1/datasets/imports" in paths
    assert "get" in paths["/api/v1/datasets/imports"]

    # Existing risk routes must remain intact
    assert "/api/v1/transactions/{transaction_id}/risk" in paths
    assert "/api/v1/transactions/{transaction_id}/risk/analyze" in paths

    schemas = spec["components"]["schemas"]
    tx_item = schemas["TransactionSummaryItem"]
    assert tx_item["properties"]["amount"]["type"] == "string"

    tx_detail = schemas["TransactionDetailResponse"]
    assert tx_detail["properties"]["amount"]["type"] == "string"
