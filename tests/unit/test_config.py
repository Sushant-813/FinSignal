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
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    monkeypatch.delenv("DATABASE_PORT", raising=False)
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("DATABASE_DB", raising=False)
    monkeypatch.delenv("DATABASE_NAME", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("DATABASE_USER", raising=False)
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
    assert settings.log_level == "INFO"
    assert settings.log_format is None
    assert settings.request_id_header == "X-Request-ID"


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


def test_settings_environment_validation() -> None:
    """Verify allowed environment profiles and rejection of invalid values."""
    for env in ("development", "testing", "production"):
        s = Settings(
            environment=env,
            database_password=SecretStr("pw"),
            jwt_secret_key=SecretStr("a" * 32),
            _env_file=None,
        )
        assert s.environment == env

    with pytest.raises(ValidationError):
        Settings(
            environment="staging",
            database_password=SecretStr("pw"),
            jwt_secret_key=SecretStr("a" * 32),
            _env_file=None,
        )


def test_settings_log_level_validation() -> None:
    """Verify log_level uppercase normalization and rejection of invalid levels."""
    s = Settings(
        log_level="debug",
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    assert s.log_level == "DEBUG"

    with pytest.raises(ValidationError):
        Settings(
            log_level="INVALID_LEVEL",
            database_password=SecretStr("pw"),
            _env_file=None,
        )


def test_settings_log_format_validation() -> None:
    """Verify log_format accepts text, json, or None."""
    s_text = Settings(
        log_format="text",
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    assert s_text.log_format == "text"

    s_json = Settings(
        log_format="json",
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    assert s_json.log_format == "json"

    with pytest.raises(ValidationError):
        Settings(
            log_format="xml",
            database_password=SecretStr("pw"),
            _env_file=None,
        )


def test_settings_jwt_defaults() -> None:
    """Verify default values and masking for JWT settings."""
    settings = Settings(
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 30
    assert "dev-insecure-jwt" not in repr(settings.jwt_secret_key)
    assert "**********" in str(settings.jwt_secret_key)


def test_settings_jwt_algorithm_restriction() -> None:
    """Verify jwt_algorithm strictly enforces HS256 and rejects other algorithms."""
    with pytest.raises(ValidationError):
        Settings(
            jwt_algorithm="RS256",
            database_password=SecretStr("pw"),
            _env_file=None,
        )

    with pytest.raises(ValidationError):
        Settings(
            jwt_algorithm="none",
            database_password=SecretStr("pw"),
            _env_file=None,
        )


def test_settings_jwt_token_expire_bounds() -> None:
    """Verify access_token_expire_minutes boundaries (1 to 1440)."""
    with pytest.raises(ValidationError):
        Settings(
            access_token_expire_minutes=0,
            database_password=SecretStr("pw"),
            _env_file=None,
        )

    with pytest.raises(ValidationError):
        Settings(
            access_token_expire_minutes=1441,
            database_password=SecretStr("pw"),
            _env_file=None,
        )

    s = Settings(
        access_token_expire_minutes=60,
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    assert s.access_token_expire_minutes == 60


def test_settings_jwt_production_requires_explicit_strong_secret() -> None:
    """Verify production rejects dev fallback and weak secrets (<32 chars)."""
    # Dev default rejected in production
    with pytest.raises(ValidationError, match="cannot use the default dev secret"):
        Settings(
            environment="production",
            database_password=SecretStr("pw"),
            _env_file=None,
        )

    # Weak secret (<32 chars) rejected in production
    with pytest.raises(ValidationError, match="at least 32 characters long"):
        Settings(
            environment="production",
            jwt_secret_key=SecretStr("short_secret_under_32_chars"),
            database_password=SecretStr("pw"),
            _env_file=None,
        )

    # Strong secret (>=32 chars) accepted in production
    strong_key = "a" * 32
    prod_settings = Settings(
        environment="production",
        jwt_secret_key=SecretStr(strong_key),
        database_password=SecretStr("pw"),
        _env_file=None,
    )
    assert prod_settings.jwt_secret_key.get_secret_value() == strong_key


def test_settings_jwt_secret_alias_support() -> None:
    """Verify secret_key alias binds to jwt_secret_key."""
    s = Settings.model_validate(
        {
            "secret_key": "custom_secret_key_for_testing_12345",
            "database_password": "pw",
        }
    )
    assert s.jwt_secret_key.get_secret_value() == "custom_secret_key_for_testing_12345"
