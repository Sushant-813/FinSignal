"""API tests for /health and /ready endpoints."""

import pytest
from httpx import AsyncClient

from finsignal.core import database


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/health", "/api/v1/health"])
async def test_health_endpoint(async_client: AsyncClient, path: str) -> None:
    """Verify that /health and /api/v1/health return HTTP 200 independent of database state and carry request headers."""
    response = await async_client.get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers.get("X-Request-ID") is not None
    assert response.headers.get("X-Process-Time") is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/ready", "/api/v1/ready"])
async def test_ready_endpoint_connected(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """Verify that /ready and /api/v1/ready return HTTP 200 when database connectivity succeeds and carry request headers."""

    async def mock_ping(_: object) -> bool:
        return True

    monkeypatch.setattr(database, "ping_database", mock_ping)
    response = await async_client.get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}
    assert response.headers.get("X-Request-ID") is not None
    assert response.headers.get("X-Process-Time") is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/ready", "/api/v1/ready"])
async def test_ready_endpoint_disconnected(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """Verify that /ready and /api/v1/ready return HTTP 503 JSONResponse when database is unreachable."""

    async def mock_ping(_: object) -> bool:
        return False

    monkeypatch.setattr(database, "ping_database", mock_ping)
    response = await async_client.get(path)
    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "database": "disconnected"}
    assert response.headers.get("X-Request-ID") is not None
    assert response.headers.get("X-Process-Time") is not None
