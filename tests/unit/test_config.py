"""Unit tests for configuration management."""

import pytest
from pydantic import SecretStr, ValidationError

from finsignal.core.config import Settings


def test_settings_requires_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that omitting database_password raises a validation error."""
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_loads_with_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify settings initialization and defaults when password is provided."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    settings = Settings(
        database_password=SecretStr("supersecret"),
        _env_file=None,
    )
    assert settings.app_name == "FinSignal"
    assert settings.environment == "development"
    assert settings.database_host == "localhost"
    assert settings.database_port == 5432
    assert settings.database_name == "finsignal_dev"
    assert settings.database_user == "postgres"
    assert settings.database_password.get_secret_value() == "supersecret"


def test_settings_masks_password() -> None:
    """Verify that SecretStr masks the secret in string representation."""
    settings = Settings(
        database_password=SecretStr("sensitive123"),
        _env_file=None,
    )
    assert "sensitive123" not in str(settings.database_password)
    assert "sensitive123" not in repr(settings.database_password)
    assert "**********" in str(settings.database_password)


def test_settings_url_generation() -> None:
    """Verify correct driver URL schemes for runtime (asyncpg) and migrations (psycopg)."""
    settings = Settings(
        database_host="127.0.0.1",
        database_port=5433,
        database_name="custom_db",
        database_user="custom_user",
        database_password=SecretStr("pass456"),
        _env_file=None,
    )
    assert (
        settings.async_database_url
        == "postgresql+asyncpg://custom_user:pass456@127.0.0.1:5433/custom_db"
    )
    assert (
        settings.sync_database_url
        == "postgresql+psycopg://custom_user:pass456@127.0.0.1:5433/custom_db"
    )
    assert settings.sanitized_database_target == "127.0.0.1:5433/custom_db"
    assert "pass456" not in settings.sanitized_database_target


def test_settings_dual_alias_support() -> None:
    """Verify that both POSTGRES_* and DATABASE_* alias styles bind correctly."""
    settings_pg = Settings.model_validate(
        {"postgres_host": "pghost", "postgres_password": "pgpw"},
    )
    assert settings_pg.database_host == "pghost"
    assert settings_pg.database_password.get_secret_value() == "pgpw"

    settings_db = Settings.model_validate(
        {"database_host": "dbhost", "database_password": "dbpw"},
    )
    assert settings_db.database_host == "dbhost"
    assert settings_db.database_password.get_secret_value() == "dbpw"


def test_settings_special_characters_in_password() -> None:
    """Verify that passwords with URL-special characters (@, :, /, ?, #, %) are preserved correctly."""
    from sqlalchemy import make_url

    special_pw = "p@ss:w/o?r#d%123"
    settings = Settings(
        database_host="localhost",
        database_port=5432,
        database_name="test_db",
        database_user="postgres",
        database_password=SecretStr(special_pw),
        _env_file=None,
    )

    async_url = make_url(settings.async_database_url)
    assert async_url.drivername == "postgresql+asyncpg"
    assert async_url.username == "postgres"
    assert async_url.password == special_pw
    assert async_url.host == "localhost"
    assert async_url.port == 5432
    assert async_url.database == "test_db"

    sync_url = make_url(settings.sync_database_url)
    assert sync_url.drivername == "postgresql+psycopg"
    assert sync_url.username == "postgres"
    assert sync_url.password == special_pw
    assert sync_url.host == "localhost"
    assert sync_url.port == 5432
    assert sync_url.database == "test_db"
