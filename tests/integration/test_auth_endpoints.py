"""Integration tests for Authentication API endpoints on disposable PostgreSQL database."""

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import timedelta
from typing import Any

import jwt
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.security import create_access_token
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.main import create_app
from finsignal.users.repository import UserRepository
from tests.integration.test_constraints import (
    get_admin_connection_params,
    is_live_postgres_available,
)


@pytest.fixture(scope="module")
def disposable_db() -> Generator[dict[str, Any], None, None]:
    """Provision a dedicated, disposable PostgreSQL test database for auth endpoint integration tests."""
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
            app_name="FinSignalAuthEndpointsIntegrationTest",
            environment="testing",
            database_host=str(params["host"]),
            database_port=int(params["port"]),
            database_name=ephemeral_db_name,
            database_user=str(params["user"]),
            database_password=SecretStr(str(params["password"])),
            jwt_secret_key=SecretStr("integration-test-secret-key-32chars-min!"),
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
        finally:
            admin_conn.close()


@pytest.fixture(autouse=True)
def clean_users_table(disposable_db: dict[str, Any]) -> Generator[None, None, None]:
    """Truncate the users table before each test run to ensure strict data isolation."""
    yield
    params = get_admin_connection_params()
    conn = psycopg.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname=disposable_db["db_name"],
        autocommit=True,
    )
    try:
        conn.execute("TRUNCATE TABLE users CASCADE;")
    finally:
        conn.close()


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
    """Provide an AsyncClient bound to the full application with all routes mounted."""
    settings: Settings = disposable_db["settings"]
    app = create_app(settings)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as http_client,
    ):
        yield http_client


# ==============================================================================
# 1. Registration Endpoints (/api/v1/auth/register)
# ==============================================================================


@pytest.mark.asyncio
async def test_register_success(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    """Verify POST /api/v1/auth/register creates user, assigns ANALYST, and returns HTTP 201."""
    payload = {
        "email": "analyst.new@finsignal.io",
        "password": "strong-password-123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["email"] == "analyst.new@finsignal.io"
    assert data["role"] == "ANALYST"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    # Verify user exists in PostgreSQL with ANALYST role
    repo = UserRepository()
    user = await repo.get_by_email(async_session, "analyst.new@finsignal.io")
    assert user is not None
    assert user.role == "ANALYST"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_register_rejects_client_supplied_role(client: AsyncClient) -> None:
    """Verify registration request rejects client-supplied role with HTTP 422."""
    payload = {
        "email": "hacker@finsignal.io",
        "password": "strong-password-123",
        "role": "ADMIN",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "extra_fields" in data["error"]["details"]


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client: AsyncClient) -> None:
    """Verify registering an existing email returns HTTP 409 STATE_CONFLICT envelope."""
    payload = {
        "email": "duplicate@finsignal.io",
        "password": "strong-password-123",
    }
    first_res = await client.post("/api/v1/auth/register", json=payload)
    assert first_res.status_code == 201

    dup_res = await client.post("/api/v1/auth/register", json=payload)
    assert dup_res.status_code == 409

    data = dup_res.json()
    assert data["error"]["code"] == "STATE_CONFLICT"
    assert "already exists" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_validation_failures(client: AsyncClient) -> None:
    """Verify invalid payloads (short password, invalid email) return HTTP 422."""
    # Short password (< 12 chars)
    res_short = await client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short"},
    )
    assert res_short.status_code == 422
    assert res_short.json()["error"]["code"] == "VALIDATION_ERROR"

    # Malformed email
    res_email = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "secure-password-123"},
    )
    assert res_email.status_code == 422
    assert res_email.json()["error"]["code"] == "VALIDATION_ERROR"


# ==============================================================================
# 2. Login Endpoints (/api/v1/auth/login)
# ==============================================================================


@pytest.mark.asyncio
async def test_login_success(
    client: AsyncClient,
    disposable_db: dict[str, Any],
) -> None:
    """Verify POST /api/v1/auth/login returns HTTP 200 with Bearer token and expiry."""
    # First register user
    reg_payload = {
        "email": "login.test@finsignal.io",
        "password": "secure-password-123",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    # Login
    login_payload = {
        "email": "login.test@finsignal.io",
        "password": "secure-password-123",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200

    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] == 30 * 60  # 30 minutes in seconds


@pytest.mark.asyncio
async def test_login_invalid_password_returns_401(client: AsyncClient) -> None:
    """Verify incorrect password returns HTTP 401 UNAUTHORIZED envelope."""
    reg_payload = {
        "email": "badpass@finsignal.io",
        "password": "correct-password-123",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "badpass@finsignal.io", "password": "wrong-password-999"},
    )
    assert login_res.status_code == 401
    assert login_res.json()["error"]["code"] == "UNAUTHORIZED"
    assert "invalid email or password" in login_res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    """Verify non-existent user returns identical HTTP 401 UNAUTHORIZED envelope (mitigating enumeration)."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@finsignal.io", "password": "some-password-123"},
    )
    assert login_res.status_code == 401
    assert login_res.json()["error"]["code"] == "UNAUTHORIZED"
    assert "invalid email or password" in login_res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify inactive user cannot log in even with valid password."""
    reg_payload = {
        "email": "inactive.login@finsignal.io",
        "password": "secure-password-123",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Deactivate user in PostgreSQL
    await async_session.execute(
        text("UPDATE users SET is_active = false WHERE email = :email"),
        {"email": "inactive.login@finsignal.io"},
    )
    await async_session.commit()

    login_res = await client.post(
        "/api/v1/auth/login",
        json=reg_payload,
    )
    assert login_res.status_code == 401
    assert login_res.json()["error"]["code"] == "UNAUTHORIZED"
    assert "inactive" in login_res.json()["error"]["message"].lower()


# ==============================================================================
# 3. Current User Endpoint (/api/v1/auth/me)
# ==============================================================================


@pytest.mark.asyncio
async def test_me_authenticated_returns_public_profile(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify GET /api/v1/auth/me returns current user identity with database-authoritative role."""
    # Register and login
    creds = {"email": "me.analyst@finsignal.io", "password": "secure-password-123"}
    await client.post("/api/v1/auth/register", json=creds)
    login_res = await client.post("/api/v1/auth/login", json=creds)
    token = login_res.json()["access_token"]

    # Request /me
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == "me.analyst@finsignal.io"
    assert data["role"] == "ANALYST"
    assert data["is_active"] is True
    assert "created_at" in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_me_rejects_unauthenticated_and_invalid_tokens(
    client: AsyncClient,
    disposable_db: dict[str, Any],
) -> None:
    """Verify GET /api/v1/auth/me rejects missing, invalid, and expired tokens with HTTP 401."""
    settings: Settings = disposable_db["settings"]

    # 1. Missing header
    res_missing = await client.get("/api/v1/auth/me")
    assert res_missing.status_code == 401
    assert res_missing.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Invalid token
    res_invalid = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert res_invalid.status_code == 401
    assert res_invalid.json()["error"]["code"] == "UNAUTHORIZED"

    # 3. Expired token
    expired_token = create_access_token(
        user_id=uuid.uuid4(),
        settings=settings,
        expires_delta=timedelta(minutes=-10),
    )
    res_expired = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401
    assert res_expired.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_me_reflects_database_role_changes(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify /me reflects database role change without issuing a new token."""
    creds = {"email": "promote.me@finsignal.io", "password": "secure-password-123"}
    await client.post("/api/v1/auth/register", json=creds)
    login_res = await client.post("/api/v1/auth/login", json=creds)
    token = login_res.json()["access_token"]

    # Before role update: ANALYST
    res_before = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_before.status_code == 200
    assert res_before.json()["role"] == "ANALYST"

    # Promote in DB to INVESTIGATOR
    await async_session.execute(
        text("UPDATE users SET role = 'INVESTIGATOR' WHERE email = :email"),
        {"email": "promote.me@finsignal.io"},
    )
    await async_session.commit()

    # After role update with the SAME token: reflects INVESTIGATOR
    res_after = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_after.status_code == 200
    assert res_after.json()["role"] == "INVESTIGATOR"


# ==============================================================================
# 4. Logout Endpoint (/api/v1/auth/logout)
# ==============================================================================


@pytest.mark.asyncio
async def test_logout_stateless_contract(client: AsyncClient) -> None:
    """Verify POST /api/v1/auth/logout acknowledges logout statelessly."""
    # Register and login to obtain token
    creds = {"email": "logout.user@finsignal.io", "password": "secure-password-123"}
    await client.post("/api/v1/auth/register", json=creds)
    login_res = await client.post("/api/v1/auth/login", json=creds)
    token = login_res.json()["access_token"]

    # Call logout with authorization header
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json() == {"message": "Successfully logged out."}

    # Under stateless design without server revocation, the token remains valid until expiration
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "logout.user@finsignal.io"


@pytest.mark.asyncio
async def test_logout_missing_credentials_returns_401(client: AsyncClient) -> None:
    """Verify POST /api/v1/auth/logout rejects requests without credentials with HTTP 401."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "credentials were not provided" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_logout_invalid_and_expired_tokens_return_401(
    client: AsyncClient,
    disposable_db: dict[str, Any],
) -> None:
    """Verify POST /api/v1/auth/logout rejects invalid and expired tokens with HTTP 401."""
    settings: Settings = disposable_db["settings"]

    # 1. Invalid token
    res_invalid = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer malformed.invalid.token"},
    )
    assert res_invalid.status_code == 401
    assert res_invalid.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Expired token
    expired_token = create_access_token(
        user_id=uuid.uuid4(),
        settings=settings,
        expires_delta=timedelta(minutes=-15),
    )
    res_expired = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401
    assert res_expired.json()["error"]["code"] == "UNAUTHORIZED"


# ==============================================================================
# 5. Security Invariants and Regression Coverage
# ==============================================================================


@pytest.mark.asyncio
async def test_concurrent_duplicate_registration_handled_cleanly(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify concurrent registration requests for the same email resolve to exactly 1 created user and 1 409 conflict."""
    payload = {
        "email": "concurrent.analyst@finsignal.io",
        "password": "secure-password-123",
    }
    # Execute two simultaneous registration requests against PostgreSQL
    res1, res2 = await asyncio.gather(
        client.post("/api/v1/auth/register", json=payload),
        client.post("/api/v1/auth/register", json=payload),
    )

    statuses = sorted([res1.status_code, res2.status_code])
    assert statuses == [201, 409]

    # Verify conflict error envelope format
    conflict_res = res1 if res1.status_code == 409 else res2
    conflict_data = conflict_res.json()
    assert conflict_data["error"]["code"] == "STATE_CONFLICT"
    assert "already exists" in conflict_data["error"]["message"].lower()

    # Verify only 1 user exists in PostgreSQL
    count_res = await async_session.execute(
        text("SELECT count(*) FROM users WHERE email = :email"),
        {"email": "concurrent.analyst@finsignal.io"},
    )
    assert count_res.scalar() == 1


@pytest.mark.asyncio
async def test_me_rejects_inactive_and_deleted_users_on_live_postgres(
    client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    """Verify /me rejects authenticated users who have been deactivated or deleted in PostgreSQL."""
    creds = {"email": "lifecycle.user@finsignal.io", "password": "secure-password-123"}
    await client.post("/api/v1/auth/register", json=creds)
    login_res = await client.post("/api/v1/auth/login", json=creds)
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify initially accessible
    res_ok = await client.get("/api/v1/auth/me", headers=headers)
    assert res_ok.status_code == 200

    # 1. Deactivate in DB -> 401 UNAUTHORIZED
    await async_session.execute(
        text("UPDATE users SET is_active = false WHERE email = :email"),
        {"email": "lifecycle.user@finsignal.io"},
    )
    await async_session.commit()

    res_inactive = await client.get("/api/v1/auth/me", headers=headers)
    assert res_inactive.status_code == 401
    assert res_inactive.json()["error"]["code"] == "UNAUTHORIZED"
    assert "inactive" in res_inactive.json()["error"]["message"].lower()

    # 2. Delete from DB -> 401 UNAUTHORIZED
    await async_session.execute(
        text("DELETE FROM users WHERE email = :email"),
        {"email": "lifecycle.user@finsignal.io"},
    )
    await async_session.commit()

    res_deleted = await client.get("/api/v1/auth/me", headers=headers)
    assert res_deleted.status_code == 401
    assert res_deleted.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_me_rejects_tampered_and_wrong_algorithm_tokens(
    client: AsyncClient,
    disposable_db: dict[str, Any],
) -> None:
    """Verify /me rejects algorithm substitution ('none', wrong key) and signature tampering with HTTP 401."""
    user_id = str(uuid.uuid4())

    # 1. Algorithm 'none' token
    none_token = jwt.encode(
        {"sub": user_id, "iat": 1700000000, "exp": 1800000000},
        key="",
        algorithm="none",
    )
    res_none = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {none_token}"},
    )
    assert res_none.status_code == 401
    assert res_none.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Token signed with wrong secret key
    wrong_key_token = jwt.encode(
        {"sub": user_id, "iat": 1700000000, "exp": 1800000000},
        key="completely-wrong-secret-key-32chars!",
        algorithm="HS256",
    )
    res_wrong_key = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {wrong_key_token}"},
    )
    assert res_wrong_key.status_code == 401
    assert res_wrong_key.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_endpoints_preserve_request_id_correlation(
    client: AsyncClient,
) -> None:
    """Verify auth endpoints preserve client-supplied X-Request-ID across success and error responses."""
    custom_request_id = "test-corr-id-12345"
    headers = {"X-Request-ID": custom_request_id}

    # Success case: register
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "corr.user@finsignal.io", "password": "secure-password-123"},
        headers=headers,
    )
    assert reg_res.status_code == 201
    assert reg_res.headers.get("x-request-id") == custom_request_id

    # Error case: duplicate conflict
    dup_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "corr.user@finsignal.io", "password": "secure-password-123"},
        headers=headers,
    )
    assert dup_res.status_code == 409
    assert dup_res.headers.get("x-request-id") == custom_request_id
    assert dup_res.json()["error"]["request_id"] == custom_request_id

    # Error case: validation error
    val_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "short"},
        headers=headers,
    )
    assert val_res.status_code == 422
    assert val_res.headers.get("x-request-id") == custom_request_id
    assert val_res.json()["error"]["request_id"] == custom_request_id

    # Error case: 401 unauthorized on /me
    auth_res = await client.get(
        "/api/v1/auth/me",
        headers={"X-Request-ID": custom_request_id},
    )
    assert auth_res.status_code == 401
    assert auth_res.headers.get("x-request-id") == custom_request_id
    assert auth_res.json()["error"]["request_id"] == custom_request_id
