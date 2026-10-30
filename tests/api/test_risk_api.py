"""API contract and authorization tests for /api/v1/transactions/{id}/risk endpoints (Phase 8)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from finsignal.api.v1.risk import get_risk_service
from finsignal.auth.dependencies import get_current_user
from finsignal.common.exceptions import AuthorizationError, NotFoundError
from finsignal.risk.exceptions import (
    IneligibleModelStatusError,
    RiskAnalysisNotFoundError,
)
from finsignal.risk.schemas import (
    RiskAnalysisResponse,
    RiskFactorCode,
    RiskFactorDTO,
    RiskLevel,
    RiskSeverity,
)
from finsignal.risk.service import RiskService
from finsignal.users.models import User


def _make_mock_user(role: str) -> User:
    """Helper to construct mock User object with specified role."""
    user = User()
    user.id = uuid.uuid4()
    user.role = role
    user.email = f"{role.lower()}@example.com"
    user.is_active = True
    return user


def _make_sample_risk_response(
    tx_id: uuid.UUID | None = None,
) -> RiskAnalysisResponse:
    """Helper to construct a compliant RiskAnalysisResponse."""
    transaction_id = tx_id or uuid.uuid4()
    model_id = uuid.uuid4()
    return RiskAnalysisResponse(
        id=uuid.uuid4(),
        transaction_id=transaction_id,
        model_version_id=model_id,
        model_version="1.0.0",
        config_version="risk_v1.0",
        feature_vector_hash="abcdef0123456789" * 4,
        score=68.5,
        risk_level=RiskLevel.HIGH,
        ml_anomaly_score=0.25,
        ml_threshold=0.12,
        normalized_ml_score=72.0,
        rule_score=60.0,
        factors=[
            RiskFactorDTO(
                code=RiskFactorCode.HIGH_VELOCITY,
                label="High Velocity",
                severity=RiskSeverity.HIGH,
                description="4 transactions in 5 minutes",
                value_numeric=Decimal("4.0"),
                value_text=None,
                evidence={"window_minutes": 5, "count": 4},
            )
        ],
        normalization_params={
            "method": "piecewise_linear",
            "s_min": -0.80,
            "tau": 0.12,
            "s_max": 0.90,
        },
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_risk_service() -> AsyncMock:
    """Mock RiskService returning compliant response models."""
    mock = AsyncMock(spec=RiskService)
    mock.get_latest_analysis.return_value = _make_sample_risk_response()
    mock.analyze_transaction.return_value = _make_sample_risk_response()
    return mock


@pytest.mark.asyncio
async def test_risk_unauthenticated_returns_401(async_client: AsyncClient) -> None:
    """Verify all risk endpoints reject unauthenticated requests with 401."""
    random_id = str(uuid.uuid4())
    get_url = f"/api/v1/transactions/{random_id}/risk"
    post_url = f"/api/v1/transactions/{random_id}/risk/analyze"

    resp_get = await async_client.get(get_url)
    assert resp_get.status_code == 401
    assert resp_get.json()["error"]["code"] == "UNAUTHORIZED"

    resp_post = await async_client.post(post_url, json={})
    assert resp_post.status_code == 401
    assert resp_post.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ADMIN", "ANALYST", "INVESTIGATOR"])
async def test_risk_permitted_roles_allowed(
    app: FastAPI,
    async_client: AsyncClient,
    mock_risk_service: AsyncMock,
    role: str,
) -> None:
    """Verify approved roles (ADMIN, ANALYST, INVESTIGATOR) can access risk endpoints."""
    user = _make_mock_user(role)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_risk_service] = lambda: mock_risk_service

    try:
        tx_id = str(uuid.uuid4())
        # Test GET
        resp_get = await async_client.get(f"/api/v1/transactions/{tx_id}/risk")
        assert resp_get.status_code == 200
        data_get = resp_get.json()
        assert "score" in data_get
        assert data_get["risk_level"] == "HIGH"
        assert len(data_get["factors"]) == 1

        # Test POST analyze
        resp_post = await async_client.post(
            f"/api/v1/transactions/{tx_id}/risk/analyze",
            json={},
        )
        assert resp_post.status_code == 200
        data_post = resp_post.json()
        assert data_post["score"] == 68.50
        assert data_post["risk_level"] == "HIGH"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_risk_unauthorized_role_forbidden(
    app: FastAPI,
    async_client: AsyncClient,
    mock_risk_service: AsyncMock,
) -> None:
    """Verify unauthorized role (e.g. AUDITOR) receives 403 Forbidden."""
    user = _make_mock_user("AUDITOR")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_risk_service] = lambda: mock_risk_service

    try:
        tx_id = str(uuid.uuid4())
        resp_get = await async_client.get(f"/api/v1/transactions/{tx_id}/risk")
        assert resp_get.status_code == 403
        assert resp_get.json()["error"]["code"] == "FORBIDDEN"

        resp_post = await async_client.post(
            f"/api/v1/transactions/{tx_id}/risk/analyze",
            json={},
        )
        assert resp_post.status_code == 403
        assert resp_post.json()["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_risk_analysis_not_found(
    app: FastAPI,
    async_client: AsyncClient,
    mock_risk_service: AsyncMock,
) -> None:
    """Verify GET returns 404 with RISK_ANALYSIS_NOT_FOUND if unanalyzed."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_risk_service] = lambda: mock_risk_service

    tx_id = uuid.uuid4()
    mock_risk_service.get_latest_analysis.side_effect = RiskAnalysisNotFoundError(
        message=f"No risk analysis found for transaction '{tx_id}'.",
        details={"transaction_id": str(tx_id)},
    )

    try:
        resp = await async_client.get(f"/api/v1/transactions/{tx_id}/risk")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "RISK_ANALYSIS_NOT_FOUND"
        assert str(tx_id) in data["error"]["message"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_risk_transaction_not_found(
    app: FastAPI,
    async_client: AsyncClient,
    mock_risk_service: AsyncMock,
) -> None:
    """Verify GET returns 404 with RESOURCE_NOT_FOUND if transaction does not exist."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_risk_service] = lambda: mock_risk_service

    tx_id = uuid.uuid4()
    mock_risk_service.get_latest_analysis.side_effect = NotFoundError(
        message=f"Transaction {tx_id} not found."
    )

    try:
        resp = await async_client.get(f"/api/v1/transactions/{tx_id}/risk")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_analyze_ineligible_model_status_returns_422(
    app: FastAPI,
    async_client: AsyncClient,
    mock_risk_service: AsyncMock,
) -> None:
    """Verify analyze returns 422 if an ineligible model (EXPERIMENTAL) is requested."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_risk_service] = lambda: mock_risk_service

    mock_model_id = uuid.uuid4()
    mock_risk_service.analyze_transaction.side_effect = IneligibleModelStatusError(
        message="EXPERIMENTAL models are ineligible for transaction risk analysis.",
        details={"model_id": str(mock_model_id), "status": "EXPERIMENTAL"},
    )

    try:
        tx_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/api/v1/transactions/{tx_id}/risk/analyze",
            json={"model_version_id": str(mock_model_id)},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "INELIGIBLE_MODEL_STATUS"
        assert "EXPERIMENTAL" in data["error"]["message"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_analyze_non_admin_validated_model_forbidden(
    app: FastAPI,
    async_client: AsyncClient,
    mock_risk_service: AsyncMock,
) -> None:
    """Verify non-admin user cannot analyze using a VALIDATED model."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_risk_service] = lambda: mock_risk_service

    mock_model_id = uuid.uuid4()
    mock_risk_service.analyze_transaction.side_effect = AuthorizationError(
        message="Only administrators may evaluate transactions using VALIDATED models.",
        details={"model_id": str(mock_model_id), "status": "VALIDATED"},
    )

    try:
        tx_id = str(uuid.uuid4())
        resp = await async_client.post(
            f"/api/v1/transactions/{tx_id}/risk/analyze",
            json={"model_version_id": str(mock_model_id)},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_response_schema_does_not_leak_internals(
    app: FastAPI,
    async_client: AsyncClient,
    mock_risk_service: AsyncMock,
) -> None:
    """Verify the risk response does not leak internal artifact paths or secrets."""
    user = _make_mock_user("ANALYST")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_risk_service] = lambda: mock_risk_service

    try:
        tx_id = str(uuid.uuid4())
        resp = await async_client.get(f"/api/v1/transactions/{tx_id}/risk")
        assert resp.status_code == 200
        raw_json_str = resp.text

        # Verify no artifact file paths or internal tokens
        assert "artifact_uri" not in raw_json_str
        assert "artifact_path" not in raw_json_str
        assert "secret" not in raw_json_str.lower()
        assert ".joblib" not in raw_json_str
    finally:
        app.dependency_overrides.clear()
