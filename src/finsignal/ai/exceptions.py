"""AI Investigation Assistant domain exceptions with machine-readable API error metadata."""

from typing import Any

from finsignal.common.exceptions import ConflictError, FinSignalError


class AISummaryError(FinSignalError):
    """Base exception for all AI Investigation Assistant errors."""


class InvestigationResolvedError(ConflictError):
    """Raised when an AI summary generation is requested on an already resolved investigation."""

    def __init__(
        self,
        message: str = "Cannot generate AI summary for a resolved investigation.",
        code: str = "INVESTIGATION_ALREADY_RESOLVED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class AISummaryInProgressError(ConflictError):
    """Raised when an active generation is already pending for the investigation."""

    def __init__(
        self,
        message: str = "An AI summary generation attempt is already in progress for this investigation.",
        code: str = "AI_SUMMARY_IN_PROGRESS",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class GenerationLeaseExpiredError(ConflictError):
    """Raised when a completed generation attempt's lease has expired or been recovered."""

    def __init__(
        self,
        message: str = "The AI generation lease expired or was superseded before completion.",
        code: str = "GENERATION_LEASE_EXPIRED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class ProviderTimeoutError(AISummaryError):
    """External/Mock provider execution timed out (HTTP 504)."""

    def __init__(
        self,
        message: str = "AI provider timed out while generating summary.",
        code: str = "PROVIDER_TIMEOUT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=504, details=details)


class ProviderExecutionError(AISummaryError):
    """Provider encountered an upstream failure (HTTP 502)."""

    def __init__(
        self,
        message: str = "AI provider encountered an error during generation.",
        code: str = "PROVIDER_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=502, details=details)


class InvalidProviderOutputError(AISummaryError):
    """Provider output failed JSON parsing or schema validation (HTTP 502)."""

    def __init__(
        self,
        message: str = "AI provider returned malformed or invalid output.",
        code: str = "INVALID_PROVIDER_OUTPUT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=502, details=details)


class GroundingValidationError(AISummaryError):
    """Provider output cited uncorroborated, non-existent, or invalid evidence references (HTTP 502)."""

    def __init__(
        self,
        message: str = "AI summary citations failed evidence grounding validation.",
        code: str = "GROUNDING_VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=502, details=details)
