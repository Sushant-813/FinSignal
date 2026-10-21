"""Shared cross-cutting domain abstractions, exceptions, response models, and handlers."""

from finsignal.common.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    FinSignalError,
    InfrastructureError,
    NamespaceMismatchError,
    NotFoundError,
    ValidationError,
)
from finsignal.common.handlers import (
    finsignal_exception_handler,
    sqlalchemy_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
)
from finsignal.common.responses import ErrorPayload, ErrorResponse

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "ErrorPayload",
    "ErrorResponse",
    "FinSignalError",
    "InfrastructureError",
    "NamespaceMismatchError",
    "NotFoundError",
    "ValidationError",
    "finsignal_exception_handler",
    "sqlalchemy_exception_handler",
    "starlette_http_exception_handler",
    "validation_exception_handler",
]
