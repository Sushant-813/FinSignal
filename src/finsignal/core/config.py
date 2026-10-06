"""Application configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """FinSignal application settings."""

    app_name: str = "FinSignal"
    environment: str = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

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

    cors_origins: list[str] = ["http://localhost:3000"]

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
