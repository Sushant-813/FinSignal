"""Application configuration management using Pydantic Settings."""

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from sqlalchemy import URL


class _FinSignalEnvSettingsSource(EnvSettingsSource):
    """Custom environment settings source handling comma-separated lists and host collision isolation."""

    def _load_env_vars(self) -> Mapping[str, str | None]:
        env_vars = dict(super()._load_env_vars())
        # Strip generic 'debug' from host OS environment to prevent toolchain collisions.
        # Unrelated host tools often set DEBUG=release, DEBUG=debug, DEBUG=*, etc.
        # OS environment must explicitly set FINSIGNAL_DEBUG or APP_DEBUG.
        for key in list(env_vars.keys()):
            if key.lower() == "debug":
                del env_vars[key]
        return env_vars

    def decode_complex_value(
        self, field_name: str, field: FieldInfo, value: Any
    ) -> Any:
        try:
            return super().decode_complex_value(field_name, field, value)
        except Exception:
            if isinstance(value, str):
                return [x.strip() for x in value.split(",") if x.strip()]
            raise


class _FinSignalDotEnvSettingsSource(DotEnvSettingsSource):
    """Custom dotenv settings source handling comma-separated lists."""

    def decode_complex_value(
        self, field_name: str, field: FieldInfo, value: Any
    ) -> Any:
        try:
            return super().decode_complex_value(field_name, field, value)
        except Exception:
            if isinstance(value, str):
                return [x.strip() for x in value.split(",") if x.strip()]
            raise


class Settings(BaseSettings):
    """FinSignal application settings."""

    app_name: str = Field(
        default="FinSignal",
        validation_alias=AliasChoices("finsignal_app_name", "app_name"),
    )
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("finsignal_environment", "environment", "env"),
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("finsignal_debug", "app_debug", "debug"),
    )
    host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("finsignal_host", "host"),
    )
    port: int = Field(
        default=8000,
        validation_alias=AliasChoices("finsignal_port", "port"),
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("finsignal_log_level", "log_level"),
    )
    log_format: Literal["text", "json"] | None = Field(
        default=None,
        validation_alias=AliasChoices("finsignal_log_format", "log_format"),
    )

    # Request correlation
    request_id_header: str = Field(
        default="X-Request-ID",
        validation_alias=AliasChoices(
            "finsignal_request_id_header", "request_id_header"
        ),
    )

    # Machine Learning & Model Artifacts
    model_artifacts_dir: Path = Field(
        default=Path("artifacts/models"),
        description="Server-controlled directory for serialized ML model artifacts",
    )
    ml_max_validation_alert_rate: float = Field(
        default=0.05,
        ge=0.001,
        le=1.0,
        description="Maximum validation alert rate constraint for threshold selection",
    )

    # Risk Scoring & Explainability (Phase 8)
    risk_config_version: str = Field(
        default="rc_v1.0",
        description="Immutable risk scoring configuration version identifier",
    )
    risk_weight_ml: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Weight of normalized ML anomaly signal in composite risk score",
    )
    risk_weight_rule: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Weight of deterministic rule score in composite risk score",
    )
    risk_escalation_floor_enabled: bool = Field(
        default=False,
        description="Whether rule-severity escalation floors are applied to composite risk score",
    )

    # AI Investigation Assistant (Phase 10)
    ai_provider: Literal["mock"] = Field(
        default="mock",
        description="Active AI summarization provider identifier",
    )
    ai_model: str = Field(
        default="mock-summarizer-v1",
        description="Default AI summarization model identifier",
    )
    ai_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Timeout in seconds for AI summary generation attempts",
    )
    ai_max_evidence_items: int = Field(
        default=50,
        ge=5,
        le=200,
        description="Maximum number of evidence records included in AI context",
    )
    ai_max_context_bytes: int = Field(
        default=65536,
        ge=4096,
        le=262144,
        description="Maximum serialized byte budget for AI context payload",
    )
    ai_pending_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Duration in seconds before an abandoned PENDING AI summary is considered expired",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, v: object) -> object:
        """Allow CORS origins as comma-separated string, JSON list, or Python list.

        Wildcard '*' is strictly forbidden when credentialed CORS is enabled,
        preventing dangerous browser credential leakage.
        """
        parsed: list[str] = []
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                import json

                try:
                    loaded = json.loads(stripped)
                    if isinstance(loaded, list):
                        parsed = [
                            str(item).strip() for item in loaded if str(item).strip()
                        ]
                except Exception:
                    parsed = [
                        origin.strip()
                        for origin in stripped.split(",")
                        if origin.strip()
                    ]
            else:
                parsed = [
                    origin.strip() for origin in stripped.split(",") if origin.strip()
                ]
        elif isinstance(v, (list, tuple, set)):
            parsed = [str(item).strip() for item in v if str(item).strip()]
        elif v is None:
            return []
        else:
            return v

        for origin in parsed:
            if origin == "*":
                raise ValueError(
                    "Wildcard '*' CORS origin is forbidden when allow_credentials=True. "
                    "Explicit domain origins must be specified."
                )
        return parsed

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
        validation_alias=AliasChoices(
            "finsignal_database_host", "database_host", "postgres_host"
        ),
    )
    database_port: int = Field(
        default=5432,
        validation_alias=AliasChoices(
            "finsignal_database_port", "database_port", "postgres_port"
        ),
    )
    database_name: str = Field(
        default="finsignal_dev",
        validation_alias=AliasChoices(
            "finsignal_database_name", "database_name", "postgres_db", "database_db"
        ),
    )
    database_user: str = Field(
        default="postgres",
        validation_alias=AliasChoices(
            "finsignal_database_user", "database_user", "postgres_user"
        ),
    )
    database_password: SecretStr = Field(
        ...,
        validation_alias=AliasChoices(
            "finsignal_database_password", "database_password", "postgres_password"
        ),
        description="PostgreSQL password (strictly required, never logged)",
    )

    # JWT authentication settings
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-insecure-jwt-secret-key-for-testing-only-32chars"),
        validation_alias=AliasChoices(
            "finsignal_jwt_secret_key", "jwt_secret_key", "secret_key"
        ),
        description="Cryptographic secret key for signing JWT tokens",
    )
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        validation_alias=AliasChoices(
            "finsignal_access_token_expire_minutes", "access_token_expire_minutes"
        ),
        description="Access token validity window in minutes",
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        validation_alias=AliasChoices("finsignal_cors_origins", "cors_origins"),
    )

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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        custom_env = (
            _FinSignalEnvSettingsSource(
                settings_cls,
                case_sensitive=env_settings.case_sensitive,
                env_prefix=env_settings.env_prefix,
                env_nested_delimiter=env_settings.env_nested_delimiter,
            )
            if isinstance(env_settings, EnvSettingsSource)
            else env_settings
        )
        custom_dotenv = (
            _FinSignalDotEnvSettingsSource(
                settings_cls,
                env_file=dotenv_settings.env_file,
                env_file_encoding=dotenv_settings.env_file_encoding,
                case_sensitive=dotenv_settings.case_sensitive,
                env_prefix=dotenv_settings.env_prefix,
                env_nested_delimiter=dotenv_settings.env_nested_delimiter,
            )
            if isinstance(dotenv_settings, DotEnvSettingsSource)
            else dotenv_settings
        )
        return (
            init_settings,
            custom_env,
            custom_dotenv,
            file_secret_settings,
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
