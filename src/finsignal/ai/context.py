"""Evidence context aggregation, canonicalization, budget enforcement, and dual-fingerprint engine."""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from finsignal.common.exceptions import FinSignalError
from finsignal.investigations.models import (
    Investigation,
    InvestigationEvidence,
    InvestigationTransaction,
)
from finsignal.risk.models import RiskAnalysis

SEVERITY_RANK: dict[str, int] = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}


class ContextBudgetExceededError(FinSignalError):
    """Raised when mandatory case facts exceed the configured maximum context byte budget."""

    def __init__(
        self,
        message: str = "Mandatory investigation context exceeds maximum allowed byte budget.",
        code: str = "CONTEXT_BUDGET_EXCEEDED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=422, details=details)


def canonical_serializer(obj: Any) -> Any:
    """Deterministic JSON serializer supporting Decimals, UUIDs, datetimes, and dates."""
    if isinstance(obj, Decimal):
        # Exact fixed-point format without float conversion or scientific notation
        return format(obj, "f")
    if isinstance(obj, (datetime, date)):
        dt = obj if isinstance(obj, datetime) else datetime.combine(obj, time.min)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(obj, uuid.UUID):
        return str(obj).lower()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_canonical_json(data: Any) -> str:
    """Serialize payload to canonical JSON with sorted keys and compact separators."""
    return json.dumps(
        data,
        default=canonical_serializer,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


@dataclass
class ContextMetadata:
    """Audit metadata describing context construction, bounds, and truncation."""

    total_evidence_count: int
    included_evidence_count: int
    omitted_evidence_count: int
    omitted_evidence_types: list[str] = field(default_factory=list)


@dataclass
class InvestigationEvidenceContext:
    """Structured, bounded case context ready for model input and fingerprinting."""

    investigation_id: uuid.UUID
    case_metadata: dict[str, Any]
    primary_transaction: dict[str, Any]
    latest_risk_analysis: dict[str, Any] | None
    risk_factors: list[dict[str, Any]]
    related_transactions: list[dict[str, Any]]
    evidence_items: list[dict[str, Any]]
    context_metadata: ContextMetadata

    def to_dict(self) -> dict[str, Any]:
        """Convert context container to a serializable dictionary."""
        return {
            "investigation_id": self.investigation_id,
            "case_metadata": self.case_metadata,
            "primary_transaction": self.primary_transaction,
            "latest_risk_analysis": self.latest_risk_analysis,
            "risk_factors": self.risk_factors,
            "related_transactions": self.related_transactions,
            "evidence_items": self.evidence_items,
            "context_metadata": {
                "total_evidence_count": self.context_metadata.total_evidence_count,
                "included_evidence_count": self.context_metadata.included_evidence_count,
                "omitted_evidence_count": self.context_metadata.omitted_evidence_count,
                "omitted_evidence_types": self.context_metadata.omitted_evidence_types,
            },
        }


class EvidenceContextBuilder:
    """Constructs canonical case contexts, enforces byte/count budgets, and computes dual fingerprints."""

    def compute_authoritative_evidence_hash(
        self,
        investigation: Investigation,
        latest_risk: RiskAnalysis | None,
    ) -> str:
        """Compute the complete authoritative SHA-256 fingerprint of the entire investigation case.

        Covers:
        - Investigation case attributes
        - Primary transaction attributes
        - All linked related transactions
        - Latest risk score and all risk factors
        - ALL attached evidence items, descriptions, and payloads (untruncated)
        """
        payload = self._build_full_untruncated_payload(investigation, latest_risk)
        canonical_str = to_canonical_json(payload)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def build_bounded_context(
        self,
        investigation: Investigation,
        latest_risk: RiskAnalysis | None,
        max_items: int = 50,
        max_bytes: int = 65536,
    ) -> tuple[InvestigationEvidenceContext, str]:
        """Build the bounded, prioritized prompt context and compute its context_hash.

        Guarantees:
        - Mandatory facts (primary tx, risk score, factors) are always included.
        - Raises ContextBudgetExceededError if mandatory facts alone exceed max_bytes.
        - Lower-priority evidence is omitted deterministically when limits are reached.
        - Returns (context, context_hash).
        """
        # 1. Mandatory Core Components
        primary_tx_dict = self._serialize_primary_transaction(investigation)
        risk_dict, factors_list = self._serialize_risk(latest_risk)
        case_meta = {
            "id": investigation.id,
            "status": investigation.status,
            "priority": investigation.priority,
            "assigned_to": investigation.assigned_to,
            "created_at": investigation.created_at,
        }

        mandatory_payload = {
            "investigation_id": investigation.id,
            "case_metadata": case_meta,
            "primary_transaction": primary_tx_dict,
            "latest_risk_analysis": risk_dict,
            "risk_factors": factors_list,
        }
        mandatory_bytes = len(to_canonical_json(mandatory_payload).encode("utf-8"))
        if mandatory_bytes > max_bytes:
            raise ContextBudgetExceededError(
                f"Mandatory investigation context ({mandatory_bytes} bytes) exceeds "
                f"configured maximum budget of {max_bytes} bytes.",
                details={"mandatory_bytes": mandatory_bytes, "max_bytes": max_bytes},
            )

        # 2. Prioritized Optional Components
        # Sort related transactions deterministically: occurred_at DESC, id ASC
        related_tx_candidates = self._get_sorted_related_transactions(investigation)
        # Sort evidence items deterministically: created_at ASC, id ASC
        all_evidence = sorted(
            list(investigation.evidence or []),
            key=lambda e: (e.created_at, e.id),
        )

        total_evidence_count = len(all_evidence)
        included_evidence: list[dict[str, Any]] = []
        omitted_types: set[str] = set()

        # Check if full payload fits
        candidate_evidence_dicts = [
            self._serialize_evidence_item(e) for e in all_evidence
        ]
        for ev_dict in candidate_evidence_dicts:
            if len(included_evidence) >= max_items:
                # Exceeded item count limit
                omitted_types.add(ev_dict["evidence_type"])
                continue

            test_included = [*included_evidence, ev_dict]
            test_metadata = {
                "total_evidence_count": total_evidence_count,
                "included_evidence_count": len(test_included),
                "omitted_evidence_count": total_evidence_count - len(test_included),
                "omitted_evidence_types": sorted(list(omitted_types)),
            }
            test_full = {
                **mandatory_payload,
                "related_transactions": related_tx_candidates,
                "evidence_items": test_included,
                "context_metadata": test_metadata,
            }
            test_bytes = len(to_canonical_json(test_full).encode("utf-8"))
            if test_bytes <= max_bytes:
                included_evidence.append(ev_dict)
            else:
                omitted_types.add(ev_dict["evidence_type"])

        # Any remaining evidence items not evaluated because of item cap are marked omitted
        for ev in all_evidence[len(included_evidence) :]:
            omitted_types.add(ev.evidence_type)

        omitted_count = total_evidence_count - len(included_evidence)
        metadata = ContextMetadata(
            total_evidence_count=total_evidence_count,
            included_evidence_count=len(included_evidence),
            omitted_evidence_count=omitted_count,
            omitted_evidence_types=sorted(list(omitted_types)),
        )

        context = InvestigationEvidenceContext(
            investigation_id=investigation.id,
            case_metadata=case_meta,
            primary_transaction=primary_tx_dict,
            latest_risk_analysis=risk_dict,
            risk_factors=factors_list,
            related_transactions=related_tx_candidates,
            evidence_items=included_evidence,
            context_metadata=metadata,
        )

        context_json = to_canonical_json(context.to_dict())
        context_hash = hashlib.sha256(context_json.encode("utf-8")).hexdigest()
        return context, context_hash

    def _build_full_untruncated_payload(
        self,
        investigation: Investigation,
        latest_risk: RiskAnalysis | None,
    ) -> dict[str, Any]:
        """Construct the complete, untruncated dictionary representation for authoritative hashing."""
        primary_tx_dict = self._serialize_primary_transaction(investigation)
        risk_dict, factors_list = self._serialize_risk(latest_risk)
        related_tx_list = self._get_sorted_related_transactions(investigation)

        all_evidence = sorted(
            list(investigation.evidence or []),
            key=lambda e: (e.created_at, e.id),
        )
        evidence_list = [self._serialize_evidence_item(e) for e in all_evidence]

        return {
            "investigation_id": investigation.id,
            "case_metadata": {
                "id": investigation.id,
                "status": investigation.status,
                "priority": investigation.priority,
                "assigned_to": investigation.assigned_to,
                "created_at": investigation.created_at,
            },
            "primary_transaction": primary_tx_dict,
            "latest_risk_analysis": risk_dict,
            "risk_factors": factors_list,
            "related_transactions": related_tx_list,
            "evidence_items": evidence_list,
        }

    def _serialize_primary_transaction(
        self, investigation: Investigation
    ) -> dict[str, Any]:
        """Extract authoritative primary transaction attributes including account status and type."""
        primary_assoc = investigation.primary_association
        if primary_assoc is None and investigation.transaction_associations:
            primary_assoc = next(
                (
                    a
                    for a in investigation.transaction_associations
                    if a.relationship_type == "PRIMARY"
                ),
                None,
            )
        if primary_assoc is None or primary_assoc.transaction is None:
            return {}

        tx = primary_assoc.transaction
        account = getattr(tx, "account", None)
        account_type: str | None = None
        account_status: str | None = None
        if account is not None:
            raw_type = getattr(account, "account_type", None)
            if isinstance(raw_type, str):
                account_type = raw_type
            raw_status = getattr(account, "status", None)
            if isinstance(raw_status, str):
                account_status = raw_status

        return {
            "id": tx.id,
            "external_transaction_id": tx.external_transaction_id,
            "account_id": tx.account_id,
            "account_type": account_type,
            "account_status": account_status,
            "counterparty_account_id": tx.counterparty_account_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "direction": tx.direction,
            "transaction_type": tx.transaction_type,
            "category": tx.category,
            "payment_method": tx.payment_method,
            "source_namespace": tx.source_namespace,
            "occurred_at": tx.occurred_at,
        }

    def _get_sorted_related_transactions(
        self, investigation: Investigation
    ) -> list[dict[str, Any]]:
        """Extract and deterministically sort all linked RELATED transactions with account context."""
        related_assocs: list[InvestigationTransaction] = [
            a
            for a in (investigation.transaction_associations or [])
            if a.relationship_type == "RELATED" and a.transaction is not None
        ]
        # Sort by occurred_at ASC, transaction_id ASC
        related_assocs.sort(
            key=lambda a: (
                a.transaction.occurred_at if a.transaction else datetime.min,
                a.transaction_id,
            )
        )

        items: list[dict[str, Any]] = []
        for assoc in related_assocs:
            tx = assoc.transaction
            assert tx is not None
            account = getattr(tx, "account", None)
            account_type: str | None = None
            account_status: str | None = None
            if account is not None:
                raw_type = getattr(account, "account_type", None)
                if isinstance(raw_type, str):
                    account_type = raw_type
                raw_status = getattr(account, "status", None)
                if isinstance(raw_status, str):
                    account_status = raw_status

            items.append(
                {
                    "transaction_id": tx.id,
                    "relationship_type": assoc.relationship_type,
                    "account_id": tx.account_id,
                    "account_type": account_type,
                    "account_status": account_status,
                    "counterparty_account_id": tx.counterparty_account_id,
                    "amount": tx.amount,
                    "currency": tx.currency,
                    "direction": tx.direction,
                    "occurred_at": tx.occurred_at,
                }
            )
        return items

    def _serialize_risk(
        self,
        latest_risk: RiskAnalysis | None,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Extract latest risk analysis and deterministically sorted risk factors."""
        if latest_risk is None:
            return None, []

        model_ver = "UNKNOWN"
        if latest_risk.model_version is not None:
            if hasattr(latest_risk.model_version, "version"):
                model_ver = str(latest_risk.model_version.version)
            else:
                model_ver = str(latest_risk.model_version)

        risk_dict = {
            "id": latest_risk.id,
            "score": latest_risk.score,
            "risk_level": latest_risk.risk_level,
            "model_version": model_ver,
            "config_version": latest_risk.config_version,
            "feature_vector_hash": latest_risk.feature_vector_hash,
            "ml_anomaly_score": latest_risk.ml_anomaly_score,
            "rule_score": latest_risk.rule_score,
            "created_at": latest_risk.created_at,
        }

        # Sort factors by (severity_rank DESC, factor_code ASC)
        factors = list(latest_risk.factors or [])
        factors.sort(
            key=lambda f: (
                -SEVERITY_RANK.get(f.severity, 0),
                f.factor_code,
                f.id,
            )
        )
        factors_list: list[dict[str, Any]] = []
        for f in factors:
            factors_list.append(
                {
                    "id": f.id,
                    "factor_code": f.factor_code,
                    "factor_label": f.factor_label,
                    "severity": f.severity,
                    "description": f.description,
                    "value_numeric": f.value_numeric,
                    "value_text": f.value_text,
                }
            )
        return risk_dict, factors_list

    def _serialize_evidence_item(
        self, evidence: InvestigationEvidence
    ) -> dict[str, Any]:
        """Extract authoritative attributes for an evidence record."""
        return {
            "id": evidence.id,
            "evidence_type": evidence.evidence_type,
            "source_type": evidence.source_type,
            "source_id": evidence.source_id,
            "title": evidence.title,
            "description": evidence.description,
            "payload": evidence.payload,
            "created_at": evidence.created_at,
        }
