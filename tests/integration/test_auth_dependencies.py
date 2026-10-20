"""Integration tests for authentication dependencies and RBAC on disposable PostgreSQL."""

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Annotated, Any

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi import APIRouter, Depends
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.dependencies import get_current_user, require_roles
from finsignal.auth.security import create_access_token
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.main import create_app
from finsignal.users.models import User
from finsignal.users.repository import UserRepository
from tests.integration.test_constraints import (
    get_admin_connection_params,
    is_live_postgres_available,
)

# Router to exercise authentication dependencies through real HTTP requests
auth_test_router = APIRouter(prefix="/test-auth", tags=["TestAuth"])


@auth_test_router.get("/protected")
async def protected_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Test endpoint requiring any authenticated, active user."""
    return {"id": str(current_user.id), "role": current_user.role}


@auth_test_router.get("/admin-only")
async def admin_only_endpoint(
    current_user: Annotated[User, Depends(require_roles("ADMIN"))],
) -> dict[str, str]:
    """Test endpoint restricted strictly to ADMIN role."""
    return {"id": str(current_user.id), "role": current_user.role}


@auth_test_router.get("/investigator-or-admin")
async def investigator_or_admin_endpoint(
    current_user: Annotated[User, Depends(require_roles("ADMIN", "INVESTIGATOR"))],
) -> dict[str, str]:
    """Test endpoint accessible by ADMIN or INVESTIGATOR."""
    return {"id": str(current_user.id), "role": current_user.role}


@pytest.fixture(scope="module")
def disposable_db() -> Generator[dict[str, Any], None, None]:
    """Provision a dedicated, disposable PostgreSQL test database."""
    if not is_live_postgres_available():
        pytest.skip("PostgreSQL is not reachable with configured credentials.")

    active_env = os.environ.get("ENVIRONMENT", "")
    if active_env != "testing":
        raise RuntimeError(
            f"Safety abort: Refusing to create disposable test DB in non-testing environment: {active_env!r}"
        )

    params = get_admin_connection_params()
    ephemeral_db_name = f"finsignal_test_ephem_{uuid.uuid4().hex[:8]}"

    admin_conn = psycopg.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname="postgres",
        autocommit=True,
    )

    try:
        admin_conn.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(ephemeral_db_name))
        )

        ephemeral_settings = Settings(
            app_name="FinSignalAuthDepIntegrationTest",
            environment="testing",
            database_host=str(params["host"]),
            database_port=int(params["port"]),
            database_name=ephemeral_db_name,
            database_user=str(params["user"]),
            database_password=SecretStr(str(params["password"])),
            jwt_secret_key=SecretStr("integration-test-dep-secret-key-32chars-min!"),
            access_token_expire_minutes=30,
            _env_file=None,
        )

        alembic_cfg = Config("alembic.ini")
        escaped_url = ephemeral_settings.sync_database_url.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", escaped_url)
        command.upgrade(alembic_cfg, "head")

        yield {
            "db_name": ephemeral_db_name,
            "settings": ephemeral_settings,
        }

    finally:
        try:
            admin_conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid();
                """,
                (ephemeral_db_name,),
            )
            admin_conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(ephemeral_db_name)
                )
            )
        except Exception:
            pass
        finally:
            admin_conn.close()


@pytest.fixture
async def async_session(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound to the disposable test database."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient wired to the test app with auth test routes mounted."""
    settings: Settings = disposable_db["settings"]
    app = create_app(settings)
    app.include_router(auth_test_router)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as http_client,
    ):
        yield http_client


@pytest.mark.asyncio
async def test_unauthenticated_request_fails_with_401(client: AsyncClient) -> None:
    """Verify missing Authorization header fails with HTTP 401 UNAUTHORIZED."""
    response = await client.get("/test-auth/protected")
    assert response.status_code == 401

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "credentials were not provided" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_invalid_bearer_token_fails_with_401(client: AsyncClient) -> None:
    """Verify malformed or invalid token fails with HTTP 401 UNAUTHORIZED."""
    headers = {"Authorization": "Bearer invalid.token.payload"}
    response = await client.get("/test-auth/protected", headers=headers)
    assert response.status_code == 401

    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_authenticated_active_user_succeeds(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify valid token for active user loads user and returns HTTP 200."""
    settings: Settings = disposable_db["settings"]
    repo = UserRepository()

    user = await repo.create(
        session=async_session,
        email="analyst.active@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ANALYST",
        is_active=True,
    )
    await async_session.commit()

    token = create_access_token(user_id=user.id, settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/test-auth/protected", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"id": str(user.id), "role": "ANALYST"}


@pytest.mark.asyncio
async def test_rbac_disallowed_role_fails_with_403(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify authenticated user with disallowed role fails with HTTP 403 FORBIDDEN."""
    settings: Settings = disposable_db["settings"]
    repo = UserRepository()

    user = await repo.create(
        session=async_session,
        email="analyst.disallowed@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ANALYST",
        is_active=True,
    )
    await async_session.commit()

    token = create_access_token(user_id=user.id, settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    # Endpoint requires ADMIN role
    response = await client.get("/test-auth/admin-only", headers=headers)
    assert response.status_code == 403

    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "permission" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_rbac_allowed_role_succeeds(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify user with allowed role accesses RBAC-restricted endpoint."""
    settings: Settings = disposable_db["settings"]
    repo = UserRepository()

    admin_user = await repo.create(
        session=async_session,
        email="admin.allowed@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ADMIN",
        is_active=True,
    )
    await async_session.commit()

    token = create_access_token(user_id=admin_user.id, settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/test-auth/admin-only", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"id": str(admin_user.id), "role": "ADMIN"}


@pytest.mark.asyncio
async def test_rbac_role_change_in_db_reflected_without_new_token(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify role updates in PostgreSQL are immediately reflected using the same JWT."""
    settings: Settings = disposable_db["settings"]
    repo = UserRepository()

    # User starts with ANALYST role
    user = await repo.create(
        session=async_session,
        email="promoted.analyst@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ANALYST",
        is_active=True,
    )
    await async_session.commit()

    # Issue token once
    token = create_access_token(user_id=user.id, settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Accessing admin-only as ANALYST fails with 403
    res_before = await client.get("/test-auth/admin-only", headers=headers)
    assert res_before.status_code == 403

    # Step 2: Role is promoted to ADMIN directly in PostgreSQL
    await async_session.execute(
        text("UPDATE users SET role = 'ADMIN' WHERE id = :user_id"),
        {"user_id": user.id},
    )
    await async_session.commit()

    # Step 3: Using the EXACT SAME token, the request now succeeds with 200!
    res_after = await client.get("/test-auth/admin-only", headers=headers)
    assert res_after.status_code == 200
    assert res_after.json() == {"id": str(user.id), "role": "ADMIN"}


@pytest.mark.asyncio
async def test_inactive_user_rejected_on_live_postgres(
    client: AsyncClient,
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify inactive user in database is rejected with HTTP 401."""
    settings: Settings = disposable_db["settings"]
    repo = UserRepository()

    # User deactivated in database
    user = await repo.create(
        session=async_session,
        email="deactivated.user@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ANALYST",
        is_active=False,
    )
    await async_session.commit()

    token = create_access_token(user_id=user.id, settings=settings)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/test-auth/protected", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "inactive" in data["error"]["message"].lower()
