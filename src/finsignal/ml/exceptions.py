"""Domain exceptions for FinSignal Phase 7 Machine Learning Subsystem."""

from typing import Any

from finsignal.common.exceptions import FinSignalError, NotFoundError, ValidationError


class MLDomainError(FinSignalError):
    """Base exception for machine learning subsystem domain errors."""

    def __init__(
        self,
        message: str = "A machine learning subsystem error occurred.",
        code: str = "ML_DOMAIN_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            internal_context=internal_context,
        )


class ModelIntegrityError(MLDomainError):
    """Raised when model artifact integrity verification fails (e.g. SHA-256 digest mismatch)."""

    def __init__(
        self,
        message: str = "Model artifact integrity verification failed.",
        code: str = "MODEL_INTEGRITY_ERROR",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            details=details,
            internal_context=internal_context,
        )


class ModelNotFoundError(NotFoundError):
    """Raised when a requested model version cannot be found."""

    def __init__(
        self,
        message: str = "The requested model version was not found.",
        code: str = "MODEL_NOT_FOUND",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            internal_context=internal_context,
        )


class NoActiveModelError(NotFoundError):
    """Raised when inference is requested without an explicit model ID and no active model exists."""

    def __init__(
        self,
        message: str = "No active machine learning model exists for inference.",
        code: str = "NO_ACTIVE_MODEL",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            internal_context=internal_context,
        )


class SchemaValidationError(ValidationError):
    """Raised when input feature matrices or schemas violate required feature contracts."""

    def __init__(
        self,
        message: str = "Input features violate the canonical feature contract.",
        code: str = "SCHEMA_VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            internal_context=internal_context,
        )


class ModelLifecycleError(FinSignalError):
    """Raised when an invalid model lifecycle transition is requested."""

    def __init__(
        self,
        message: str = "Invalid model lifecycle state transition requested.",
        code: str = "MODEL_LIFECYCLE_ERROR",
        status_code: int = 409,
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
            internal_context=internal_context,
        )
