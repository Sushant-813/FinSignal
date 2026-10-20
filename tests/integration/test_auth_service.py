"""Integration tests for AuthService on disposable PostgreSQL test database."""

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from finsignal.auth.security import decode_access_token
from finsignal.auth.service import AuthService
from finsignal.common.exceptions import AuthenticationError, ConflictError
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.users.repository import UserRepository
from tests.integration.test_constraints import (
    get_admin_connection_params,
    is_live_postgres_available,
)


@pytest.fixture(scope="module")
def disposable_db() -> Generator[dict[str, Any], None, None]:
    """Provision a dedicated, disposable PostgreSQL test database for auth service integration tests."""
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
            app_name="FinSignalAuthServiceIntegrationTest",
            environment="testing",
            database_host=str(params["host"]),
            database_port=int(params["port"]),
            database_name=ephemeral_db_name,
            database_user=str(params["user"]),
            database_password=SecretStr(str(params["password"])),
            jwt_secret_key=SecretStr("integration-test-secret-key-32chars-min!"),
            access_token_expire_minutes=20,
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


@pytest.mark.asyncio
async def test_service_registration_and_login_full_cycle(
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify registration creates user in PostgreSQL and subsequent login authenticates."""
    settings: Settings = disposable_db["settings"]
    auth_service = AuthService(settings=settings)

    # 1. Register new user
    reg_req = RegisterRequest(
        email="lead.analyst@example.com",
        password="StrongPassword123!",
    )
    user_res = await auth_service.register(async_session, reg_req)

    assert isinstance(user_res, UserResponse)
    assert user_res.email == "lead.analyst@example.com"
    assert user_res.role == "ANALYST"
    assert user_res.is_active is True

    # 2. Login with newly registered user
    login_req = LoginRequest(
        email="LEAD.ANALYST@example.com",  # mixed case should match normalized
        password="StrongPassword123!",
    )
    token_res = await auth_service.login(async_session, login_req)

    assert isinstance(token_res, TokenResponse)
    assert token_res.token_type == "bearer"
    assert token_res.expires_in == 20 * 60  # 1200 seconds

    # 3. Verify access token payload
    payload = decode_access_token(token_res.access_token, settings)
    assert payload["sub"] == str(user_res.id)


@pytest.mark.asyncio
async def test_service_duplicate_registration_leaves_session_recoverable(
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify duplicate registration fails with ConflictError and leaves session in recoverable state."""
    settings: Settings = disposable_db["settings"]
    auth_service = AuthService(settings=settings)

    # Pre-register user
    await auth_service.register(
        async_session,
        RegisterRequest(
            email="existing.investigator@example.com",
            password="StrongPassword123!",
        ),
    )

    # Duplicate registration attempt
    with pytest.raises(ConflictError) as exc_info:
        await auth_service.register(
            async_session,
            RegisterRequest(
                email="EXISTING.INVESTIGATOR@EXAMPLE.COM",
                password="AnotherPassword123!",
            ),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "STATE_CONFLICT"

    # Verify session is still healthy and recoverable (not aborted)
    result = await async_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_service_duplicate_registration_real_db_constraint_race(
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify real PostgreSQL uniqueness constraint violation triggers rollback and ConflictError.

    Simulates a concurrent race condition where the preliminary get_by_email check
    misses an in-flight insert, forcing PostgreSQL's uq_users_email constraint
    to raise a real psycopg UniqueViolation during flush/commit.
    """
    settings: Settings = disposable_db["settings"]
    auth_service = AuthService(settings=settings)

    # 1. Pre-register and commit a legitimate user
    await auth_service.register(
        async_session,
        RegisterRequest(
            email="race.condition@example.com",
            password="InitialPassword123!",
        ),
    )

    # 2. Bypass preliminary lookup to force the real repository and PostgreSQL execution
    with patch.object(
        auth_service.user_repo, "get_by_email", new_callable=AsyncMock
    ) as mock_lookup:
        mock_lookup.return_value = None

        # 3. Attempt second registration with same email (uppercase) against live PostgreSQL
        with pytest.raises(ConflictError) as exc_info:
            await auth_service.register(
                async_session,
                RegisterRequest(
                    email="RACE.CONDITION@EXAMPLE.COM",
                    password="SecondPassword123!",
                ),
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "STATE_CONFLICT"
        assert (
            exc_info.value.message == "A user with this email address already exists."
        )

    # 4. Verify rollback cleared PostgreSQL's 25P02 aborted state and restored session
    result = await async_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_service_unrelated_constraint_on_postgres_not_masked(
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify non-email constraint violations on real PostgreSQL are re-raised and not masked as duplicate email."""
    settings: Settings = disposable_db["settings"]
    auth_service = AuthService(settings=settings)

    # Force user_repo.create to violate PostgreSQL's chk_users_role constraint
    real_create = auth_service.user_repo.create

    async def invalid_role_create(session, email, password_hash, role, is_active=True):
        # Substitute an invalid role to trigger chk_users_role on live PostgreSQL
        return await real_create(
            session=session,
            email=email,
            password_hash=password_hash,
            role="INVALID_SUPERUSER_ROLE",
            is_active=is_active,
        )

    with patch.object(
        auth_service.user_repo, "create", side_effect=invalid_role_create
    ):
        # Must re-raise IntegrityError, NOT mask it as ConflictError
        with pytest.raises(IntegrityError) as exc_info:
            await auth_service.register(
                async_session,
                RegisterRequest(
                    email="check.test@example.com",
                    password="ValidPassword123!",
                ),
            )
        # Verify that the underlying error was indeed a CheckViolation for chk_users_role
        orig_err = getattr(exc_info.value, "orig", None)
        cause = getattr(orig_err, "__cause__", None)
        diag = getattr(orig_err, "diag", None)
        constraint = (
            getattr(diag, "constraint_name", None)
            or getattr(cause, "constraint_name", None)
            or str(exc_info.value)
        )
        assert "chk_users_role" in constraint

    # Verify session was rolled back and is healthy
    result = await async_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_service_login_failures_on_postgres(
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify wrong password and unknown user raise indistinguishable AuthenticationError on real DB."""
    settings: Settings = disposable_db["settings"]
    auth_service = AuthService(settings=settings)

    # Register legitimate user
    await auth_service.register(
        async_session,
        RegisterRequest(
            email="legit.user@example.com",
            password="CorrectPassword123!",
        ),
    )

    # 1. Bad password
    with pytest.raises(AuthenticationError) as bad_pw_exc:
        await auth_service.login(
            async_session,
            LoginRequest(
                email="legit.user@example.com",
                password="WrongPassword999!",
            ),
        )

    # 2. Unknown user
    with pytest.raises(AuthenticationError) as unknown_exc:
        await auth_service.login(
            async_session,
            LoginRequest(
                email="unknown.user@example.com",
                password="AnyPassword123!",
            ),
        )

    # Both errors must be identical
    assert bad_pw_exc.value.status_code == unknown_exc.value.status_code == 401
    assert bad_pw_exc.value.code == unknown_exc.value.code == "UNAUTHORIZED"
    assert (
        bad_pw_exc.value.message
        == unknown_exc.value.message
        == "Invalid email or password."
    )


@pytest.mark.asyncio
async def test_service_login_inactive_user_on_postgres(
    async_session: AsyncSession,
    disposable_db: dict[str, Any],
) -> None:
    """Verify inactive account is rejected on live PostgreSQL."""
    settings: Settings = disposable_db["settings"]
    auth_service = AuthService(settings=settings)
    repo = UserRepository()

    # Create inactive user directly in DB
    await repo.create(
        session=async_session,
        email="inactive.analyst@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ANALYST",
        is_active=False,
    )
    await async_session.commit()

    with pytest.raises(AuthenticationError) as exc_info:
        await auth_service.login(
            async_session,
            LoginRequest(
                email="inactive.analyst@example.com",
                password="SomePassword123!",
            ),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
