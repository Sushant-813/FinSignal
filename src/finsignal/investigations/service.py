"""Service layer implementing core business logic, lifecycle transitions, authorization,
and transactional invariants for Phase 9 Investigation & Evidence.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.audit.models import AuditEvent
from finsignal.common.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from finsignal.investigations.models import (
    Investigation,
    InvestigationEvidence,
    InvestigationTransaction,
)
from finsignal.investigations.repository import InvestigationRepository
from finsignal.investigations.schemas import (
    EVIDENCE_TYPE_SOURCE_MAPPING,
    EvidenceSourceType,
    EvidenceType,
    InvestigationCreateRequest,
    InvestigationDetailResponse,
    InvestigationEvidenceCreateRequest,
    InvestigationEvidenceListResponse,
    InvestigationEvidenceResponse,
    InvestigationLatestRiskDTO,
    InvestigationListResponse,
    InvestigationPatchRequest,
    InvestigationPrimaryTransactionDTO,
    InvestigationPriority,
    InvestigationRelatedTransactionAddRequest,
    InvestigationRelationshipType,
    InvestigationResolution,
    InvestigationResolveRequest,
    InvestigationStatus,
    InvestigationSummaryItem,
    InvestigationTransactionItem,
    InvestigationTransactionsListResponse,
)
from finsignal.risk.models import RiskAnalysis
from finsignal.transactions.models import Transaction
from finsignal.users.models import User


class InvestigationService:
    """Orchestrates investigation workflow, RBAC, evidence immutability, and audit logging."""

    def __init__(self, repo: InvestigationRepository | None = None) -> None:
        self.repo = repo or InvestigationRepository()

    # -------------------------------------------------------------------------
    # Investigation Creation
    # -------------------------------------------------------------------------
    async def create_investigation(
        self,
        session: AsyncSession,
        request: InvestigationCreateRequest,
        current_user: User,
    ) -> InvestigationDetailResponse:
        """Create a new unassigned investigation atomically linked to its primary transaction.

        Guarantees:
        - Accessible to ADMIN, ANALYST, and INVESTIGATOR roles.
        - Primary transaction existence validated.
        - Atomically inserts: Investigation, PRIMARY InvestigationTransaction, and INVESTIGATION_CREATED AuditEvent.
        - Exactly one PRIMARY transaction association guaranteed upon commit.
        """
        self._require_roles(current_user, {"ADMIN", "ANALYST", "INVESTIGATOR"})

        tx = await self.repo.get_transaction(session, request.transaction_id)
        if tx is None:
            raise NotFoundError(
                f"Transaction '{request.transaction_id}' was not found.",
                code="TRANSACTION_NOT_FOUND",
            )

        inv_id = uuid.uuid4()
        investigation = Investigation(
            id=inv_id,
            status=InvestigationStatus.OPEN.value,
            priority=request.priority.value,
            assigned_to=None,
            resolution=None,
            resolution_notes=None,
        )
        primary_link = InvestigationTransaction(
            investigation_id=inv_id,
            transaction_id=tx.id,
            relationship_type=InvestigationRelationshipType.PRIMARY.value,
        )

        await self.repo.create_atomic(session, investigation, primary_link)

        # Transactional audit event
        audit_event = AuditEvent(
            id=uuid.uuid4(),
            actor_user_id=current_user.id,
            action="INVESTIGATION_CREATED",
            entity_type="investigation",
            entity_id=inv_id,
            metadata_={
                "transaction_id": str(tx.id),
                "priority": investigation.priority,
            },
        )
        session.add(audit_event)
        await session.flush()

        return await self.get_investigation_workspace(
            session=session,
            investigation_id=inv_id,
            current_user=current_user,
        )

    # -------------------------------------------------------------------------
    # Investigation Workspace / Detail
    # -------------------------------------------------------------------------
    async def get_investigation_workspace(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        current_user: User,
    ) -> InvestigationDetailResponse:
        """Retrieve complete investigation workspace detail without N+1 query overhead."""
        self._require_roles(current_user, {"ADMIN", "ANALYST", "INVESTIGATOR"})

        inv = await self.repo.get_workspace_detail(session, investigation_id)
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        primary_assoc = inv.primary_association
        if primary_assoc is None:
            primary_assoc = next(
                (
                    a
                    for a in inv.transaction_associations
                    if a.relationship_type
                    == InvestigationRelationshipType.PRIMARY.value
                ),
                None,
            )
        if primary_assoc is None or primary_assoc.transaction is None:
            raise NotFoundError(
                f"Primary transaction association for investigation '{investigation_id}' not found.",
                code="PRIMARY_TRANSACTION_NOT_FOUND",
            )

        primary_tx = primary_assoc.transaction
        latest_risk = await self.repo.get_latest_risk_for_transaction(
            session, primary_tx.id
        )

        return self._to_workspace_response(inv, primary_tx, latest_risk)

    # -------------------------------------------------------------------------
    # Investigation Listing & Filtering
    # -------------------------------------------------------------------------
    async def list_investigations(
        self,
        session: AsyncSession,
        page: int,
        page_size: int,
        status: InvestigationStatus | None,
        priority: InvestigationPriority | None,
        assigned_to: uuid.UUID | None,
        unassigned: bool | None,
        current_user: User,
    ) -> InvestigationListResponse:
        """Query paginated investigations with dynamic filtering and deterministic ordering."""
        self._require_roles(current_user, {"ADMIN", "ANALYST", "INVESTIGATOR"})

        if assigned_to is not None and unassigned is True:
            raise ValidationError(
                "Cannot combine assigned_to filter with unassigned=true.",
                code="FILTER_CONFLICT",
            )

        items, total, total_pages = await self.repo.list_investigations(
            session=session,
            page=page,
            page_size=page_size,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            unassigned=unassigned,
        )

        summary_items: list[InvestigationSummaryItem] = []
        for inv in items:
            primary_assoc = inv.primary_association
            if primary_assoc is None or primary_assoc.transaction is None:
                continue
            summary_items.append(
                InvestigationSummaryItem(
                    id=inv.id,
                    status=InvestigationStatus(inv.status),
                    priority=InvestigationPriority(inv.priority),
                    assigned_to=inv.assigned_to,
                    primary_transaction_id=primary_assoc.transaction_id,
                    account_id=primary_assoc.transaction.account_id,
                    resolution=InvestigationResolution(inv.resolution)
                    if inv.resolution
                    else None,
                    created_at=inv.created_at,
                    updated_at=inv.updated_at,
                )
            )

        return InvestigationListResponse(
            items=summary_items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    # -------------------------------------------------------------------------
    # Investigation Mutation (PATCH)
    # -------------------------------------------------------------------------
    async def patch_investigation(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        patch: InvestigationPatchRequest,
        current_user: User,
    ) -> InvestigationDetailResponse:
        """Apply permitted mutations (assignment, priority, OPEN->UNDER_REVIEW status).

        Uses SELECT ... FOR UPDATE row-level lock and enforces RBAC and race distinction.
        """
        self._require_roles(current_user, {"ADMIN", "INVESTIGATOR"})

        # Check pre-lock state for investigators to distinguish explicit peer take (403)
        # from concurrent self-assignment race loser (409)
        fields_set = patch.model_fields_set
        if (
            current_user.role == "INVESTIGATOR"
            and "assigned_to" in fields_set
            and patch.assigned_to == current_user.id
        ):
            pre_lock = await self.repo.get_by_id(session, investigation_id)
            if pre_lock is None:
                raise NotFoundError(
                    f"Investigation '{investigation_id}' was not found.",
                    code="INVESTIGATION_NOT_FOUND",
                )
            if (
                pre_lock.assigned_to is not None
                and pre_lock.assigned_to != current_user.id
            ):
                raise AuthorizationError(
                    "Cannot take an investigation assigned to another investigator.",
                    code="FORBIDDEN",
                )

        inv = await self.repo.get_for_update(session, investigation_id)
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        if inv.status == InvestigationStatus.RESOLVED.value:
            raise ConflictError(
                "Resolved investigations are immutable.",
                code="INVESTIGATION_ALREADY_RESOLVED",
            )

        # 1. Assignment Mutation
        if "assigned_to" in fields_set:
            await self._handle_assignment(
                session=session,
                inv=inv,
                target_user_id=patch.assigned_to,
                current_user=current_user,
            )

        # 2. Priority Mutation
        if "priority" in fields_set and patch.priority is not None:
            self._handle_priority_change(
                session=session,
                inv=inv,
                target_priority=patch.priority,
                current_user=current_user,
            )

        # 3. Status Mutation (only OPEN -> UNDER_REVIEW supported via PATCH)
        if "status" in fields_set and patch.status is not None:
            self._handle_status_transition(
                session=session,
                inv=inv,
                target_status=patch.status,
                current_user=current_user,
            )

        await session.flush()
        return await self.get_investigation_workspace(
            session=session,
            investigation_id=inv.id,
            current_user=current_user,
        )

    # -------------------------------------------------------------------------
    # Investigation Resolution
    # -------------------------------------------------------------------------
    async def resolve_investigation(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        request: InvestigationResolveRequest,
        current_user: User,
    ) -> InvestigationDetailResponse:
        """Explicitly resolve an investigation in UNDER_REVIEW status.

        Guarantees:
        - Row-level lock acquired via SELECT ... FOR UPDATE.
        - Only ADMIN or assigned INVESTIGATOR may resolve.
        - Must be in UNDER_REVIEW state.
        - Resolved state becomes permanently immutable.
        - Emits exactly one INVESTIGATION_RESOLVED audit event.
        """
        self._require_roles(current_user, {"ADMIN", "INVESTIGATOR"})

        inv = await self.repo.get_for_update(session, investigation_id)
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        if inv.status == InvestigationStatus.RESOLVED.value:
            raise ConflictError(
                "Investigation is already resolved.",
                code="INVESTIGATION_ALREADY_RESOLVED",
            )

        if inv.status != InvestigationStatus.UNDER_REVIEW.value:
            raise ConflictError(
                f"Investigation must be in UNDER_REVIEW status to resolve, currently {inv.status}.",
                code="INVALID_LIFECYCLE_TRANSITION",
            )

        if current_user.role == "INVESTIGATOR" and inv.assigned_to != current_user.id:
            raise AuthorizationError(
                "Investigators can only resolve investigations assigned to themselves.",
                code="FORBIDDEN",
            )

        notes = request.resolution_notes.strip()
        if not notes:
            raise ValidationError(
                "Resolution notes must contain meaningful non-whitespace characters.",
                code="INVALID_RESOLUTION_NOTES",
            )

        inv.status = InvestigationStatus.RESOLVED.value
        inv.resolution = request.resolution.value
        inv.resolution_notes = notes

        # Exactly one audit event representing resolution
        audit_event = AuditEvent(
            id=uuid.uuid4(),
            actor_user_id=current_user.id,
            action="INVESTIGATION_RESOLVED",
            entity_type="investigation",
            entity_id=inv.id,
            metadata_={
                "resolution": inv.resolution,
                "resolution_notes": inv.resolution_notes,
            },
        )
        session.add(audit_event)
        await session.flush()

        return await self.get_investigation_workspace(
            session=session,
            investigation_id=inv.id,
            current_user=current_user,
        )

    # -------------------------------------------------------------------------
    # Related Transactions Management
    # -------------------------------------------------------------------------
    async def get_investigation_transactions(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        current_user: User,
    ) -> InvestigationTransactionsListResponse:
        """Retrieve all transactions associated with an investigation."""
        self._require_roles(current_user, {"ADMIN", "ANALYST", "INVESTIGATOR"})

        inv = await self.repo.get_by_id(session, investigation_id)
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        links = await self.repo.get_transaction_links(session, investigation_id)
        items: list[InvestigationTransactionItem] = []
        for link in links:
            tx = link.transaction
            if tx is not None:
                items.append(
                    InvestigationTransactionItem(
                        transaction_id=link.transaction_id,
                        relationship_type=InvestigationRelationshipType(
                            link.relationship_type
                        ),
                        account_id=tx.account_id,
                        amount=str(tx.amount),
                        currency=tx.currency,
                        direction=tx.direction,
                        occurred_at=tx.occurred_at,
                        created_at=link.created_at,
                    )
                )

        return InvestigationTransactionsListResponse(
            investigation_id=investigation_id,
            items=items,
        )

    async def add_related_transaction(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        request: InvestigationRelatedTransactionAddRequest,
        current_user: User,
    ) -> InvestigationTransactionItem:
        """Associate a related transaction satisfying the strict 4-way 1-hop scope."""
        self._require_roles(current_user, {"ADMIN", "INVESTIGATOR"})

        inv = await self.repo.get_workspace_detail(session, investigation_id)
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        if inv.status == InvestigationStatus.RESOLVED.value:
            raise ConflictError(
                "Cannot link transactions to a resolved investigation.",
                code="INVESTIGATION_ALREADY_RESOLVED",
            )

        if current_user.role == "INVESTIGATOR" and inv.assigned_to != current_user.id:
            raise AuthorizationError(
                "Investigators can only link transactions on their assigned investigations.",
                code="FORBIDDEN",
            )

        target_tx = await self.repo.get_transaction(session, request.transaction_id)
        if target_tx is None:
            raise NotFoundError(
                f"Transaction '{request.transaction_id}' was not found.",
                code="TRANSACTION_NOT_FOUND",
            )

        # Duplicate association check
        is_already_linked = await self.repo.is_transaction_linked(
            session, investigation_id, target_tx.id
        )
        if is_already_linked:
            raise ConflictError(
                f"Transaction '{request.transaction_id}' is already linked to this investigation.",
                code="TRANSACTION_ALREADY_LINKED",
            )

        # Primary transaction relationship and 1-hop scope verification
        primary_assoc = inv.primary_association
        if primary_assoc is None:
            primary_assoc = next(
                (
                    a
                    for a in inv.transaction_associations
                    if a.relationship_type
                    == InvestigationRelationshipType.PRIMARY.value
                ),
                None,
            )
        if primary_assoc is None or primary_assoc.transaction is None:
            raise NotFoundError(
                f"Primary transaction association for investigation '{investigation_id}' not found.",
                code="PRIMARY_TRANSACTION_NOT_FOUND",
            )
        primary_tx = primary_assoc.transaction

        # 1. Namespace boundary check
        if target_tx.source_namespace != primary_tx.source_namespace:
            raise ValidationError(
                f"Target transaction namespace '{target_tx.source_namespace}' does not match "
                f"primary transaction namespace '{primary_tx.source_namespace}'.",
                code="NAMESPACE_MISMATCH",
            )

        # 2. Strict 4-way 1-hop matching condition check
        # Condition 1: Target account_id == Primary account_id
        c1 = target_tx.account_id == primary_tx.account_id
        # Condition 2: Target account_id == Primary counterparty_account_id
        c2 = (
            primary_tx.counterparty_account_id is not None
            and target_tx.account_id == primary_tx.counterparty_account_id
        )
        # Condition 3: Target counterparty_account_id == Primary account_id
        c3 = (
            target_tx.counterparty_account_id is not None
            and target_tx.counterparty_account_id == primary_tx.account_id
        )
        # Condition 4: Both counterparty_account_id non-null and equal
        c4 = (
            primary_tx.counterparty_account_id is not None
            and target_tx.counterparty_account_id is not None
            and target_tx.counterparty_account_id == primary_tx.counterparty_account_id
        )

        if not (c1 or c2 or c3 or c4):
            raise ValidationError(
                "Transaction does not satisfy the direct 1-hop relationship condition with the primary transaction.",
                code="TRANSACTION_NOT_RELATED",
            )

        new_link = InvestigationTransaction(
            investigation_id=inv.id,
            transaction_id=target_tx.id,
            relationship_type=InvestigationRelationshipType.RELATED.value,
            created_at=datetime.now(UTC),
        )
        await self.repo.add_transaction_link(session, new_link)

        # Transactional audit event
        audit_event = AuditEvent(
            id=uuid.uuid4(),
            actor_user_id=current_user.id,
            action="INVESTIGATION_TRANSACTION_LINKED",
            entity_type="investigation",
            entity_id=inv.id,
            metadata_={
                "transaction_id": str(target_tx.id),
                "relationship_type": InvestigationRelationshipType.RELATED.value,
            },
        )
        session.add(audit_event)
        await session.flush()

        return InvestigationTransactionItem(
            transaction_id=new_link.transaction_id,
            relationship_type=InvestigationRelationshipType.RELATED,
            account_id=target_tx.account_id,
            amount=str(target_tx.amount),
            currency=target_tx.currency,
            direction=target_tx.direction,
            occurred_at=target_tx.occurred_at,
            created_at=new_link.created_at,
        )

    # -------------------------------------------------------------------------
    # Evidence Assembly & Validation
    # -------------------------------------------------------------------------
    async def list_evidence(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        page: int,
        page_size: int,
        current_user: User,
    ) -> InvestigationEvidenceListResponse:
        """Query paginated evidence records with deterministic ordering."""
        self._require_roles(current_user, {"ADMIN", "ANALYST", "INVESTIGATOR"})

        inv = await self.repo.get_by_id(session, investigation_id)
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        items, total, total_pages = await self.repo.list_evidence(
            session=session,
            investigation_id=investigation_id,
            page=page,
            page_size=page_size,
        )

        dtos = [
            InvestigationEvidenceResponse(
                id=ev.id,
                investigation_id=ev.investigation_id,
                evidence_type=EvidenceType(ev.evidence_type),
                source_type=EvidenceSourceType(ev.source_type),
                source_id=ev.source_id,
                title=ev.title,
                description=ev.description,
                payload=ev.payload,
                created_at=ev.created_at,
            )
            for ev in items
        ]

        return InvestigationEvidenceListResponse(
            items=dtos,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def attach_evidence(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        request: InvestigationEvidenceCreateRequest,
        current_user: User,
    ) -> InvestigationEvidenceResponse:
        """Validate source authority, construct immutable snapshot, and persist evidence record."""
        self._require_roles(current_user, {"ADMIN", "INVESTIGATOR"})

        inv = await self.repo.get_workspace_detail(session, investigation_id)
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        if inv.status == InvestigationStatus.RESOLVED.value:
            raise ConflictError(
                "Cannot attach evidence to a resolved investigation.",
                code="INVESTIGATION_ALREADY_RESOLVED",
            )

        if current_user.role == "INVESTIGATOR" and inv.assigned_to != current_user.id:
            raise AuthorizationError(
                "Investigators can only attach evidence to their assigned investigations.",
                code="FORBIDDEN",
            )

        # Enforce exact evidence_type / source_type pairing
        expected_source_type = EVIDENCE_TYPE_SOURCE_MAPPING.get(request.evidence_type)
        if expected_source_type != request.source_type:
            raise ValidationError(
                f"Evidence type '{request.evidence_type.value}' requires source_type '{expected_source_type.value if expected_source_type else 'UNKNOWN'}', got '{request.source_type.value}'.",
                code="INVALID_EVIDENCE_SOURCE_PAIR",
            )

        # Source consistency check
        if request.evidence_type == EvidenceType.USER_NOTE:
            if request.source_id is not None:
                raise ValidationError(
                    "USER_NOTE evidence must have a null source_id.",
                    code="INVALID_EVIDENCE_SOURCE_ID",
                )
        elif request.source_id is None:
            raise ValidationError(
                f"Evidence type '{request.evidence_type.value}' requires a non-null source_id.",
                code="MISSING_EVIDENCE_SOURCE_ID",
            )

        # Authoritative snapshot construction based on validated source entity
        snapshot_payload = await self._build_evidence_snapshot(
            session=session,
            inv=inv,
            request=request,
        )

        evidence = InvestigationEvidence(
            id=uuid.uuid4(),
            investigation_id=inv.id,
            evidence_type=request.evidence_type.value,
            source_type=request.source_type.value,
            source_id=request.source_id,
            title=request.title,
            description=request.description,
            payload=snapshot_payload,
            created_at=datetime.now(UTC),
        )
        await self.repo.add_evidence(session, evidence)

        # Transactional audit event
        audit_event = AuditEvent(
            id=uuid.uuid4(),
            actor_user_id=current_user.id,
            action="EVIDENCE_ATTACHED",
            entity_type="investigation",
            entity_id=inv.id,
            metadata_={
                "evidence_id": str(evidence.id),
                "evidence_type": evidence.evidence_type,
                "source_type": evidence.source_type,
                "source_id": str(evidence.source_id) if evidence.source_id else None,
            },
        )
        session.add(audit_event)
        await session.flush()

        return InvestigationEvidenceResponse(
            id=evidence.id,
            investigation_id=evidence.investigation_id,
            evidence_type=EvidenceType(evidence.evidence_type),
            source_type=EvidenceSourceType(evidence.source_type),
            source_id=evidence.source_id,
            title=evidence.title,
            description=evidence.description,
            payload=evidence.payload,
            created_at=evidence.created_at,
        )

    # -------------------------------------------------------------------------
    # Internal Domain Helpers & Validation
    # -------------------------------------------------------------------------
    async def _handle_assignment(
        self,
        session: AsyncSession,
        inv: Investigation,
        target_user_id: uuid.UUID | None,
        current_user: User,
    ) -> None:
        """Evaluate assignment rules under row-level lock."""
        old_assigned = inv.assigned_to

        if current_user.role == "INVESTIGATOR":
            if target_user_id == current_user.id:
                # Concurrent self-assignment loser check
                if inv.assigned_to is not None and inv.assigned_to != current_user.id:
                    raise ConflictError(
                        "Investigation was concurrently assigned to another user.",
                        code="CASE_ALREADY_ASSIGNED",
                    )
                inv.assigned_to = current_user.id
            elif target_user_id is None:
                # Self-unassign
                if inv.assigned_to != current_user.id:
                    raise AuthorizationError(
                        "Cannot unassign an investigation that is not assigned to you.",
                        code="FORBIDDEN",
                    )
                inv.assigned_to = None
            else:
                raise AuthorizationError(
                    "Investigators cannot assign investigations to peers.",
                    code="FORBIDDEN",
                )
        elif current_user.role == "ADMIN":
            if target_user_id is not None:
                assignee = await self.repo.get_user(session, target_user_id)
                if assignee is None:
                    raise NotFoundError(
                        f"User '{target_user_id}' was not found.",
                        code="USER_NOT_FOUND",
                    )
                if not assignee.is_active:
                    raise ValidationError(
                        "Cannot assign an investigation to an inactive user.",
                        code="USER_INACTIVE",
                    )
                if assignee.role not in ("ADMIN", "INVESTIGATOR"):
                    raise ValidationError(
                        "Assignee must have role ADMIN or INVESTIGATOR.",
                        code="INVALID_ASSIGNEE_ROLE",
                    )
            inv.assigned_to = target_user_id

        if old_assigned != inv.assigned_to:
            audit_event = AuditEvent(
                id=uuid.uuid4(),
                actor_user_id=current_user.id,
                action="INVESTIGATION_ASSIGNED",
                entity_type="investigation",
                entity_id=inv.id,
                metadata_={
                    "old_assigned_to": str(old_assigned) if old_assigned else None,
                    "new_assigned_to": str(inv.assigned_to)
                    if inv.assigned_to
                    else None,
                },
            )
            session.add(audit_event)

    def _handle_priority_change(
        self,
        session: AsyncSession,
        inv: Investigation,
        target_priority: InvestigationPriority,
        current_user: User,
    ) -> None:
        """Evaluate priority change rules under row-level lock."""
        if current_user.role == "INVESTIGATOR" and inv.assigned_to != current_user.id:
            raise AuthorizationError(
                "Investigators can only change priority on their assigned investigations.",
                code="FORBIDDEN",
            )

        if inv.priority != target_priority.value:
            old_priority = inv.priority
            inv.priority = target_priority.value
            audit_event = AuditEvent(
                id=uuid.uuid4(),
                actor_user_id=current_user.id,
                action="INVESTIGATION_PRIORITY_CHANGED",
                entity_type="investigation",
                entity_id=inv.id,
                metadata_={
                    "old_priority": old_priority,
                    "new_priority": inv.priority,
                },
            )
            session.add(audit_event)

    def _handle_status_transition(
        self,
        session: AsyncSession,
        inv: Investigation,
        target_status: InvestigationStatus,
        current_user: User,
    ) -> None:
        """Evaluate lifecycle status transitions permitted via PATCH."""
        if target_status == InvestigationStatus.RESOLVED:
            raise ConflictError(
                "Resolution must use the dedicated /resolve endpoint.",
                code="INVALID_LIFECYCLE_TRANSITION",
            )

        if (
            inv.status == InvestigationStatus.OPEN.value
            and target_status == InvestigationStatus.UNDER_REVIEW
        ):
            if (
                current_user.role == "INVESTIGATOR"
                and inv.assigned_to != current_user.id
            ):
                raise AuthorizationError(
                    "Investigators can only transition investigations assigned to themselves.",
                    code="FORBIDDEN",
                )
            old_status = inv.status
            inv.status = InvestigationStatus.UNDER_REVIEW.value
            audit_event = AuditEvent(
                id=uuid.uuid4(),
                actor_user_id=current_user.id,
                action="INVESTIGATION_STATUS_CHANGED",
                entity_type="investigation",
                entity_id=inv.id,
                metadata_={
                    "old_status": old_status,
                    "new_status": inv.status,
                },
            )
            session.add(audit_event)
        elif target_status.value != inv.status:
            raise ConflictError(
                f"Invalid lifecycle transition from {inv.status} to {target_status.value}.",
                code="INVALID_LIFECYCLE_TRANSITION",
            )

    async def _build_evidence_snapshot(
        self,
        session: AsyncSession,
        inv: Investigation,
        request: InvestigationEvidenceCreateRequest,
    ) -> dict[str, Any] | None:
        """Validate source scope against investigation context and build authoritative snapshot."""
        # 1. USER_NOTE
        if request.evidence_type == EvidenceType.USER_NOTE:
            return request.payload

        assert request.source_id is not None
        linked_tx_ids = {link.transaction_id for link in inv.transaction_associations}

        # 2. TRANSACTION_FACT
        if request.evidence_type == EvidenceType.TRANSACTION_FACT:
            tx = await self.repo.get_transaction(session, request.source_id)
            if tx is None:
                raise NotFoundError(
                    f"Transaction source '{request.source_id}' was not found.",
                    code="SOURCE_NOT_FOUND",
                )
            if tx.id not in linked_tx_ids:
                raise ValidationError(
                    f"Transaction '{tx.id}' is not linked to investigation '{inv.id}'.",
                    code="SOURCE_SCOPE_INVALID",
                )
            return {
                "id": str(tx.id),
                "external_transaction_id": tx.external_transaction_id,
                "account_id": str(tx.account_id),
                "counterparty_account_id": str(tx.counterparty_account_id)
                if tx.counterparty_account_id
                else None,
                "amount": str(tx.amount),
                "currency": tx.currency,
                "transaction_type": tx.transaction_type,
                "direction": tx.direction,
                "occurred_at": tx.occurred_at.isoformat(),
                "source_namespace": tx.source_namespace,
                "category": tx.category,
                "payment_method": tx.payment_method,
                "channel": tx.channel,
            }

        # 3. RISK_SCORE
        if request.evidence_type == EvidenceType.RISK_SCORE:
            ra = await self.repo.get_risk_analysis(session, request.source_id)
            if ra is None:
                raise NotFoundError(
                    f"RiskAnalysis source '{request.source_id}' was not found.",
                    code="SOURCE_NOT_FOUND",
                )
            if ra.transaction_id not in linked_tx_ids:
                raise ValidationError(
                    f"RiskAnalysis transaction '{ra.transaction_id}' is not linked to investigation '{inv.id}'.",
                    code="SOURCE_SCOPE_INVALID",
                )
            return {
                "id": str(ra.id),
                "transaction_id": str(ra.transaction_id),
                "score": float(ra.score),
                "risk_level": ra.risk_level,
                "model_version": ra.model_version.version if ra.model_version else None,
                "config_version": ra.config_version,
                "feature_vector_hash": ra.feature_vector_hash,
                "ml_anomaly_score": ra.ml_anomaly_score,
                "rule_score": ra.rule_score,
                "created_at": ra.created_at.isoformat(),
            }

        # 4. RISK_FACTOR
        if request.evidence_type == EvidenceType.RISK_FACTOR:
            rf = await self.repo.get_risk_factor(session, request.source_id)
            if rf is None:
                raise NotFoundError(
                    f"RiskFactor source '{request.source_id}' was not found.",
                    code="SOURCE_NOT_FOUND",
                )
            if (
                rf.risk_analysis is None
                or rf.risk_analysis.transaction_id not in linked_tx_ids
            ):
                raise ValidationError(
                    "RiskFactor parent transaction is not linked to this investigation.",
                    code="SOURCE_SCOPE_INVALID",
                )
            return {
                "id": str(rf.id),
                "risk_analysis_id": str(rf.risk_analysis_id),
                "factor_code": rf.factor_code,
                "factor_label": rf.factor_label,
                "severity": rf.severity,
                "description": rf.description,
                "value_numeric": float(rf.value_numeric)
                if rf.value_numeric is not None
                else None,
                "value_text": rf.value_text,
                "evidence": rf.evidence,
                "created_at": rf.created_at.isoformat(),
            }

        # Collect all account IDs associated with linked transactions
        involved_account_ids: set[uuid.UUID] = set()
        for assoc in inv.transaction_associations:
            if assoc.transaction is not None:
                involved_account_ids.add(assoc.transaction.account_id)
                if assoc.transaction.counterparty_account_id is not None:
                    involved_account_ids.add(assoc.transaction.counterparty_account_id)

        # 5. ACCOUNT_PROFILE
        if request.evidence_type == EvidenceType.ACCOUNT_PROFILE:
            acc = await self.repo.get_account(session, request.source_id)
            if acc is None:
                raise NotFoundError(
                    f"Account source '{request.source_id}' was not found.",
                    code="SOURCE_NOT_FOUND",
                )
            if acc.id not in involved_account_ids:
                raise ValidationError(
                    f"Account '{acc.id}' is not involved in any transaction linked to this investigation.",
                    code="SOURCE_SCOPE_INVALID",
                )
            return {
                "id": str(acc.id),
                "external_account_id": acc.external_account_id,
                "account_type": acc.account_type,
                "customer_age": acc.customer_age,
                "status": acc.status,
                "source_namespace": acc.source_namespace,
                "created_at": acc.created_at.isoformat(),
            }

        # 6. DEVICE_PROFILE
        if request.evidence_type == EvidenceType.DEVICE_PROFILE:
            dev = await self.repo.get_device(session, request.source_id)
            if dev is None:
                raise NotFoundError(
                    f"Device source '{request.source_id}' was not found.",
                    code="SOURCE_NOT_FOUND",
                )
            is_linked_to_accounts = await self.repo.is_device_linked_to_accounts(
                session, dev.id, list(involved_account_ids)
            )
            if not is_linked_to_accounts:
                raise ValidationError(
                    f"Device '{dev.id}' is not linked to any account involved in this investigation.",
                    code="SOURCE_SCOPE_INVALID",
                )
            return {
                "id": str(dev.id),
                "external_device_id": dev.external_device_id,
                "device_type": dev.device_type,
                "operating_system": dev.operating_system,
                "first_seen_at": dev.first_seen_at.isoformat()
                if dev.first_seen_at
                else None,
                "created_at": dev.created_at.isoformat(),
            }

        return None

    def _to_workspace_response(
        self,
        inv: Investigation,
        primary_tx: Transaction,
        latest_risk: RiskAnalysis | None,
    ) -> InvestigationDetailResponse:
        """Map ORM models to complete workspace detail response DTO."""
        primary_dto = InvestigationPrimaryTransactionDTO(
            id=primary_tx.id,
            external_transaction_id=primary_tx.external_transaction_id,
            account_id=primary_tx.account_id,
            amount=str(primary_tx.amount),
            currency=primary_tx.currency,
            direction=primary_tx.direction,
            occurred_at=primary_tx.occurred_at,
            source_namespace=primary_tx.source_namespace,
            category=primary_tx.category,
            payment_method=primary_tx.payment_method,
        )

        risk_dto: InvestigationLatestRiskDTO | None = None
        if latest_risk is not None:
            risk_dto = InvestigationLatestRiskDTO(
                id=latest_risk.id,
                score=float(latest_risk.score),
                risk_level=latest_risk.risk_level,
                model_version=latest_risk.model_version.version
                if latest_risk.model_version
                else "UNKNOWN",
                created_at=latest_risk.created_at,
            )

        related_items: list[InvestigationTransactionItem] = []
        for assoc in inv.transaction_associations:
            if assoc.relationship_type == InvestigationRelationshipType.RELATED.value:
                tx = assoc.transaction
                if tx is not None:
                    related_items.append(
                        InvestigationTransactionItem(
                            transaction_id=assoc.transaction_id,
                            relationship_type=InvestigationRelationshipType.RELATED,
                            account_id=tx.account_id,
                            amount=str(tx.amount),
                            currency=tx.currency,
                            direction=tx.direction,
                            occurred_at=tx.occurred_at,
                            created_at=assoc.created_at,
                        )
                    )

        # Sort deterministic
        related_items.sort(key=lambda item: (item.created_at, item.transaction_id))

        return InvestigationDetailResponse(
            id=inv.id,
            status=InvestigationStatus(inv.status),
            priority=InvestigationPriority(inv.priority),
            assigned_to=inv.assigned_to,
            assigned_user_email=inv.assigned_user.email if inv.assigned_user else None,
            primary_transaction=primary_dto,
            latest_risk_analysis=risk_dto,
            related_transactions=related_items,
            resolution=InvestigationResolution(inv.resolution)
            if inv.resolution
            else None,
            resolution_notes=inv.resolution_notes,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    def _require_roles(self, current_user: User, allowed_roles: set[str]) -> None:
        """Enforce service-layer role authorization."""
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Role '{current_user.role}' is not authorized to perform this operation.",
                code="FORBIDDEN",
            )
