"""Centralized application exception hierarchy and safety contracts."""

import re
from typing import Any

ERROR_CODE_REGEX = re.compile(r"^[A-Z0-9_]{3,64}$")


class FinSignalError(Exception):
    """Base application exception carrying machine-readable API metadata.

    Safety Contract:
    - `message`: Must contain strictly an intentionally selected, client-safe public message.
    - `code`: Controlled machine-readable identifier (upper snake case, 3-64 chars).
    - `details`: Must contain strictly client-safe public metadata (e.g. public field names, public IDs).
      Never include credentials, raw SQL, connection parameters, stack traces, or sensitive transaction data.
    - `internal_context`: Optional dictionary reserved strictly for internal diagnostics;
      it is NEVER serialized into the client HTTP error response and NEVER attached as a raw dict to logging.extra.
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        if not ERROR_CODE_REGEX.match(code):
            msg = f"Invalid error code format: '{code}'. Must match pattern ^[A-Z0-9_]{{3,64}}$"
            raise ValueError(msg)

        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.internal_context = internal_context or {}


class NotFoundError(FinSignalError):
    """Resource not found (HTTP 404)."""

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        code: str = "RESOURCE_NOT_FOUND",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=404,
            details=details,
            internal_context=internal_context,
        )


class ConflictError(FinSignalError):
    """State or uniqueness conflict (HTTP 409)."""

    def __init__(
        self,
        message: str = "A state conflict occurred.",
        code: str = "STATE_CONFLICT",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=409,
            details=details,
            internal_context=internal_context,
        )


class ValidationError(FinSignalError):
    """Application/domain invariant validation failure (HTTP 422, distinct from RequestValidationError)."""

    def __init__(
        self,
        message: str = "Domain validation failed.",
        code: str = "DOMAIN_VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=422,
            details=details,
            internal_context=internal_context,
        )


class AuthenticationError(FinSignalError):
    """Authentication failure (HTTP 401)."""

    def __init__(
        self,
        message: str = "Authentication credentials were not provided or are invalid.",
        code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=401,
            details=details,
            internal_context=internal_context,
        )


class AuthorizationError(FinSignalError):
    """Permission denied (HTTP 403)."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=403,
            details=details,
            internal_context=internal_context,
        )


class InfrastructureError(FinSignalError):
    """External or internal infrastructure dependency failure (HTTP 503)."""

    def __init__(
        self,
        message: str = "A backend service dependency is temporarily unavailable.",
        code: str = "INFRASTRUCTURE_ERROR",
        details: dict[str, Any] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=503,
            details=details,
            internal_context=internal_context,
        )
