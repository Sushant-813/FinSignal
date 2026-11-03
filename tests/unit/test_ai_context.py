"""Unit tests for Phase 10 EvidenceContextBuilder, dual fingerprinting, and canonical serialization."""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from finsignal.ai.context import EvidenceContextBuilder, to_canonical_json
from finsignal.investigations.models import (
    InvestigationEvidence,
    InvestigationTransaction,
)


def test_canonical_json_dump_determinism() -> None:
    """Keys are sorted, Decimals formatted as exact strings, datetimes formatted with microseconds and Z."""
    now = datetime(2026, 11, 4, 12, 0, 0, 123456, tzinfo=UTC)
    uid = uuid.UUID("11111111-2222-3333-4444-555555555555")

    dict_a = {
        "z": 1,
        "a": Decimal("100.50"),
        "m": now,
        "u": uid,
    }
    dict_b = {
        "u": uid,
        "m": now,
        "a": Decimal("100.50"),
        "z": 1,
    }

    dump_a = to_canonical_json(dict_a)
    dump_b = to_canonical_json(dict_b)

    assert dump_a == dump_b
    parsed = json.loads(dump_a)
    assert parsed["a"] == "100.50"
    assert parsed["m"] == "2026-11-04T12:00:00.123456Z"
    assert parsed["u"] == "11111111-2222-3333-4444-555555555555"


def test_dual_hash_isolation() -> None:
    """evidence_hash changes when data changes; context_hash changes when data or bounds change."""
    builder = EvidenceContextBuilder()
    inv_id = uuid.uuid4()
    now = datetime(2026, 11, 4, 10, 0, 0, tzinfo=UTC)

    # Mock investigation object
    mock_inv = MagicMock()
    mock_inv.id = inv_id
    mock_inv.status = "UNDER_REVIEW"
    mock_inv.priority = "HIGH"
    mock_inv.title = "High Risk Transfer"
    mock_inv.description = "Suspicious velocity across accounts"
    mock_inv.assigned_to = None
    mock_inv.created_at = now
    mock_inv.updated_at = now

    # Primary transaction association
    mock_assoc = MagicMock()
    mock_assoc.relationship_type = "PRIMARY"
    mock_assoc.transaction.id = uuid.uuid4()
    mock_assoc.transaction.amount = Decimal("9999.00")
    mock_assoc.transaction.currency = "USD"
    mock_assoc.transaction.occurred_at = now
    mock_assoc.transaction.account_id = uuid.uuid4()
    mock_assoc.transaction.counterparty_account_id = None
    mock_assoc.transaction.external_transaction_id = "EXT_1"
    mock_assoc.transaction.direction = "OUTBOUND"
    mock_assoc.transaction.transaction_type = "TRANSFER"
    mock_assoc.transaction.category = "WIRE"
    mock_assoc.transaction.payment_method = "ACH"
    mock_assoc.transaction.source_namespace = "CORE"

    mock_inv.transaction_associations = [mock_assoc]
    mock_inv.primary_association = mock_assoc
    empty_evidence: list[InvestigationEvidence] = []
    mock_inv.evidence = empty_evidence

    # Mock RiskAnalysis
    mock_risk = MagicMock()
    mock_risk.id = uuid.uuid4()
    mock_risk.score = Decimal("85.500")
    mock_risk.risk_level = "CRITICAL"
    mock_risk.model_version = "v1.0.0"
    mock_risk.config_version = "cfg_1"
    mock_risk.feature_vector_hash = "abc123hash"
    mock_risk.ml_anomaly_score = 0.92
    mock_risk.rule_score = 75.0
    mock_risk.created_at = now

    factor_mock = MagicMock()
    factor_mock.id = uuid.uuid4()
    factor_mock.factor_code = "high_velocity"
    factor_mock.factor_label = "High Velocity"
    factor_mock.severity = "HIGH"
    factor_mock.description = "Velocity is high"
    factor_mock.value_numeric = Decimal("4.5")
    factor_mock.value_text = None
    mock_risk.factors = [factor_mock]

    ev_hash1 = builder.compute_authoritative_evidence_hash(mock_inv, mock_risk)
    ctx1, ctx_hash1 = builder.build_bounded_context(
        mock_inv, mock_risk, max_items=50, max_bytes=65536
    )

    # Second call without changes must yield identical hashes
    ev_hash2 = builder.compute_authoritative_evidence_hash(mock_inv, mock_risk)
    ctx2, ctx_hash2 = builder.build_bounded_context(
        mock_inv, mock_risk, max_items=50, max_bytes=65536
    )

    assert ev_hash1 == ev_hash2
    assert ctx_hash1 == ctx_hash2

    # Now mutate risk score in evidence
    mock_risk.score = Decimal("95.000")
    ev_hash3 = builder.compute_authoritative_evidence_hash(mock_inv, mock_risk)
    ctx3, ctx_hash3 = builder.build_bounded_context(
        mock_inv, mock_risk, max_items=50, max_bytes=65536
    )

    # Both hashes must now change
    assert ev_hash3 != ev_hash1
    assert ctx_hash3 != ctx_hash1


def test_budget_truncation_evidence_count() -> None:
    """Evidence records exceeding max_items are truncated deterministically."""
    builder = EvidenceContextBuilder()
    inv_id = uuid.uuid4()
    now = datetime(2026, 11, 4, 10, 0, 0, tzinfo=UTC)

    mock_inv = MagicMock()
    mock_inv.id = inv_id
    mock_inv.status = "UNDER_REVIEW"
    mock_inv.priority = "MEDIUM"
    mock_inv.title = "Bulk Evidence"
    mock_inv.description = "Test"
    mock_inv.assigned_to = None
    mock_inv.created_at = now
    mock_inv.updated_at = now
    empty_associations: list[InvestigationTransaction] = []
    mock_inv.transaction_associations = empty_associations
    mock_inv.primary_association = None

    # Create 10 evidence items
    evidence_list = []
    for i in range(10):
        ev = MagicMock()
        ev.id = uuid.UUID(f"00000000-0000-0000-0000-{i:012d}")
        ev.evidence_type = "NOTE"
        ev.source_type = "INVESTIGATOR"
        ev.source_id = None
        ev.title = f"Evidence {i}"
        ev.description = f"Evidence item {i}"
        ev.created_at = datetime(2026, 11, 4, 10, i, 0, tzinfo=UTC)
        ev.payload = {"index": i}
        evidence_list.append(ev)
    mock_inv.evidence = evidence_list

    # Limit to 5 items
    ctx, ctx_hash = builder.build_bounded_context(
        mock_inv,
        latest_risk=None,
        max_items=5,
        max_bytes=65536,
    )

    assert ctx.context_metadata.total_evidence_count == 10
    assert ctx.context_metadata.included_evidence_count == 5
    assert ctx.context_metadata.omitted_evidence_count == 5
    assert len(ctx.evidence_items) == 5


def test_account_attributes_affect_authoritative_hash() -> None:
    """Mutating account status or account type materially alters the authoritative evidence hash."""
    builder = EvidenceContextBuilder()
    inv_id = uuid.uuid4()
    now = datetime(2026, 11, 4, 10, 0, 0, tzinfo=UTC)

    mock_inv = MagicMock()
    mock_inv.id = inv_id
    mock_inv.status = "UNDER_REVIEW"
    mock_inv.priority = "HIGH"
    mock_inv.assigned_to = None
    mock_inv.created_at = now
    empty_evidence: list[InvestigationEvidence] = []
    mock_inv.evidence = empty_evidence

    mock_account = MagicMock()
    mock_account.account_type = "CHECKING"
    mock_account.status = "ACTIVE"

    mock_assoc = MagicMock()
    mock_assoc.relationship_type = "PRIMARY"
    mock_assoc.transaction.id = uuid.uuid4()
    mock_assoc.transaction.amount = Decimal("5000.00")
    mock_assoc.transaction.currency = "USD"
    mock_assoc.transaction.occurred_at = now
    mock_assoc.transaction.account_id = uuid.uuid4()
    mock_assoc.transaction.account = mock_account
    mock_assoc.transaction.counterparty_account_id = None
    mock_assoc.transaction.external_transaction_id = "EXT_TX_1"
    mock_assoc.transaction.direction = "DEBIT"
    mock_assoc.transaction.transaction_type = "PURCHASE"
    mock_assoc.transaction.category = "RETAIL"
    mock_assoc.transaction.payment_method = "CARD"
    mock_assoc.transaction.source_namespace = "CORE"

    mock_inv.transaction_associations = [mock_assoc]
    mock_inv.primary_association = mock_assoc

    hash_active = builder.compute_authoritative_evidence_hash(
        mock_inv, latest_risk=None
    )

    # Mutate account status to FROZEN
    mock_account.status = "FROZEN"
    hash_frozen = builder.compute_authoritative_evidence_hash(
        mock_inv, latest_risk=None
    )
    assert hash_active != hash_frozen

    # Mutate account type to SAVINGS
    mock_account.account_type = "SAVINGS"
    hash_savings = builder.compute_authoritative_evidence_hash(
        mock_inv, latest_risk=None
    )
    assert hash_frozen != hash_savings
