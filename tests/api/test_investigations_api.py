"""API contract, authentication, and authorization tests for /api/v1/investigations endpoints (Phase 9)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from finsignal.api.v1.investigations import get_investigation_service
from finsignal.auth.dependencies import get_current_user
from finsignal.common.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from finsignal.investigations.schemas import (
    EvidenceSourceType,
    EvidenceType,
    InvestigationDetailResponse,
    InvestigationEvidenceListResponse,
    InvestigationEvidenceResponse,
    InvestigationListResponse,
    InvestigationPrimaryTransactionDTO,
    InvestigationPriority,
    InvestigationRelationshipType,
    InvestigationStatus,
    InvestigationSummaryItem,
    InvestigationTransactionItem,
    InvestigationTransactionsListResponse,
)
from finsignal.investigations.service import InvestigationService
from finsignal.users.models import User


def _make_mock_user(role: str, user_id: uuid.UUID | None = None) -> User:
    user = User()
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.email = f"{role.lower()}@example.com"
    user.is_active = True
    return user


def _make_sample_detail_response(
    inv_id: uuid.UUID | None = None,
    status: InvestigationStatus = InvestigationStatus.OPEN,
    priority: InvestigationPriority = InvestigationPriority.MEDIUM,
    assigned_to: uuid.UUID | None = None,
) -> InvestigationDetailResponse:
    now = datetime.now(UTC)
    primary_tx = InvestigationPrimaryTransactionDTO(
        id=uuid.uuid4(),
        external_transaction_id="TX_1001",
        account_id=uuid.uuid4(),
        amount="250.00",
        currency="USD",
        direction="DEBIT",
        occurred_at=now,
        source_namespace="SYNTHETIC",
        category="RETAIL",
        payment_method="CARD",
    )
    return InvestigationDetailResponse(
        id=inv_id or uuid.uuid4(),
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        assigned_user_email="investigator@example.com" if assigned_to else None,
        primary_transaction=primary_tx,
        latest_risk_analysis=None,
        related_transactions=[],
        resolution=None,
        resolution_notes=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_investigation_service() -> AsyncMock:
    """Mock InvestigationService returning schema-compliant DTO responses."""
    mock = AsyncMock(spec=InvestigationService)
    detail = _make_sample_detail_response()
    mock.create_investigation.return_value = detail
    mock.get_investigation_workspace.return_value = detail
    mock.patch_investigation.return_value = detail
    mock.resolve_investigation.return_value = _make_sample_detail_response(
        status=InvestigationStatus.RESOLVED
    )

    mock.list_investigations.return_value = InvestigationListResponse(
        items=[
            InvestigationSummaryItem(
                id=detail.id,
                status=detail.status,
                priority=detail.priority,
                assigned_to=detail.assigned_to,
                primary_transaction_id=detail.primary_transaction.id,
                account_id=detail.primary_transaction.account_id,
                created_at=detail.created_at,
                updated_at=detail.updated_at,
            )
        ],
        page=1,
        page_size=25,
        total=1,
        total_pages=1,
    )

    mock.get_investigation_transactions.return_value = (
        InvestigationTransactionsListResponse(
            investigation_id=detail.id,
            items=[
                InvestigationTransactionItem(
                    transaction_id=detail.primary_transaction.id,
                    relationship_type=InvestigationRelationshipType.PRIMARY,
                    account_id=detail.primary_transaction.account_id,
                    amount="250.00",
                    currency="USD",
                    direction="DEBIT",
                    occurred_at=detail.primary_transaction.occurred_at,
                    created_at=detail.created_at,
                )
            ],
        )
    )

    mock.add_related_transaction.return_value = InvestigationTransactionItem(
        transaction_id=uuid.uuid4(),
        relationship_type=InvestigationRelationshipType.RELATED,
        account_id=uuid.uuid4(),
        amount="100.00",
        currency="USD",
        direction="DEBIT",
        occurred_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )

    evidence_item = InvestigationEvidenceResponse(
        id=uuid.uuid4(),
        investigation_id=detail.id,
        evidence_type=EvidenceType.USER_NOTE,
        source_type=EvidenceSourceType.USER_NOTE,
        source_id=None,
        title="Sample Note",
        description="Notes from review",
        payload={"note": "Initial observations"},
        created_at=datetime.now(UTC),
    )
    mock.list_evidence.return_value = InvestigationEvidenceListResponse(
        items=[evidence_item],
        page=1,
        page_size=50,
        total=1,
        total_pages=1,
    )
    mock.attach_evidence.return_value = evidence_item

    return mock


# -----------------------------------------------------------------------------
# 1. Authentication (401) Tests Across All 9 Endpoints
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_investigations_unauthenticated_returns_401(
    async_client: AsyncClient,
) -> None:
    """Verify all 9 investigation endpoints reject unauthenticated requests with 401."""
    inv_id = str(uuid.uuid4())

    endpoints = [
        ("GET", "/api/v1/investigations"),
        ("POST", "/api/v1/investigations"),
        ("GET", f"/api/v1/investigations/{inv_id}"),
        ("PATCH", f"/api/v1/investigations/{inv_id}"),
        ("POST", f"/api/v1/investigations/{inv_id}/resolve"),
        ("GET", f"/api/v1/investigations/{inv_id}/transactions"),
        ("POST", f"/api/v1/investigations/{inv_id}/transactions"),
        ("GET", f"/api/v1/investigations/{inv_id}/evidence"),
        ("POST", f"/api/v1/investigations/{inv_id}/evidence"),
    ]

    for method, url in endpoints:
        if method == "GET":
            resp = await async_client.get(url)
        elif method == "POST":
            resp = await async_client.post(url, json={})
        elif method == "PATCH":
            resp = await async_client.patch(url, json={})
        assert resp.status_code == 401, f"{method} {url} returned {resp.status_code}"
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# -----------------------------------------------------------------------------
# 2. Endpoint: GET /api/v1/investigations (Listing & Filtering)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_investigations_success(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify listing investigations returns 200 with standard pagination envelope."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        resp = await async_client.get("/api/v1/investigations?page=1&page_size=25")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["page"] == 1
        assert body["total"] == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_investigations_filter_conflict_422(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify combining assigned_to with unassigned=true returns 422."""
    user = _make_mock_user("ADMIN")
    mock_investigation_service.list_investigations.side_effect = ValidationError(
        "Cannot combine assigned_to filter with unassigned=true.",
        code="FILTER_CONFLICT",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        uid = str(uuid.uuid4())
        resp = await async_client.get(
            f"/api/v1/investigations?assigned_to={uid}&unassigned=true"
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "FILTER_CONFLICT"
    finally:
        app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 3. Endpoint: POST /api/v1/investigations (Creation)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_investigation_success(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify creating investigation returns 201 with detail response."""
    user = _make_mock_user("INVESTIGATOR")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        tx_id = str(uuid.uuid4())
        resp = await async_client.post(
            "/api/v1/investigations",
            json={"transaction_id": tx_id, "priority": "HIGH"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "primary_transaction" in body
        assert body["status"] == "OPEN"
    finally:
        app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 4. Endpoint: GET /api/v1/investigations/{id} (Workspace Detail)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_investigation_not_found_404(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify missing investigation returns 404."""
    user = _make_mock_user("ANALYST")
    inv_id = uuid.uuid4()
    mock_investigation_service.get_investigation_workspace.side_effect = NotFoundError(
        f"Investigation '{inv_id}' was not found.",
        code="INVESTIGATION_NOT_FOUND",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        resp = await async_client.get(f"/api/v1/investigations/{inv_id}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "INVESTIGATION_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 5. Endpoint: PATCH /api/v1/investigations/{id} (Mutations)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_patch_investigation_analyst_forbidden_403(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify ANALYST cannot patch investigations (HTTP 403)."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        inv_id = str(uuid.uuid4())
        resp = await async_client.patch(
            f"/api/v1/investigations/{inv_id}",
            json={"priority": "CRITICAL"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_investigation_invalid_lifecycle_transition_409(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify patching status to RESOLVED via PATCH returns 409 conflict."""
    user = _make_mock_user("ADMIN")
    mock_investigation_service.patch_investigation.side_effect = ConflictError(
        "Resolution must use the dedicated /resolve endpoint.",
        code="INVALID_LIFECYCLE_TRANSITION",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        inv_id = str(uuid.uuid4())
        resp = await async_client.patch(
            f"/api/v1/investigations/{inv_id}",
            json={"status": "RESOLVED"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INVALID_LIFECYCLE_TRANSITION"
    finally:
        app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 6. Endpoint: POST /api/v1/investigations/{id}/resolve (Resolution)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resolve_investigation_whitespace_notes_rejected_422(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify whitespace-only resolution notes are rejected with 422."""
    user = _make_mock_user("INVESTIGATOR")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        inv_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/api/v1/investigations/{inv_id}/resolve",
            json={
                "resolution": "CONFIRMED_FRAUD",
                "resolution_notes": "   \n\t  ",
            },
        )
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_resolve_investigation_success(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify valid resolution returns 200 with RESOLVED status."""
    user = _make_mock_user("INVESTIGATOR")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        inv_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/api/v1/investigations/{inv_id}/resolve",
            json={
                "resolution": "CONFIRMED_FRAUD",
                "resolution_notes": "Compromised credential identified.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "RESOLVED"
    finally:
        app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 7. Endpoint: Transactions Link Management
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_link_related_transaction_success(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify linking related transaction returns 201."""
    user = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        inv_id = str(uuid.uuid4())
        tx_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/api/v1/investigations/{inv_id}/transactions",
            json={"transaction_id": tx_id},
        )
        assert resp.status_code == 201
        assert resp.json()["relationship_type"] == "RELATED"
    finally:
        app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 8. Endpoint: Evidence Attachment & Listing
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_attach_evidence_success(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify attaching evidence returns 201."""
    user = _make_mock_user("INVESTIGATOR")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        inv_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/api/v1/investigations/{inv_id}/evidence",
            json={
                "evidence_type": "USER_NOTE",
                "source_type": "USER_NOTE",
                "source_id": None,
                "title": "Reviewer notes",
                "payload": {"note": "Investigator observations"},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["evidence_type"] == "USER_NOTE"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_evidence_success(
    app: FastAPI,
    async_client: AsyncClient,
    mock_investigation_service: AsyncMock,
) -> None:
    """Verify listing evidence returns 200 with items list."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_investigation_service] = lambda: (
        mock_investigation_service
    )

    try:
        inv_id = str(uuid.uuid4())
        resp = await async_client.get(f"/api/v1/investigations/{inv_id}/evidence")
        assert resp.status_code == 200
        assert "items" in resp.json()
    finally:
        app.dependency_overrides.clear()
