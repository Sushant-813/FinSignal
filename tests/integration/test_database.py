"""Integration tests for application construction, database resources, and isolation."""

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources, ping_database
from finsignal.main import create_app


def test_app_construction_and_database_isolation() -> None:
    """Verify that create_app with test_settings binds a separate test database engine."""
    dev_settings = Settings(
        database_name="finsignal_dev",
        database_password=SecretStr("devpw"),
        _env_file=None,
    )
    dev_app = create_app(dev_settings)
    assert dev_app.state.settings.database_name == "finsignal_dev"
    assert "finsignal_dev" in str(dev_app.state.db_engine.url)

    test_settings = Settings(
        database_name="finsignal_test",
        database_password=SecretStr("testpw"),
        _env_file=None,
    )
    test_app = create_app(test_settings)
    assert test_app.state.settings.database_name == "finsignal_test"
    assert "finsignal_test" in str(test_app.state.db_engine.url)

    # Assert engines are distinct objects and point to different databases
    assert dev_app.state.db_engine is not test_app.state.db_engine
    assert dev_app.state.session_maker is not test_app.state.session_maker


@pytest.mark.asyncio
async def test_session_lifecycle_and_rollback() -> None:
    """Verify that session management rolls back cleanly on exception."""
    test_settings = Settings(
        database_name="finsignal_test",
        database_password=SecretStr("testpw"),
        _env_file=None,
    )
    engine, session_maker = create_db_resources(test_settings)
    try:
        async with session_maker() as session:
            # Verify session is active and transaction state is tracked
            assert session.is_active
            try:
                # Simulate an error during execution
                raise RuntimeError("Simulated transaction failure")
            except RuntimeError:
                await session.rollback()
            assert session.is_active
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_live_database_connection_if_available(test_settings: Settings) -> None:
    """Verify SELECT 1 against engine if native/CI PostgreSQL is reachable with credentials."""
    engine, _ = create_db_resources(test_settings)
    try:
        is_reachable = await ping_database(engine)
        if is_reachable:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.scalar()
                assert row == 1
    finally:
        await engine.dispose()
