"""Standardized machine-readable API error response schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorPayload(BaseModel):
    """Machine-readable error payload conforming to API_GUIDELINES.md §42."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Stable, machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Field or context error details"
    )
    request_id: str = Field(..., description="Correlation request ID")


class ErrorResponse(BaseModel):
    """Standard top-level error response envelope."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorPayload
