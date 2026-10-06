"""Pytest configuration and test fixtures for FinSignal."""

import os

# Ensure safe test environment defaults before any module imports
os.environ.setdefault("DATABASE_PASSWORD", "test_password")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("ENVIRONMENT", "testing")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from pydantic import SecretStr  # noqa: E402

from finsignal.core.config import Settings  # noqa: E402
from finsignal.main import create_app  # noqa: E402


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated test settings pointing to finsignal_test."""
    pw = (
        os.environ.get("POSTGRES_PASSWORD")
        or os.environ.get("DATABASE_PASSWORD")
        or "test_password"
    )
    return Settings(
        app_name="FinSignalTest",
        environment="testing",
        database_host=os.environ.get("POSTGRES_HOST", "localhost"),
        database_port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database_name="finsignal_test",
        database_user=os.environ.get("POSTGRES_USER", "postgres"),
        database_password=SecretStr(pw),
        _env_file=None,
    )


@pytest.fixture
async def app(test_settings: Settings) -> AsyncGenerator[FastAPI, None]:
    """Provide an application instance managed by its lifespan context.

    Ensures lifespan startup and shutdown (engine disposal) execute properly.
    """
    application = create_app(test_settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient wired to the test application."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
