"""Pydantic v2 schemas for authentication request and response contracts."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from finsignal.users.repository import normalize_email


class RegisterRequest(BaseModel):
    """Registration request payload for new application user accounts."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        max_length=128,
        description="Plaintext password (strictly 12-128 characters)",
    )

    @field_validator("email", mode="after")
    @classmethod
    def normalize_request_email(cls, v: EmailStr) -> str:
        """Normalize email address to lowercase and trimmed string."""
        return normalize_email(str(v))


class LoginRequest(BaseModel):
    """Login request payload for user authentication."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Plaintext password candidate",
    )

    @field_validator("email", mode="after")
    @classmethod
    def normalize_request_email(cls, v: EmailStr) -> str:
        """Normalize email address to lowercase and trimmed string."""
        return normalize_email(str(v))


class TokenResponse(BaseModel):
    """JWT bearer token response payload."""

    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(..., description="Signed JWT access token")
    token_type: Literal["bearer"] = Field(
        default="bearer", description="Token type identifier"
    )
    expires_in: int = Field(..., ge=1, description="Token lifetime in seconds")


class UserResponse(BaseModel):
    """Sanitized user identity representation safe for client responses."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime


class LogoutResponse(BaseModel):
    """Logout confirmation response payload."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        default="Successfully logged out.",
        description="Human-readable confirmation message",
    )
