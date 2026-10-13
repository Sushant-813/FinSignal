"""Centralized FastAPI exception handlers ensuring safe error envelopes and sanitization."""

import logging
import re

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from finsignal.common.exceptions import FinSignalError
from finsignal.core.logging import request_id_ctx

logger = logging.getLogger("finsignal.handlers")

FIELD_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{1,64}$")

# Safe allowlisted messages for standard HTTP status codes
SAFE_HTTP_MESSAGES: dict[int, str] = {
    400: "Bad request.",
    401: "Authentication credentials were not provided or are invalid.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    405: "Method not allowed for this resource.",
    409: "A state conflict occurred.",
    422: "Request validation failed.",
    429: "Too many requests. Please try again later.",
    500: "An internal server error occurred.",
    502: "Bad gateway.",
    503: "Service temporarily unavailable.",
    504: "Gateway timeout.",
}

# Predictable client-safe descriptions mapped by Pydantic error type
SAFE_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "Field required.",
    "extra_forbidden": "Unexpected field in payload.",
    "string_too_short": "Value is too short.",
    "string_too_long": "Value is too long.",
    "string_pattern_mismatch": "Value does not match required format.",
    "greater_than": "Value is below minimum threshold.",
    "greater_than_equal": "Value is below minimum threshold.",
    "less_than": "Value exceeds maximum threshold.",
    "less_than_equal": "Value exceeds maximum threshold.",
    "enum": "Value is not an accepted choice.",
    "int_parsing": "Value must be a valid integer.",
    "float_parsing": "Value must be a valid number.",
    "decimal_parsing": "Value must be a valid decimal amount.",
    "uuid_parsing": "Value must be a valid UUID.",
    "date_parsing": "Value must be a valid date.",
    "datetime_parsing": "Value must be a valid ISO 8601 datetime.",
    "json_invalid": "Invalid JSON format.",
    "value_error": "Invalid input value.",
}


async def finsignal_exception_handler(
    request: Request, exc: FinSignalError
) -> JSONResponse:
    """Handle custom application exceptions, logging safe scalar metadata without leaking internal context."""
    request_id = request_id_ctx.get("-")

    # Safe logging: scalar metadata only; raw exc.internal_context is never attached to extra or message
    logger.warning(
        "Application error encountered: code=%s exception_class=%s has_internal_context=%s",
        exc.code,
        exc.__class__.__name__,
        bool(exc.internal_context),
        extra={
            "request_id": request_id,
            "exception_code": exc.code,
            "exception_class": exc.__class__.__name__,
            "has_internal_context": bool(exc.internal_context),
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation errors without reflecting caller-supplied sensitive values or keys."""
    request_id = request_id_ctx.get("-")
    field_details: dict[str, list[str]] = {}

    for error in exc.errors():
        err_type = str(error.get("type", ""))

        # If unexpected extra fields are forbidden, use generic field label
        if err_type == "extra_forbidden":
            loc_label = "extra_fields"
        else:
            raw_loc = [str(item) for item in error.get("loc", []) if item != "body"]
            # Validate field location: only accept standard alphanumeric field names to avoid echoing arbitrary keys
            valid_loc = [part for part in raw_loc if FIELD_NAME_REGEX.match(part)]
            loc_label = ".".join(valid_loc) if valid_loc else "payload"

        safe_msg = SAFE_VALIDATION_MESSAGES.get(err_type, "Invalid input value.")
        field_details.setdefault(loc_label, []).append(safe_msg)

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": field_details,
                "request_id": request_id,
            }
        },
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy errors, suppressing raw SQL statements, driver messages, and credentials."""
    request_id = request_id_ctx.get("-")

    # Safe logging: exception class name and request ID only
    logger.error(
        "Database operation failed: exception_class=%s",
        exc.__class__.__name__,
        extra={"exception_class": exc.__class__.__name__, "request_id": request_id},
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "A database error occurred.",
                "details": {},
                "request_id": request_id,
            }
        },
    )


async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle Starlette HTTP exceptions, using allowlisted public messages while preserving protocol headers."""
    request_id = request_id_ctx.get("-")
    code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else f"HTTP_{exc.status_code}"
    message = SAFE_HTTP_MESSAGES.get(exc.status_code, "An HTTP error occurred.")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "request_id": request_id,
            }
        },
        headers=exc.headers,
    )
