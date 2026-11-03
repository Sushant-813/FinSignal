"""Pydantic v2 schemas and validation DTOs for Phase 10 AI Investigation Assistant."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AISummaryStatus(StrEnum):
    """Lifecycle state classifications for AI summary generation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvidenceReference(BaseModel):
    """Typed reference linking an observation or claim to source evidence."""

    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(
        ..., description="Evidence source type (e.g. TRANSACTION, RISK_FACTOR, ACCOUNT)"
    )
    source_id: uuid.UUID | None = Field(
        default=None, description="Authoritative UUID of the referenced entity"
    )
    note: str | None = Field(
        default=None, description="Contextual note describing relevance"
    )


class GroundedObservation(BaseModel):
    """An analytical observation citing at least one verified evidence or transaction identifier."""

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Specific factual claim or derived observation",
    )
    evidence_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        description="Citations to verified evidence/transaction UUIDs",
    )


class AISummaryOutput(BaseModel):
    """Structured AI-generated briefing output format."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(
        ...,
        min_length=1,
        max_length=3000,
        description="Concise high-level synthesis of case findings for investigators",
    )
    observed_facts: list[GroundedObservation] = Field(
        ...,
        min_length=1,
        description="Factual observations directly corroborated by case evidence",
    )
    derived_signals: list[GroundedObservation] = Field(
        default_factory=list,
        description="Analytical risk signals, anomalies, and factor deviations",
    )
    potential_interpretations: list[str] = Field(
        default_factory=list,
        description="Non-binding hypotheses or fraud typologies for investigator consideration",
    )
    uncertainties_and_limitations: list[str] = Field(
        default_factory=list,
        description="Explicit gaps, omitted context, data limits, or unverified claims",
    )


class AISummaryGenerateRequest(BaseModel):
    """Request payload to trigger AI summary generation."""

    model_config = ConfigDict(extra="forbid")

    force_refresh: bool = Field(
        default=False,
        description="When true, bypasses reuse of existing matching completed summaries and forces regeneration",
    )


class AISummaryResponse(BaseModel):
    """Client representation of a persistent AI summary record."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    investigation_id: uuid.UUID
    provider: str
    model: str
    prompt_version: str
    evidence_hash: str
    context_hash: str
    status: AISummaryStatus
    summary: AISummaryOutput | None = None
    error_message: str | None = None
    is_stale: bool = Field(
        default=False, description="Whether case evidence has changed since generation"
    )
    generated_at: datetime
    completed_at: datetime | None = None
    created_at: datetime


class AISummaryListResponse(BaseModel):
    """Paginated collection response for investigation AI summary history."""

    model_config = ConfigDict(extra="forbid")

    items: list[AISummaryResponse]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
