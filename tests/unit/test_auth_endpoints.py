"""Unit tests for authentication API endpoints and validation contracts."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from finsignal.api.v1.auth import get_me, login, logout, register
from finsignal.auth.dependencies import get_auth_service, get_current_user
from finsignal.auth.schemas import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from finsignal.auth.service import AuthService
from finsignal.common.exceptions import AuthenticationError, ConflictError
from finsignal.core.config import Settings
from finsignal.main import create_app
from finsignal.users.models import User


@pytest.fixture
def test_settings() -> Settings:
    """Isolated test settings."""
    return Settings(
        app_name="FinSignalEndpointUnitTest",
        environment="testing",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        _env_file=None,
    )


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    """Mock AuthService for endpoint unit tests."""
    return AsyncMock(spec=AuthService)


@pytest.mark.asyncio
async def test_register_handler_success(mock_auth_service: AsyncMock) -> None:
    """Verify register handler delegates to AuthService and returns 201 UserResponse."""
    req = RegisterRequest(email="newuser@example.com", password="secure-password-123")
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    expected_response = UserResponse(
        id=user_id,
        email="newuser@example.com",
        role="ANALYST",
        is_active=True,
        created_at=now,
    )
    mock_auth_service.register.return_value = expected_response
    mock_session = AsyncMock()

    result = await register(
        request=req,
        session=mock_session,
        auth_service=mock_auth_service,
    )

    assert result == expected_response
    mock_auth_service.register.assert_awaited_once_with(
        session=mock_session, request=req
    )


@pytest.mark.asyncio
async def test_login_handler_success(mock_auth_service: AsyncMock) -> None:
    """Verify login handler delegates to AuthService and returns 200 TokenResponse."""
    req = LoginRequest(email="user@example.com", password="secure-password-123")
    expected_response = TokenResponse(
        access_token="mocked.jwt.token",
        token_type="bearer",
        expires_in=1800,
    )
    mock_auth_service.login.return_value = expected_response
    mock_session = AsyncMock()

    result = await login(
        request=req,
        session=mock_session,
        auth_service=mock_auth_service,
    )

    assert result == expected_response
    mock_auth_service.login.assert_awaited_once_with(session=mock_session, request=req)


@pytest.mark.asyncio
async def test_get_me_handler_returns_public_fields() -> None:
    """Verify get_me returns strictly public user representation without internal fields."""
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ANALYST",
        is_active=True,
        created_at=now,
    )

    result = await get_me(current_user=user)

    assert isinstance(result, UserResponse)
    assert result.id == user_id
    assert result.email == "analyst@example.com"
    assert result.role == "ANALYST"
    assert result.is_active is True
    assert result.created_at == now
    # Verify sensitive attributes are absent from UserResponse model
    data = result.model_dump()
    assert "password_hash" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_logout_handler_returns_stateless_confirmation() -> None:
    """Verify logout returns standard stateless confirmation message."""
    user = User(
        id=uuid.uuid4(),
        email="analyst@example.com",
        password_hash="hash",
        role="ANALYST",
        is_active=True,
    )
    result = await logout(current_user=user)

    assert isinstance(result, LogoutResponse)
    assert result.message == "Successfully logged out."


@pytest.mark.asyncio
async def test_register_endpoint_rejects_client_supplied_role(
    test_settings: Settings,
) -> None:
    """Verify POST /api/v1/auth/register rejects client-supplied role with 422."""
    app = create_app(test_settings)
    payload = {
        "email": "analyst@example.com",
        "password": "secure-password-123",
        "role": "ADMIN",
    }

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "extra_fields" in data["error"].get("details", {})
    assert "Unexpected field in payload." in data["error"]["details"]["extra_fields"]


@pytest.mark.asyncio
async def test_register_endpoint_rejects_short_password(
    test_settings: Settings,
) -> None:
    """Verify POST /api/v1/auth/register rejects passwords shorter than 12 characters."""
    app = create_app(test_settings)
    payload = {
        "email": "analyst@example.com",
        "password": "short",
    }

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_register_endpoint_conflict_error_envelope(
    test_settings: Settings,
    mock_auth_service: AsyncMock,
) -> None:
    """Verify duplicate email conflict maps cleanly to HTTP 409 STATE_CONFLICT envelope."""
    app = create_app(test_settings)
    mock_auth_service.register.side_effect = ConflictError(
        message="A user with this email address already exists.",
        code="STATE_CONFLICT",
    )
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    payload = {
        "email": "existing@example.com",
        "password": "secure-password-123",
    }

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "STATE_CONFLICT"
    assert "already exists" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_endpoint_authentication_error_envelope(
    test_settings: Settings,
    mock_auth_service: AsyncMock,
) -> None:
    """Verify invalid credentials map to HTTP 401 UNAUTHORIZED envelope."""
    app = create_app(test_settings)
    mock_auth_service.login.side_effect = AuthenticationError(
        message="Invalid email or password.",
        code="UNAUTHORIZED",
    )
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    payload = {
        "email": "user@example.com",
        "password": "wrong-password-123",
    }

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "invalid email or password" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_endpoint_inactive_user_error_envelope(
    test_settings: Settings,
    mock_auth_service: AsyncMock,
) -> None:
    """Verify inactive user login produces HTTP 401 UNAUTHORIZED envelope."""
    app = create_app(test_settings)
    mock_auth_service.login.side_effect = AuthenticationError(
        message="User account is inactive.",
        code="UNAUTHORIZED",
    )
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    payload = {
        "email": "inactive@example.com",
        "password": "secure-password-123",
    }

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "inactive" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_me_endpoint_requires_authentication(
    test_settings: Settings,
) -> None:
    """Verify GET /api/v1/auth/me rejects unauthenticated requests with HTTP 401."""
    app = create_app(test_settings)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_me_endpoint_authenticated_returns_user(
    test_settings: Settings,
) -> None:
    """Verify GET /api/v1/auth/me returns 200 UserResponse when authenticated."""
    app = create_app(test_settings)
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    mock_user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash="argon2id_hash",
        role="ANALYST",
        is_active=True,
        created_at=now,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["email"] == "analyst@example.com"
    assert data["role"] == "ANALYST"
    assert data["is_active"] is True
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_logout_endpoint_requires_authentication(
    test_settings: Settings,
) -> None:
    """Verify POST /api/v1/auth/logout rejects unauthenticated requests with HTTP 401."""
    app = create_app(test_settings)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_logout_endpoint_authenticated_success(
    test_settings: Settings,
) -> None:
    """Verify POST /api/v1/auth/logout returns HTTP 200 with LogoutResponse when authenticated."""
    app = create_app(test_settings)
    mock_user = User(
        id=uuid.uuid4(),
        email="analyst@example.com",
        password_hash="argon2id_hash",
        role="ANALYST",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out."}
