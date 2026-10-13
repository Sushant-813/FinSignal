"""Unit tests for application exception hierarchy and safety contracts."""

import pytest

from finsignal.common.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    FinSignalError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
)


def test_finsignal_error_defaults_and_contracts() -> None:
    """Verify base exception defaults, safety contract attributes, and status code."""
    exc = FinSignalError(
        message="Client safe error",
        code="CUSTOM_CODE",
        status_code=400,
        details={"field": "value"},
        internal_context={"raw_driver": "error_detail"},
    )
    assert str(exc) == "Client safe error"
    assert exc.message == "Client safe error"
    assert exc.code == "CUSTOM_CODE"
    assert exc.status_code == 400
    assert exc.details == {"field": "value"}
    assert exc.internal_context == {"raw_driver": "error_detail"}


def test_finsignal_error_code_format_validation() -> None:
    """Verify exception code must follow strict upper snake-case format."""
    # Valid codes
    FinSignalError("msg", code="VALID_CODE_123")
    FinSignalError("msg", code="ABC")

    # Invalid codes
    with pytest.raises(ValueError, match="Invalid error code format"):
        FinSignalError("msg", code="lowercase_code")

    with pytest.raises(ValueError, match="Invalid error code format"):
        FinSignalError("msg", code="with spaces")

    with pytest.raises(ValueError, match="Invalid error code format"):
        FinSignalError("msg", code="NO")  # Too short (< 3 chars)

    with pytest.raises(ValueError, match="Invalid error code format"):
        FinSignalError("msg", code="SPECIAL!_CHARS")


def test_exception_subclasses_status_codes_and_defaults() -> None:
    """Verify standard subclasses carry expected HTTP status codes and default machine codes."""
    not_found = NotFoundError()
    assert not_found.status_code == 404
    assert not_found.code == "RESOURCE_NOT_FOUND"

    conflict = ConflictError()
    assert conflict.status_code == 409
    assert conflict.code == "STATE_CONFLICT"

    val_err = ValidationError()
    assert val_err.status_code == 422
    assert val_err.code == "DOMAIN_VALIDATION_ERROR"

    auth_err = AuthenticationError()
    assert auth_err.status_code == 401
    assert auth_err.code == "UNAUTHORIZED"

    forbidden = AuthorizationError()
    assert forbidden.status_code == 403
    assert forbidden.code == "FORBIDDEN"

    infra = InfrastructureError()
    assert infra.status_code == 503
    assert infra.code == "INFRASTRUCTURE_ERROR"
