"""Unit tests for investigation schemas, enums, validators, and DTO contracts (Phase 9)."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from finsignal.investigations.schemas import (
    EVIDENCE_TYPE_SOURCE_MAPPING,
    EvidenceSourceType,
    EvidenceType,
    InvestigationCreateRequest,
    InvestigationDetailResponse,
    InvestigationEvidenceCreateRequest,
    InvestigationListResponse,
    InvestigationPatchRequest,
    InvestigationPrimaryTransactionDTO,
    InvestigationPriority,
    InvestigationResolution,
    InvestigationResolveRequest,
    InvestigationStatus,
    InvestigationSummaryItem,
)


def test_investigation_status_enums() -> None:
    """Verify approved lifecycle states."""
    assert InvestigationStatus.OPEN == "OPEN"
    assert InvestigationStatus.UNDER_REVIEW == "UNDER_REVIEW"
    assert InvestigationStatus.RESOLVED == "RESOLVED"
    assert len(InvestigationStatus) == 3


def test_investigation_priority_enums() -> None:
    """Verify approved priority values."""
    assert InvestigationPriority.LOW == "LOW"
    assert InvestigationPriority.MEDIUM == "MEDIUM"
    assert InvestigationPriority.HIGH == "HIGH"
    assert InvestigationPriority.CRITICAL == "CRITICAL"
    assert len(InvestigationPriority) == 4


def test_investigation_resolution_enums() -> None:
    """Verify approved resolution outcomes."""
    assert InvestigationResolution.LEGITIMATE == "LEGITIMATE"
    assert InvestigationResolution.SUSPICIOUS == "SUSPICIOUS"
    assert InvestigationResolution.CONFIRMED_FRAUD == "CONFIRMED_FRAUD"
    assert InvestigationResolution.INCONCLUSIVE == "INCONCLUSIVE"
    assert len(InvestigationResolution) == 4


def test_evidence_and_source_type_pairings() -> None:
    """Verify 1-to-1 canonical pairing map for all 6 evidence types."""
    assert (
        EVIDENCE_TYPE_SOURCE_MAPPING[EvidenceType.TRANSACTION_FACT]
        == EvidenceSourceType.TRANSACTION
    )
    assert (
        EVIDENCE_TYPE_SOURCE_MAPPING[EvidenceType.RISK_SCORE]
        == EvidenceSourceType.RISK_ANALYSIS
    )
    assert (
        EVIDENCE_TYPE_SOURCE_MAPPING[EvidenceType.RISK_FACTOR]
        == EvidenceSourceType.RISK_FACTOR
    )
    assert (
        EVIDENCE_TYPE_SOURCE_MAPPING[EvidenceType.ACCOUNT_PROFILE]
        == EvidenceSourceType.ACCOUNT
    )
    assert (
        EVIDENCE_TYPE_SOURCE_MAPPING[EvidenceType.DEVICE_PROFILE]
        == EvidenceSourceType.DEVICE
    )
    assert (
        EVIDENCE_TYPE_SOURCE_MAPPING[EvidenceType.USER_NOTE]
        == EvidenceSourceType.USER_NOTE
    )
    assert len(EVIDENCE_TYPE_SOURCE_MAPPING) == 6


def test_create_request_validation() -> None:
    """Verify InvestigationCreateRequest defaults and restrictions."""
    tx_id = uuid.uuid4()
    req = InvestigationCreateRequest(transaction_id=tx_id)
    assert req.transaction_id == tx_id
    assert req.priority == InvestigationPriority.MEDIUM

    req_high = InvestigationCreateRequest(
        transaction_id=tx_id, priority=InvestigationPriority.HIGH
    )
    assert req_high.priority == InvestigationPriority.HIGH

    # Disallow extra fields
    with pytest.raises(ValidationError):
        InvestigationCreateRequest(transaction_id=tx_id, title="Forbidden Title")  # type: ignore[call-arg]


def test_resolve_request_validation() -> None:
    """Verify resolution notes non-whitespace constraint."""
    # Valid notes
    req = InvestigationResolveRequest(
        resolution=InvestigationResolution.CONFIRMED_FRAUD,
        resolution_notes="Found multiple linked compromised accounts.",
    )
    assert req.resolution == InvestigationResolution.CONFIRMED_FRAUD
    assert req.resolution_notes == "Found multiple linked compromised accounts."

    # Whitespace-only notes must fail
    with pytest.raises(ValidationError) as exc:
        InvestigationResolveRequest(
            resolution=InvestigationResolution.CONFIRMED_FRAUD,
            resolution_notes="   \t\n   ",
        )
    assert "resolution_notes must contain non-whitespace characters" in str(exc.value)

    # Empty notes must fail
    with pytest.raises(ValidationError) as exc:
        InvestigationResolveRequest(
            resolution=InvestigationResolution.CONFIRMED_FRAUD,
            resolution_notes="",
        )
    assert "resolution_notes must contain non-whitespace characters" in str(exc.value)


def test_patch_request_validation() -> None:
    """Verify InvestigationPatchRequest fields."""
    uid = uuid.uuid4()
    patch = InvestigationPatchRequest(
        assigned_to=uid,
        status=InvestigationStatus.UNDER_REVIEW,
        priority=InvestigationPriority.CRITICAL,
    )
    assert patch.assigned_to == uid
    assert patch.status == InvestigationStatus.UNDER_REVIEW
    assert patch.priority == InvestigationPriority.CRITICAL

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        InvestigationPatchRequest(unsupported_field="fail")  # type: ignore[call-arg]


def test_evidence_create_request_payload_size() -> None:
    """Verify payload 64 KB validation and title whitespace checks."""
    # Valid payload within 64 KB
    valid_payload = {"key": "x" * 1000}
    req = InvestigationEvidenceCreateRequest(
        evidence_type=EvidenceType.TRANSACTION_FACT,
        source_type=EvidenceSourceType.TRANSACTION,
        source_id=uuid.uuid4(),
        title="Transaction Record",
        payload=valid_payload,
    )
    assert req.title == "Transaction Record"

    # Whitespace-only title must fail
    with pytest.raises(ValidationError) as exc:
        InvestigationEvidenceCreateRequest(
            evidence_type=EvidenceType.TRANSACTION_FACT,
            source_type=EvidenceSourceType.TRANSACTION,
            source_id=uuid.uuid4(),
            title="   \t   ",
            payload=valid_payload,
        )
    assert "title cannot be empty or whitespace-only" in str(exc.value)

    # Payload exceeding 64 KB must fail
    huge_payload = {"large": "x" * 70000}
    with pytest.raises(ValidationError) as exc:
        InvestigationEvidenceCreateRequest(
            evidence_type=EvidenceType.USER_NOTE,
            source_type=EvidenceSourceType.USER_NOTE,
            title="Large Note",
            payload=huge_payload,
        )
    assert "payload exceeds maximum permitted size" in str(exc.value)


def test_dtos_serialization() -> None:
    """Verify serialization of summary, detail, and list envelopes."""
    inv_id = uuid.uuid4()
    tx_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    now = datetime.now(UTC)

    primary_tx = InvestigationPrimaryTransactionDTO(
        id=tx_id,
        external_transaction_id="TX_1001",
        account_id=acc_id,
        amount="250.00",
        currency="USD",
        direction="DEBIT",
        occurred_at=now,
        source_namespace="SYNTHETIC",
        category="RETAIL",
        payment_method="CARD",
    )

    detail = InvestigationDetailResponse(
        id=inv_id,
        status=InvestigationStatus.OPEN,
        priority=InvestigationPriority.MEDIUM,
        assigned_to=None,
        primary_transaction=primary_tx,
        created_at=now,
        updated_at=now,
    )
    assert detail.id == inv_id
    assert detail.primary_transaction.amount == "250.00"

    summary_item = InvestigationSummaryItem(
        id=inv_id,
        status=InvestigationStatus.OPEN,
        priority=InvestigationPriority.MEDIUM,
        assigned_to=None,
        primary_transaction_id=tx_id,
        account_id=acc_id,
        created_at=now,
        updated_at=now,
    )

    list_response = InvestigationListResponse(
        items=[summary_item],
        page=1,
        page_size=25,
        total=1,
        total_pages=1,
    )
    assert len(list_response.items) == 1
    assert list_response.total == 1
