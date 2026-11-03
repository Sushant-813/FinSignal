"""API contract, authentication, authorization, and error envelope tests for Phase 10 AI endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from finsignal.ai.exceptions import (
    AISummaryInProgressError,
    GroundingValidationError,
    InvestigationResolvedError,
    ProviderTimeoutError,
)
from finsignal.ai.schemas import (
    AISummaryListResponse,
    AISummaryOutput,
    AISummaryResponse,
    AISummaryStatus,
    GroundedObservation,
)
from finsignal.ai.service import AISummaryService
from finsignal.api.v1.investigations import get_ai_service
from finsignal.auth.dependencies import get_current_user
from finsignal.common.exceptions import AuthorizationError, NotFoundError
from finsignal.users.models import User


def _make_mock_user(role: str, user_id: uuid.UUID | None = None) -> User:
    user = User()
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.email = f"{role.lower()}@example.com"
    user.is_active = True
    return user


def _make_sample_summary_response(
    inv_id: uuid.UUID,
    summary_id: uuid.UUID | None = None,
    is_stale: bool = False,
) -> AISummaryResponse:
    now = datetime.now(UTC)
    s_id = summary_id or uuid.uuid4()
    tx_id = uuid.uuid4()
    output = AISummaryOutput(
        executive_summary="Sample executive summary for test case.",
        observed_facts=[
            GroundedObservation(claim="Transaction observed", evidence_ids=[tx_id]),
        ],
        derived_signals=[
            GroundedObservation(claim="Signal observed", evidence_ids=[tx_id]),
        ],
        potential_interpretations=["Account takeover hypothesis."],
        uncertainties_and_limitations=["No historical velocity records available."],
    )
    return AISummaryResponse(
        id=s_id,
        investigation_id=inv_id,
        provider="mock",
        model="mock-v1",
        prompt_version="pv_1.0",
        evidence_hash="ehash_test_123",
        context_hash="chash_test_123",
        status=AISummaryStatus.COMPLETED,
        summary=output,
        error_message=None,
        is_stale=is_stale,
        generated_at=now,
        completed_at=now,
        created_at=now,
    )


# -----------------------------------------------------------------------------
# 1. Authentication (401) Tests Across All 3 Endpoints
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ai_endpoints_unauthenticated_returns_401(
    async_client: AsyncClient,
) -> None:
    """All 3 AI endpoints reject unauthenticated requests with 401."""
    inv_id = str(uuid.uuid4())
    endpoints = [
        ("POST", f"/api/v1/investigations/{inv_id}/ai-summary"),
        ("GET", f"/api/v1/investigations/{inv_id}/ai-summary"),
        ("GET", f"/api/v1/investigations/{inv_id}/ai-summary/history"),
    ]
    for method, url in endpoints:
        if method == "POST":
            resp = await async_client.post(url, json={})
        else:
            resp = await async_client.get(url)
        assert resp.status_code == 401, (
            f"Expected 401 for {method} {url}, got {resp.status_code}"
        )
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "UNAUTHORIZED"


# -----------------------------------------------------------------------------
# 2. RBAC & Authorization (403) Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_ai_summary_forbidden_for_analyst(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """ANALYST role cannot trigger POST generation (requires ADMIN or INVESTIGATOR)."""
    analyst = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: analyst
    inv_id = str(uuid.uuid4())

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{inv_id}/ai-summary", json={}
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_generate_ai_summary_investigator_unassigned_forbidden(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """INVESTIGATOR cannot generate summary for an investigation not assigned to them."""
    investigator = _make_mock_user("INVESTIGATOR")
    app.dependency_overrides[get_current_user] = lambda: investigator

    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.generate_summary.side_effect = AuthorizationError(
        "Investigators can only access AI summaries for investigations assigned to themselves."
    )
    app.dependency_overrides[get_ai_service] = lambda: mock_service
    inv_id = str(uuid.uuid4())

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{inv_id}/ai-summary", json={}
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


# -----------------------------------------------------------------------------
# 3. Successful Generation & Schema Contract
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_ai_summary_admin_success(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """ADMIN can successfully generate and receive completed AI summary."""
    admin = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin

    inv_id = uuid.uuid4()
    sample_dto = _make_sample_summary_response(inv_id=inv_id)

    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.generate_summary.return_value = sample_dto
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{inv_id}/ai-summary", json={}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_dto.id)
        assert body["status"] == "COMPLETED"
        assert body["is_stale"] is False
        assert "observed_facts" in body["summary"]
        assert "derived_signals" in body["summary"]
        assert len(body["summary"]["observed_facts"]) == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


# -----------------------------------------------------------------------------
# 4. Error Status Codes: 404, 409, 502, 504
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_ai_summary_not_found(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """404 when investigation does not exist."""
    admin = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin

    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.generate_summary.side_effect = NotFoundError("Investigation not found")
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{uuid.uuid4()}/ai-summary", json={}
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


@pytest.mark.asyncio
async def test_generate_ai_summary_resolved_conflict(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """409 when investigation is resolved."""
    admin = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin

    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.generate_summary.side_effect = InvestigationResolvedError()
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{uuid.uuid4()}/ai-summary", json={}
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INVESTIGATION_ALREADY_RESOLVED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


@pytest.mark.asyncio
async def test_generate_ai_summary_in_progress_conflict(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """409 when an active summary is currently generating."""
    admin = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin

    active_id = uuid.uuid4()
    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.generate_summary.side_effect = AISummaryInProgressError(
        details={"active_summary_id": str(active_id)}
    )
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{uuid.uuid4()}/ai-summary", json={}
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"]["code"] == "AI_SUMMARY_IN_PROGRESS"
        assert body["error"]["details"]["active_summary_id"] == str(active_id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


@pytest.mark.asyncio
async def test_generate_ai_summary_provider_timeout_504(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """504 when upstream provider times out, returning summary_id in error details."""
    admin = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin

    failed_summary_id = uuid.uuid4()
    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.generate_summary.side_effect = ProviderTimeoutError(
        "AI provider timed out.",
        details={"summary_id": str(failed_summary_id), "status": "FAILED"},
    )
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{uuid.uuid4()}/ai-summary", json={}
        )
        assert resp.status_code == 504
        body = resp.json()
        assert body["error"]["code"] == "PROVIDER_TIMEOUT"
        assert body["error"]["details"]["summary_id"] == str(failed_summary_id)
        assert body["error"]["details"]["status"] == "FAILED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


@pytest.mark.asyncio
async def test_generate_ai_summary_bad_gateway_502(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """502 when provider returns malformed output or fails grounding validation."""
    admin = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin

    failed_summary_id = uuid.uuid4()
    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.generate_summary.side_effect = GroundingValidationError(
        "Grounding validation failure: citations not in context",
        details={"summary_id": str(failed_summary_id), "status": "FAILED"},
    )
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.post(
            f"/api/v1/investigations/{uuid.uuid4()}/ai-summary", json={}
        )
        assert resp.status_code == 502
        body = resp.json()
        assert body["error"]["code"] == "GROUNDING_VALIDATION_ERROR"
        assert body["error"]["details"]["summary_id"] == str(failed_summary_id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


# -----------------------------------------------------------------------------
# 5. Get Latest Summary & Staleness Flag
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_latest_ai_summary_success(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """GET /api/v1/investigations/{id}/ai-summary returns latest summary with staleness flag."""
    analyst = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: analyst

    inv_id = uuid.uuid4()
    sample_dto = _make_sample_summary_response(inv_id=inv_id, is_stale=True)

    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.get_latest_summary.return_value = sample_dto
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.get(f"/api/v1/investigations/{inv_id}/ai-summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_dto.id)
        assert body["is_stale"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)


# -----------------------------------------------------------------------------
# 6. History Pagination
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_ai_summary_history_paginated(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    """GET /api/v1/investigations/{id}/ai-summary/history returns paginated summary items."""
    admin = _make_mock_user("ADMIN")
    app.dependency_overrides[get_current_user] = lambda: admin

    inv_id = uuid.uuid4()
    item = _make_sample_summary_response(inv_id=inv_id)
    history_dto = AISummaryListResponse(
        items=[item],
        total=1,
        page=1,
        page_size=10,
        total_pages=1,
    )

    mock_service = AsyncMock(spec=AISummaryService)
    mock_service.list_summary_history.return_value = history_dto
    app.dependency_overrides[get_ai_service] = lambda: mock_service

    try:
        resp = await async_client.get(
            f"/api/v1/investigations/{inv_id}/ai-summary/history?page=1&page_size=10"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["page_size"] == 10
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == str(item.id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_service, None)
