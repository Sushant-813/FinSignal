"""API tests for Cross-Origin Resource Sharing (CORS) middleware (SEC-01)."""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from finsignal.core.config import Settings
from finsignal.main import create_app


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin() -> None:
    """Verify that OPTIONS preflight request with allowed origin returns 200 with CORS headers."""
    settings = Settings(
        database_password=SecretStr("supersecret"),
        cors_origins=["http://localhost:3000", "https://app.finsignal.com"],
        _env_file=None,
    )
    test_app = create_app(settings=settings)
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Custom-Header",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert "GET" in (response.headers.get("access-control-allow-methods") or "")


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_origin() -> None:
    """Verify that OPTIONS preflight request from untrusted origin does NOT receive allow headers."""
    settings = Settings(
        database_password=SecretStr("supersecret"),
        cors_origins=["http://localhost:3000"],
        _env_file=None,
    )
    test_app = create_app(settings=settings)
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://evil-attacker.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") is None


@pytest.mark.asyncio
async def test_cors_actual_request_headers() -> None:
    """Verify that simple GET request from allowed origin includes access-control-allow-origin header."""
    settings = Settings(
        database_password=SecretStr("supersecret"),
        cors_origins=["http://localhost:3000"],
        _env_file=None,
    )
    test_app = create_app(settings=settings)
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert response.headers.get("X-Request-ID") is not None
