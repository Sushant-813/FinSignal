"""Shared pytest fixtures and utilities for integration tests."""

import os
import uuid
from collections.abc import Generator
from typing import Any

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic import SecretStr

from finsignal.core.config import Settings

_PROVISIONED_DISPOSABLE_DATABASES: set[str] = set()


def get_admin_connection_params() -> dict[str, str | int]:
    """Return administrative PostgreSQL connection parameters from settings or environment."""
    from dotenv import dotenv_values

    env_vals = dotenv_values(".env") if os.path.exists(".env") else {}
    host = (
        os.environ.get("POSTGRES_HOST") or env_vals.get("POSTGRES_HOST") or "localhost"
    )
    port = int(os.environ.get("POSTGRES_PORT") or env_vals.get("POSTGRES_PORT") or 5432)
    user = (
        os.environ.get("POSTGRES_USER") or env_vals.get("POSTGRES_USER") or "postgres"
    )

    dotenv_pw = env_vals.get("POSTGRES_PASSWORD")
    env_override_pw = os.environ.get("POSTGRES_PASSWORD") or os.environ.get(
        "DATABASE_PASSWORD"
    )
    if env_override_pw and env_override_pw != "test_password":
        pw = env_override_pw
    elif dotenv_pw:
        pw = dotenv_pw
    else:
        pw = "test_password"

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": pw,
    }


def is_live_postgres_available() -> bool:
    """Check if PostgreSQL server is reachable with admin credentials."""
    params = get_admin_connection_params()
    try:
        conn = psycopg.connect(
            host=params["host"],
            port=params["port"],
            user=params["user"],
            password=params["password"],
            dbname="postgres",
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def disposable_db() -> Generator[dict[str, Any], None, None]:
    """Provision a dedicated, disposable PostgreSQL test database.

    Enforces strict safety preconditions:
    1. Verifies database name has disposable prefix 'finsignal_test_ephem_'.
    2. Verifies environment is 'testing'.
    3. Runs Alembic migrations to head.
    4. Drops the ephemeral database completely on teardown.
    """
    if not is_live_postgres_available():
        pytest.skip("PostgreSQL is not reachable with configured credentials.")

    active_env = os.environ.get("ENVIRONMENT", "")
    if active_env != "testing":
        raise RuntimeError(
            f"Safety abort: Refusing to create disposable test DB in non-testing environment: {active_env!r}"
        )

    params = get_admin_connection_params()
    ephemeral_db_name = f"finsignal_test_ephem_{uuid.uuid4().hex[:8]}"

    # Precondition assertion
    assert ephemeral_db_name.startswith("finsignal_test_ephem_")
    _PROVISIONED_DISPOSABLE_DATABASES.add(ephemeral_db_name)

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
            app_name="FinSignalDisposableTest",
            environment="testing",
            database_host=str(params["host"]),
            database_port=int(params["port"]),
            database_name=ephemeral_db_name,
            database_user=str(params["user"]),
            database_password=SecretStr(str(params["password"])),
            _env_file=None,
        )

        # Run Alembic migrations on the disposable database
        alembic_cfg = Config("alembic.ini")
        escaped_url = ephemeral_settings.sync_database_url.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", escaped_url)
        command.upgrade(alembic_cfg, "head")

        yield {
            "db_name": ephemeral_db_name,
            "settings": ephemeral_settings,
            "sync_url": ephemeral_settings.sync_database_url,
            "alembic_cfg": alembic_cfg,
        }

    finally:
        _PROVISIONED_DISPOSABLE_DATABASES.discard(ephemeral_db_name)
        # Terminate any remaining client connections to allow drop
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
