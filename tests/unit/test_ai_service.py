"""Unit tests for Phase 10 AISummaryService orchestration, validation, caching, and error handling."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from finsignal.ai.context import ContextMetadata, InvestigationEvidenceContext
from finsignal.ai.exceptions import (
    AISummaryInProgressError,
    GroundingValidationError,
    InvestigationResolvedError,
)
from finsignal.ai.schemas import (
    AISummaryGenerateRequest,
    AISummaryOutput,
    GroundedObservation,
)
from finsignal.ai.service import AISummaryService
from finsignal.common.exceptions import AuthorizationError
from finsignal.core.config import Settings
from finsignal.users.models import User


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        ai_provider="mock",
        ai_model="mock-v1",
        ai_timeout_seconds=5.0,
        ai_max_evidence_items=50,
        ai_max_context_bytes=65536,
        ai_pending_timeout_seconds=60,
    )


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="admin@finsignal.internal",
        password_hash="hash",
        role="ADMIN",
        is_active=True,
    )


@pytest.fixture
def investigator_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="investigator@finsignal.internal",
        password_hash="hash",
        role="INVESTIGATOR",
        is_active=True,
    )


@pytest.fixture
def sample_context() -> InvestigationEvidenceContext:
    tx_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    factor_id = uuid.uuid4()
    return InvestigationEvidenceContext(
        investigation_id=uuid.uuid4(),
        case_metadata={
            "status": "UNDER_REVIEW",
            "priority": "HIGH",
            "title": "Wire Fraud Check",
            "description": "Suspicious rapid transfer",
            "assigned_to": None,
            "created_at": None,
        },
        primary_transaction={
            "id": tx_id,
            "external_transaction_id": "EXT-100",
            "account_id": uuid.uuid4(),
            "counterparty_account_id": None,
            "amount": Decimal("15000.00"),
            "currency": "USD",
            "direction": "OUTBOUND",
            "transaction_type": "TRANSFER",
            "category": "WIRE",
            "payment_method": "SWIFT",
            "source_namespace": "CORE",
            "occurred_at": None,
        },
        latest_risk_analysis={
            "id": uuid.uuid4(),
            "score": Decimal("91.500"),
            "risk_level": "CRITICAL",
            "model_version": "v1.0.0",
        },
        risk_factors=[
            {
                "id": factor_id,
                "factor_code": "velocity_burst",
                "factor_label": "Velocity Burst",
                "severity": "CRITICAL",
                "description": "Unusually high transfer volume",
                "value_numeric": Decimal("10.0"),
                "value_text": None,
            }
        ],
        related_transactions=[],
        evidence_items=[
            {
                "id": ev_id,
                "evidence_type": "NOTE",
                "source_type": "INVESTIGATOR",
                "source_id": None,
                "title": "Investigator note",
                "description": "Customer confirmed unauthorized login",
                "payload": {},
                "created_at": None,
            }
        ],
        context_metadata=ContextMetadata(
            total_evidence_count=1,
            included_evidence_count=1,
            omitted_evidence_count=0,
            omitted_evidence_types=[],
        ),
    )


def test_grounding_validation_unverified_citation(
    test_settings: Settings,
    sample_context: InvestigationEvidenceContext,
) -> None:
    """LLM summary referencing unverified citation raises GroundingValidationError."""
    service = AISummaryService(
        engine=MagicMock(),
        session_maker=MagicMock(),
        settings=test_settings,
    )

    valid_tx_id = sample_context.primary_transaction["id"]
    hallucinated_id = uuid.uuid4()

    output = AISummaryOutput(
        executive_summary="Executive briefing",
        observed_facts=[
            GroundedObservation(claim="Valid observation", evidence_ids=[valid_tx_id]),
            GroundedObservation(
                claim="Hallucinated claim", evidence_ids=[hallucinated_id]
            ),
        ],
        derived_signals=[],
        potential_interpretations=[],
        uncertainties_and_limitations=[],
    )

    with pytest.raises(GroundingValidationError) as exc:
        service._validate_grounding(output, sample_context)

    assert str(hallucinated_id) in str(exc.value.details)


def test_grounding_validation_success(
    test_settings: Settings,
    sample_context: InvestigationEvidenceContext,
) -> None:
    """LLM summary referencing only verified citations passes validation."""
    service = AISummaryService(
        engine=MagicMock(),
        session_maker=MagicMock(),
        settings=test_settings,
    )

    valid_tx_id = sample_context.primary_transaction["id"]
    valid_ev_id = sample_context.evidence_items[0]["id"]

    output = AISummaryOutput(
        executive_summary="Executive briefing",
        observed_facts=[
            GroundedObservation(claim="Fact 1", evidence_ids=[valid_tx_id]),
        ],
        derived_signals=[
            GroundedObservation(claim="Signal 1", evidence_ids=[valid_ev_id]),
        ],
        potential_interpretations=[],
        uncertainties_and_limitations=[],
    )

    # Should not raise
    service._validate_grounding(output, sample_context)


def test_authorization_check_unassigned_investigator(
    test_settings: Settings,
    investigator_user: User,
) -> None:
    """Non-admin investigator cannot access case assigned to another investigator."""
    service = AISummaryService(
        engine=MagicMock(),
        session_maker=MagicMock(),
        settings=test_settings,
    )

    other_user_id = uuid.uuid4()
    mock_inv = MagicMock()
    mock_inv.assigned_to = other_user_id

    with pytest.raises(AuthorizationError):
        service._check_investigation_authorization(mock_inv, investigator_user)


def test_authorization_check_admin_allowed(
    test_settings: Settings, admin_user: User
) -> None:
    """Admin can access any investigation regardless of assignment."""
    service = AISummaryService(
        engine=MagicMock(),
        session_maker=MagicMock(),
        settings=test_settings,
    )

    other_user_id = uuid.uuid4()
    mock_inv = MagicMock()
    mock_inv.assigned_to = other_user_id

    # Should not raise
    service._check_investigation_authorization(mock_inv, admin_user)


@pytest.mark.asyncio
async def test_resolved_investigation_rejects_generation(
    test_settings: Settings,
    admin_user: User,
) -> None:
    """Generating AI summary on RESOLVED or CLOSED investigation raises InvestigationResolvedError."""
    service = AISummaryService(
        engine=MagicMock(),
        session_maker=MagicMock(),
        settings=test_settings,
    )

    mock_inv = MagicMock()
    mock_inv.id = uuid.uuid4()
    mock_inv.status = "RESOLVED"
    mock_inv.assigned_to = admin_user.id

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_inv
    mock_session.execute.return_value = mock_res

    with pytest.raises(InvestigationResolvedError):
        await service._reserve_and_snapshot(
            session=mock_session,
            investigation_id=mock_inv.id,
            request=AISummaryGenerateRequest(),
            current_user=admin_user,
        )

    # Also test CLOSED
    mock_inv.status = "CLOSED"
    with pytest.raises(InvestigationResolvedError):
        await service._reserve_and_snapshot(
            session=mock_session,
            investigation_id=mock_inv.id,
            request=AISummaryGenerateRequest(),
            current_user=admin_user,
        )


@pytest.mark.asyncio
async def test_in_progress_rejects_generation(
    test_settings: Settings,
    admin_user: User,
) -> None:
    """Active unexpired PENDING attempt triggers AISummaryInProgressError."""
    service = AISummaryService(
        engine=MagicMock(),
        session_maker=MagicMock(),
        settings=test_settings,
    )

    mock_inv = MagicMock()
    mock_inv.id = uuid.uuid4()
    mock_inv.status = "UNDER_REVIEW"
    mock_inv.assigned_to = admin_user.id

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_inv
    mock_session.execute.return_value = mock_res

    # Mock no expired recovery, but active pending exists
    service.ai_repo.recover_expired_pending = AsyncMock(return_value=None)  # type: ignore[method-assign]
    active_summary = MagicMock()
    active_summary.id = uuid.uuid4()
    active_summary.generated_at = datetime(2026, 11, 4, 12, 0, 0, tzinfo=UTC)
    service.ai_repo.get_active_pending = AsyncMock(return_value=active_summary)  # type: ignore[method-assign]

    with pytest.raises(AISummaryInProgressError) as exc:
        await service._reserve_and_snapshot(
            session=mock_session,
            investigation_id=mock_inv.id,
            request=AISummaryGenerateRequest(),
            current_user=admin_user,
        )
    assert str(active_summary.id) in str(exc.value.details)
