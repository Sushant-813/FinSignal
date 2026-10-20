"""Integration tests for UserRepository and User database constraints on disposable PostgreSQL."""

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.users.repository import UserRepository
from tests.integration.test_constraints import (
    get_admin_connection_params,
    is_live_postgres_available,
)


@pytest.fixture(scope="module")
def disposable_db() -> Generator[dict[str, Any], None, None]:
    """Provision a dedicated, disposable PostgreSQL test database for user repository tests."""
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
            app_name="FinSignalUserRepoTest",
            environment="testing",
            database_host=str(params["host"]),
            database_port=int(params["port"]),
            database_name=ephemeral_db_name,
            database_user=str(params["user"]),
            database_password=SecretStr(str(params["password"])),
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
async def test_create_and_get_by_id(async_session: AsyncSession) -> None:
    """Verify creating a user populates database defaults and get_by_id retrieves it."""
    repo = UserRepository()
    user = await repo.create(
        session=async_session,
        email="analyst.alpha@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="ANALYST",
    )

    assert user.id is not None
    assert isinstance(user.id, uuid.UUID)
    assert user.email == "analyst.alpha@example.com"
    assert user.role == "ANALYST"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None

    # Retrieve by ID
    retrieved = await repo.get_by_id(async_session, user.id)
    assert retrieved is not None
    assert retrieved.id == user.id
    assert retrieved.email == "analyst.alpha@example.com"


@pytest.mark.asyncio
async def test_get_by_email_normalized(async_session: AsyncSession) -> None:
    """Verify lookup by email matches case-insensitively with untrimmed whitespace."""
    repo = UserRepository()
    user = await repo.create(
        session=async_session,
        email="Investigator.Case@FinSignal.IO",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="INVESTIGATOR",
    )
    assert user.email == "investigator.case@finsignal.io"

    # Query with leading/trailing spaces and alternating case
    found = await repo.get_by_email(
        async_session, "   INVESTIGATOR.CASE@FINSIGNAL.IO   "
    )
    assert found is not None
    assert found.id == user.id
    assert found.email == "investigator.case@finsignal.io"

    # Non-existent email returns None
    missing = await repo.get_by_email(async_session, "nonexistent@example.com")
    assert missing is None


@pytest.mark.asyncio
async def test_duplicate_email_enforces_uniqueness(async_session: AsyncSession) -> None:
    """Verify duplicate email insertion triggers database IntegrityError."""
    repo = UserRepository()
    await repo.create(
        session=async_session,
        email="unique.user@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$hash1",
        role="ANALYST",
    )

    # Attempting to create another user with identical or differently-cased email
    with pytest.raises(IntegrityError, match="uq_users_email|ix_users_email"):
        await repo.create(
            session=async_session,
            email="UNIQUE.USER@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$hash2",
            role="ANALYST",
        )
    await async_session.rollback()


@pytest.mark.asyncio
async def test_role_check_constraint(async_session: AsyncSession) -> None:
    """Verify chk_users_role allows valid roles and rejects invalid roles."""
    repo = UserRepository()

    # Valid roles: ADMIN, ANALYST, INVESTIGATOR
    for valid_role in ["ADMIN", "ANALYST", "INVESTIGATOR"]:
        user = await repo.create(
            session=async_session,
            email=f"{valid_role.lower()}@domain.com",
            password_hash="hash",
            role=valid_role,
        )
        assert user.role == valid_role

    # Invalid role must fail PostgreSQL check constraint chk_users_role
    with pytest.raises(IntegrityError, match="chk_users_role"):
        await repo.create(
            session=async_session,
            email="invalid_role@domain.com",
            password_hash="hash",
            role="SUPERUSER",
        )
    await async_session.rollback()


@pytest.mark.asyncio
async def test_transaction_ownership_remains_outside_repository(
    disposable_db: dict[str, Any],
) -> None:
    """Verify repository does not commit transactions; rollback discards changes."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    repo = UserRepository()

    user_id: uuid.UUID
    # Session 1: create user, then explicitly rollback
    async with session_maker() as session1:
        user = await repo.create(
            session=session1,
            email="rollback_user@example.com",
            password_hash="hash",
            role="ANALYST",
        )
        user_id = user.id
        await session1.rollback()

    # Session 2: verify user was NOT persisted to DB
    async with session_maker() as session2:
        found = await repo.get_by_id(session2, user_id)
        assert found is None

    # Session 3: create user and explicitly commit
    async with session_maker() as session3:
        user = await repo.create(
            session=session3,
            email="committed_user@example.com",
            password_hash="hash",
            role="ANALYST",
        )
        user_id = user.id
        await session3.commit()

    # Session 4: verify user WAS persisted to DB
    async with session_maker() as session4:
        found = await repo.get_by_id(session4, user_id)
        assert found is not None
        assert found.email == "committed_user@example.com"

    await engine.dispose()
