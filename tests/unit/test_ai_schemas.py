"""Unit tests for Phase 10 AI schemas, validation rules, and forbid-extra constraints."""

import uuid

import pytest
from pydantic import ValidationError

from finsignal.ai.schemas import (
    AISummaryGenerateRequest,
    AISummaryOutput,
    EvidenceReference,
    GroundedObservation,
)


def test_grounded_observation_valid() -> None:
    """Valid observation citing verified entity UUIDs."""
    ev_id = uuid.uuid4()
    obs = GroundedObservation(
        claim="Transaction occurred at an unusual time of day.",
        evidence_ids=[ev_id],
    )
    assert obs.claim == "Transaction occurred at an unusual time of day."
    assert obs.evidence_ids == [ev_id]


def test_grounded_observation_empty_citations_rejected() -> None:
    """GroundedObservation requires at least one citation (min_length=1)."""
    with pytest.raises(ValidationError):
        GroundedObservation(
            claim="Unfounded claim with no evidence",
            evidence_ids=[],
        )


def test_grounded_observation_extra_forbidden() -> None:
    """extra='forbid' rejects extra fields on GroundedObservation and EvidenceReference."""
    with pytest.raises(ValidationError):
        EvidenceReference(
            source_type="TRANSACTION",
            source_id=uuid.uuid4(),
            extra_field="rejected",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        GroundedObservation(
            claim="Valid claim",
            evidence_ids=[uuid.uuid4()],
            extra_field="rejected",  # type: ignore[call-arg]
        )


def test_ai_summary_output_valid() -> None:
    """Valid complete AI summary output structure matching Phase 10 taxonomy."""
    ev_id = uuid.uuid4()
    out = AISummaryOutput(
        executive_summary="Executive summary of suspicious transaction velocity.",
        observed_facts=[
            GroundedObservation(
                claim="Velocity is 400% above peer average.",
                evidence_ids=[ev_id],
            )
        ],
        derived_signals=[
            GroundedObservation(
                claim="High deviation from historical pattern.",
                evidence_ids=[ev_id],
            )
        ],
        potential_interpretations=["Account takeover hypothesis."],
        uncertainties_and_limitations=["Device IP geolocation could not be resolved."],
    )
    assert len(out.observed_facts) == 1
    assert len(out.derived_signals) == 1
    assert out.potential_interpretations == ["Account takeover hypothesis."]
    assert out.uncertainties_and_limitations == [
        "Device IP geolocation could not be resolved."
    ]


def test_ai_summary_output_extra_forbidden() -> None:
    """extra='forbid' prevents unvalidated LLM output injection."""
    with pytest.raises(ValidationError):
        AISummaryOutput(
            executive_summary="Test",
            observed_facts=[
                GroundedObservation(claim="Test claim", evidence_ids=[uuid.uuid4()])
            ],
            hallucinated_key="malicious_payload",  # type: ignore[call-arg]
        )


def test_ai_summary_generate_request_defaults() -> None:
    """force_refresh defaults to False and forbids extra fields."""
    req = AISummaryGenerateRequest()
    assert req.force_refresh is False

    req2 = AISummaryGenerateRequest(force_refresh=True)
    assert req2.force_refresh is True

    with pytest.raises(ValidationError):
        AISummaryGenerateRequest(unknown="field")  # type: ignore[call-arg]
