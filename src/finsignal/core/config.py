"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """FinSignal application settings."""

    app_name: str = "FinSignal"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # Logging settings
    log_level: str = "INFO"
    log_format: Literal["text", "json"] | None = None

    # Request correlation
    request_id_header: str = "X-Request-ID"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level string."""
        normalized = v.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            msg = f"Invalid log level: '{v}'. Must be one of {allowed}"
            raise ValueError(msg)
        return normalized

    # Database settings with dual alias support (POSTGRES_* and DATABASE_*)
    database_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("database_host", "postgres_host"),
    )
    database_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("database_port", "postgres_port"),
    )
    database_name: str = Field(
        default="finsignal_dev",
        validation_alias=AliasChoices("database_name", "postgres_db", "database_db"),
    )
    database_user: str = Field(
        default="postgres",
        validation_alias=AliasChoices("database_user", "postgres_user"),
    )
    database_password: SecretStr = Field(
        ...,
        validation_alias=AliasChoices("database_password", "postgres_password"),
        description="PostgreSQL password (strictly required, never logged)",
    )

    # JWT authentication settings
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-insecure-jwt-secret-key-for-testing-only-32chars"),
        validation_alias=AliasChoices("jwt_secret_key", "secret_key"),
        description="Cryptographic secret key for signing JWT tokens",
    )
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Access token validity window in minutes",
    )

    cors_origins: list[str] = ["http://localhost:3000"]

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        """Validate JWT signing secret strength and prevent hardcoded fallbacks in production."""
        secret = self.jwt_secret_key.get_secret_value()
        dev_default = "dev-insecure-jwt-secret-key-for-testing-only-32chars"
        if self.environment == "production":
            if secret == dev_default:
                msg = (
                    "In production, 'jwt_secret_key' must be explicitly configured "
                    "and cannot use the default dev secret."
                )
                raise ValueError(msg)
            if len(secret) < 32:
                msg = "In production, 'jwt_secret_key' must be at least 32 characters long."
                raise ValueError(msg)
        elif (
            self.environment == "development"
            and secret != dev_default
            and len(secret) < 32
        ):
            msg = "'jwt_secret_key' must be at least 32 characters long."
            raise ValueError(msg)
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """Construct the asyncpg connection URL."""
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.database_user,
            password=self.database_password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(hide_password=False)

    @property
    def sync_database_url(self) -> str:
        """Construct the psycopg connection URL for Alembic migrations."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.database_user,
            password=self.database_password.get_secret_value(),
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        ).render_as_string(hide_password=False)

    @property
    def sanitized_database_target(self) -> str:
        """Return safe host/database target string without credentials for logging."""
        return f"{self.database_host}:{self.database_port}/{self.database_name}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
