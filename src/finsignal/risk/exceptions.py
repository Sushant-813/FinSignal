"""Domain exceptions for FinSignal Phase 8 Risk Analysis & Explainability."""

from typing import Any

from finsignal.common.exceptions import FinSignalError, NotFoundError, ValidationError


class RiskDomainError(FinSignalError):
    """Base exception for risk domain errors."""

    def __init__(
        self,
        message: str = "A risk analysis error occurred.",
        code: str = "RISK_DOMAIN_ERROR",
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


class RiskAnalysisNotFoundError(NotFoundError):
    """Raised when a requested risk analysis is not found."""

    def __init__(
        self,
        message: str = "No risk analysis found for the requested transaction.",
        code: str = "RISK_ANALYSIS_NOT_FOUND",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            internal_context=internal_context,
        )


class RiskConfigurationError(ValidationError):
    """Raised when risk scoring configuration or normalization bounds are invalid."""

    def __init__(
        self,
        message: str = "Invalid risk scoring configuration.",
        code: str = "INVALID_RISK_CONFIGURATION",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            internal_context=internal_context,
        )


class IneligibleModelStatusError(ValidationError):
    """Raised when inference is requested against an ineligible model status."""

    def __init__(
        self,
        message: str = "The specified model status is ineligible for risk analysis.",
        code: str = "INELIGIBLE_MODEL_STATUS",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            details=details,
            internal_context=internal_context,
        )
