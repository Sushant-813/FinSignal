"""API tests for /health and /ready endpoints."""

import pytest
from httpx import AsyncClient

from finsignal.core import database


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    """Verify that /health returns HTTP 200 independent of database state."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_ready_endpoint_connected(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that /ready returns HTTP 200 when database connectivity succeeds."""

    async def mock_ping(_: object) -> bool:
        return True

    monkeypatch.setattr(database, "ping_database", mock_ping)
    response = await async_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


@pytest.mark.asyncio
async def test_ready_endpoint_disconnected(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that /ready returns HTTP 503 JSONResponse when database is unreachable."""

    async def mock_ping(_: object) -> bool:
        return False

    monkeypatch.setattr(database, "ping_database", mock_ping)
    response = await async_client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "database": "disconnected"}
