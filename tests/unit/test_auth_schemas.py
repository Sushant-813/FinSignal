"""Unit tests for authentication request and response schemas."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from finsignal.auth.schemas import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from finsignal.users.models import User
from finsignal.users.repository import normalize_email


def test_normalize_email_helper() -> None:
    """Verify email normalization trims whitespace and lowercases string."""
    assert normalize_email("  User.Name@Example.COM  ") == "user.name@example.com"
    assert normalize_email("simple@domain.org") == "simple@domain.org"
    assert normalize_email("CAPS_USER+tag@TEST.NET ") == "caps_user+tag@test.net"


def test_register_request_valid() -> None:
    """Verify valid RegisterRequest succeeds."""
    req = RegisterRequest(
        email="analyst@example.com",
        password="ValidPassword123!",
    )
    assert req.email == "analyst@example.com"
    assert req.password == "ValidPassword123!"


def test_register_request_email_normalization() -> None:
    """Verify RegisterRequest normalizes email upon instantiation."""
    req = RegisterRequest(
        email="  ANALYST.Lead@FinSignal.IO  ",
        password="ValidPassword123!",
    )
    assert req.email == "analyst.lead@finsignal.io"


def test_register_request_invalid_email() -> None:
    """Verify malformed email addresses are rejected."""
    invalid_emails = [
        "plainaddress",
        "@missingusername.com",
        "username@.com",
        "",
    ]
    for bad_email in invalid_emails:
        with pytest.raises(ValidationError):
            RegisterRequest(
                email=bad_email,
                password="ValidPassword123!",
            )


def test_register_request_password_length_boundaries() -> None:
    """Verify 12-128 character password boundary constraints."""
    # 11 characters (too short)
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="analyst@example.com",
            password="A" * 11,
        )

    # 12 characters (minimum valid)
    req_12 = RegisterRequest(
        email="analyst@example.com",
        password="A" * 12,
    )
    assert len(req_12.password) == 12

    # 128 characters (maximum valid)
    req_128 = RegisterRequest(
        email="analyst@example.com",
        password="A" * 128,
    )
    assert len(req_128.password) == 128

    # 129 characters (too long)
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="analyst@example.com",
            password="A" * 129,
        )


def test_register_request_forbid_extra_fields() -> None:
    """Verify unexpected extra fields including role are strictly rejected."""
    # Attempting privilege escalation via client-supplied role
    with pytest.raises(ValidationError, match="extra_forbidden"):
        RegisterRequest.model_validate(
            {
                "email": "analyst@example.com",
                "password": "ValidPassword123!",
                "role": "ADMIN",
            }
        )

    # Any other arbitrary unexpected field
    with pytest.raises(ValidationError, match="extra_forbidden"):
        RegisterRequest.model_validate(
            {
                "email": "analyst@example.com",
                "password": "ValidPassword123!",
                "is_active": False,
            }
        )


def test_login_request_valid() -> None:
    """Verify valid LoginRequest succeeds."""
    req = LoginRequest(
        email="investigator@example.com",
        password="Password123!",
    )
    assert req.email == "investigator@example.com"
    assert req.password == "Password123!"


def test_login_request_email_normalization() -> None:
    """Verify LoginRequest normalizes email consistently with RegisterRequest."""
    req = LoginRequest(
        email="  INVESTIGATOR@Example.COM  ",
        password="Password123!",
    )
    assert req.email == "investigator@example.com"


def test_login_request_empty_password_rejected() -> None:
    """Verify empty password candidate is rejected."""
    with pytest.raises(ValidationError):
        LoginRequest(
            email="user@example.com",
            password="",
        )


def test_login_request_extra_fields_forbidden() -> None:
    """Verify unexpected fields are rejected on LoginRequest."""
    with pytest.raises(ValidationError, match="extra_forbidden"):
        LoginRequest.model_validate(
            {
                "email": "user@example.com",
                "password": "Password123!",
                "remember_me": True,
            }
        )


def test_token_response_defaults_and_validation() -> None:
    """Verify TokenResponse fields and constraints."""
    res = TokenResponse(access_token="valid_jwt_token", expires_in=1800)
    assert res.access_token == "valid_jwt_token"
    assert res.token_type == "bearer"
    assert res.expires_in == 1800

    # Non-positive expires_in rejected
    with pytest.raises(ValidationError):
        TokenResponse(access_token="valid_jwt_token", expires_in=0)


def test_user_response_serialization_and_sanitization() -> None:
    """Verify UserResponse serializes approved fields and never exposes password_hash."""
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    # Construct user model instance with sensitive password_hash
    user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$sensitive_hash",
        role="ANALYST",
        is_active=True,
        created_at=now,
    )

    # Validate from ORM attributes
    res = UserResponse.model_validate(user)
    assert res.id == user_id
    assert res.email == "analyst@example.com"
    assert res.role == "ANALYST"
    assert res.is_active is True
    assert res.created_at == now

    dumped = res.model_dump()
    assert set(dumped.keys()) == {"id", "email", "role", "is_active", "created_at"}
    assert "password_hash" not in dumped
    assert "password" not in dumped


def test_logout_response_default_message() -> None:
    """Verify LogoutResponse default message and structure."""
    res = LogoutResponse()
    assert res.message == "Successfully logged out."
