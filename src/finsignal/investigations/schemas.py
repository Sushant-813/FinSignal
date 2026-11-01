"""Pydantic v2 schemas and validation DTOs for Phase 9 Investigation & Evidence."""

import json
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_EVIDENCE_PAYLOAD_BYTES = 65536  # 64 KB limit


class InvestigationStatus(StrEnum):
    """Investigation operational lifecycle states."""

    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"


class InvestigationPriority(StrEnum):
    """Investigation urgency priority classifications."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InvestigationResolution(StrEnum):
    """Formal investigator resolution classifications."""

    LEGITIMATE = "LEGITIMATE"
    SUSPICIOUS = "SUSPICIOUS"
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    INCONCLUSIVE = "INCONCLUSIVE"


class InvestigationRelationshipType(StrEnum):
    """Transaction link relationship classifications."""

    PRIMARY = "PRIMARY"
    RELATED = "RELATED"


class EvidenceType(StrEnum):
    """Evidence finding classification."""

    TRANSACTION_FACT = "TRANSACTION_FACT"
    RISK_SCORE = "RISK_SCORE"
    RISK_FACTOR = "RISK_FACTOR"
    ACCOUNT_PROFILE = "ACCOUNT_PROFILE"
    DEVICE_PROFILE = "DEVICE_PROFILE"
    USER_NOTE = "USER_NOTE"


class EvidenceSourceType(StrEnum):
    """Underlying domain entity source type."""

    TRANSACTION = "TRANSACTION"
    RISK_ANALYSIS = "RISK_ANALYSIS"
    RISK_FACTOR = "RISK_FACTOR"
    ACCOUNT = "ACCOUNT"
    DEVICE = "DEVICE"
    USER_NOTE = "USER_NOTE"


EVIDENCE_TYPE_SOURCE_MAPPING: dict[EvidenceType, EvidenceSourceType] = {
    EvidenceType.TRANSACTION_FACT: EvidenceSourceType.TRANSACTION,
    EvidenceType.RISK_SCORE: EvidenceSourceType.RISK_ANALYSIS,
    EvidenceType.RISK_FACTOR: EvidenceSourceType.RISK_FACTOR,
    EvidenceType.ACCOUNT_PROFILE: EvidenceSourceType.ACCOUNT,
    EvidenceType.DEVICE_PROFILE: EvidenceSourceType.DEVICE,
    EvidenceType.USER_NOTE: EvidenceSourceType.USER_NOTE,
}


class InvestigationCreateRequest(BaseModel):
    """Request payload for manual investigation case creation."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: uuid.UUID = Field(
        ..., description="Target primary transaction UUID"
    )
    priority: InvestigationPriority = Field(
        default=InvestigationPriority.MEDIUM,
        description="Case triage priority",
    )


class InvestigationPrimaryTransactionDTO(BaseModel):
    """Primary transaction representation within investigation context."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    external_transaction_id: str
    account_id: uuid.UUID
    amount: str
    currency: str
    direction: str
    occurred_at: datetime
    source_namespace: str
    category: str | None = None
    payment_method: str | None = None


class InvestigationLatestRiskDTO(BaseModel):
    """Latest risk analysis snapshot for primary transaction."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    score: float
    risk_level: str
    model_version: str
    created_at: datetime


class InvestigationTransactionItem(BaseModel):
    """Transaction item linked to an investigation."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: uuid.UUID
    relationship_type: InvestigationRelationshipType
    account_id: uuid.UUID
    amount: str
    currency: str
    direction: str
    occurred_at: datetime
    created_at: datetime


class InvestigationDetailResponse(BaseModel):
    """Complete investigation workspace detail response."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    status: InvestigationStatus
    priority: InvestigationPriority
    assigned_to: uuid.UUID | None
    assigned_user_email: str | None = None
    primary_transaction: InvestigationPrimaryTransactionDTO
    latest_risk_analysis: InvestigationLatestRiskDTO | None = None
    related_transactions: list[InvestigationTransactionItem] = Field(
        default_factory=list
    )
    resolution: InvestigationResolution | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class InvestigationSummaryItem(BaseModel):
    """Item representation in paginated investigation lists."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    status: InvestigationStatus
    priority: InvestigationPriority
    assigned_to: uuid.UUID | None
    primary_transaction_id: uuid.UUID
    account_id: uuid.UUID
    resolution: InvestigationResolution | None = None
    created_at: datetime
    updated_at: datetime


class InvestigationListResponse(BaseModel):
    """Paginated collection response for investigations."""

    model_config = ConfigDict(extra="forbid")

    items: list[InvestigationSummaryItem]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class InvestigationPatchRequest(BaseModel):
    """Request payload for mutable investigation attributes."""

    model_config = ConfigDict(extra="forbid")

    assigned_to: uuid.UUID | None = Field(
        default=None,
        description="Target investigator user UUID, or explicit null to unassign",
    )
    status: InvestigationStatus | None = Field(
        default=None,
        description="Lifecycle state transition (only OPEN -> UNDER_REVIEW supported via PATCH)",
    )
    priority: InvestigationPriority | None = Field(
        default=None,
        description="Urgency priority adjustment",
    )


class InvestigationResolveRequest(BaseModel):
    """Request payload for explicit case resolution."""

    model_config = ConfigDict(extra="forbid")

    resolution: InvestigationResolution = Field(
        ..., description="Final investigative outcome"
    )
    resolution_notes: str = Field(
        ..., description="Meaningful explanatory notes (non-whitespace)"
    )

    @field_validator("resolution_notes")
    @classmethod
    def validate_non_whitespace_notes(cls, v: str) -> str:
        """Enforce that resolution notes contain non-whitespace text."""
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("resolution_notes must contain non-whitespace characters.")
        return trimmed


class InvestigationTransactionsListResponse(BaseModel):
    """Collection response of all transactions associated with an investigation."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: uuid.UUID
    items: list[InvestigationTransactionItem]


class InvestigationRelatedTransactionAddRequest(BaseModel):
    """Request payload to associate a related transaction."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: uuid.UUID = Field(
        ..., description="Transaction UUID to link as RELATED"
    )


class InvestigationEvidenceCreateRequest(BaseModel):
    """Request payload to attach a new evidence record."""

    model_config = ConfigDict(extra="forbid")

    evidence_type: EvidenceType
    source_type: EvidenceSourceType
    source_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    payload: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def validate_title_non_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("title cannot be empty or whitespace-only.")
        return trimmed

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            serialized = json.dumps(v)
            if len(serialized.encode("utf-8")) > MAX_EVIDENCE_PAYLOAD_BYTES:
                raise ValueError(
                    f"payload exceeds maximum permitted size of {MAX_EVIDENCE_PAYLOAD_BYTES} bytes."
                )
        return v


class InvestigationEvidenceResponse(BaseModel):
    """Single evidence record response."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    investigation_id: uuid.UUID
    evidence_type: EvidenceType
    source_type: EvidenceSourceType
    source_id: uuid.UUID | None
    title: str
    description: str | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime


class InvestigationEvidenceListResponse(BaseModel):
    """Paginated collection response for evidence records."""

    model_config = ConfigDict(extra="forbid")

    items: list[InvestigationEvidenceResponse]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
