"""Unit tests for Phase 10 MockLLMProvider fault simulation and deterministic generation."""

import uuid
from decimal import Decimal

import pytest

from finsignal.ai.context import ContextMetadata, InvestigationEvidenceContext
from finsignal.ai.providers.base import ProviderRequest
from finsignal.ai.providers.mock import MockLLMProvider, MockProviderError


@pytest.fixture
def sample_context() -> InvestigationEvidenceContext:
    """Provide a minimal valid context with a primary transaction and risk factor."""
    tx_id = uuid.uuid4()
    ev_id = uuid.uuid4()
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
                "id": uuid.uuid4(),
                "factor_code": "velocity_burst",
                "factor_label": "Velocity Burst",
                "severity": "CRITICAL",
                "description": "Unusually high transfer volume in 1 hour",
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
                "description": "Customer called about unauthorized login",
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


@pytest.mark.asyncio
async def test_mock_provider_deterministic_generation(
    sample_context: InvestigationEvidenceContext,
) -> None:
    """Mock provider returns valid parseable JSON strictly grounded in context citations."""
    provider = MockLLMProvider()
    request = ProviderRequest(
        system_prompt="System prompt",
        user_prompt="User prompt",
        context=sample_context,
        model="mock-v1",
        timeout_seconds=5.0,
    )

    resp = await provider.generate(request)
    assert resp.provider == "mock"
    assert resp.model == "mock-v1"
    assert "observed_facts" in resp.raw_content
    assert "derived_signals" in resp.raw_content
    assert str(sample_context.primary_transaction["id"]) in resp.raw_content


@pytest.mark.asyncio
async def test_mock_provider_simulate_timeout(
    sample_context: InvestigationEvidenceContext,
) -> None:
    """simulate_timeout triggers TimeoutError."""
    provider = MockLLMProvider(simulate_timeout=True)
    request = ProviderRequest(
        system_prompt="System prompt",
        user_prompt="User prompt",
        context=sample_context,
        model="mock-v1",
        timeout_seconds=1.0,
    )
    with pytest.raises(TimeoutError):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_mock_provider_simulate_provider_error(
    sample_context: InvestigationEvidenceContext,
) -> None:
    """simulate_provider_error triggers MockProviderError."""
    provider = MockLLMProvider(simulate_provider_error=True)
    request = ProviderRequest(
        system_prompt="System prompt",
        user_prompt="User prompt",
        context=sample_context,
        model="mock-v1",
        timeout_seconds=1.0,
    )
    with pytest.raises(MockProviderError):
        await provider.generate(request)


@pytest.mark.asyncio
async def test_mock_provider_simulate_invalid_json(
    sample_context: InvestigationEvidenceContext,
) -> None:
    """simulate_invalid_json returns malformed raw text."""
    provider = MockLLMProvider(simulate_invalid_json=True)
    request = ProviderRequest(
        system_prompt="System prompt",
        user_prompt="User prompt",
        context=sample_context,
        model="mock-v1",
        timeout_seconds=1.0,
    )
    resp = await provider.generate(request)
    assert "MALFORMED_NON_JSON_RESPONSE" in resp.raw_content
