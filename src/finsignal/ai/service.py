"""Service layer orchestrating Phase 10 AI Investigation Assistant lifecycle, concurrency, and grounding."""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from finsignal.ai.context import (
    EvidenceContextBuilder,
    InvestigationEvidenceContext,
)
from finsignal.ai.exceptions import (
    AISummaryInProgressError,
    GroundingValidationError,
    InvalidProviderOutputError,
    InvestigationResolvedError,
    ProviderExecutionError,
    ProviderTimeoutError,
)
from finsignal.ai.models import AISummary
from finsignal.ai.prompts import CURRENT_PROMPT_VERSION, PromptManager
from finsignal.ai.providers.base import BaseLLMProvider, ProviderRequest
from finsignal.ai.providers.factory import get_llm_provider
from finsignal.ai.providers.mock import MockProviderError
from finsignal.ai.repository import AISummaryRepository
from finsignal.ai.schemas import (
    AISummaryGenerateRequest,
    AISummaryListResponse,
    AISummaryOutput,
    AISummaryResponse,
    AISummaryStatus,
)
from finsignal.audit.models import AuditEvent
from finsignal.common.exceptions import (
    AuthorizationError,
    NotFoundError,
)
from finsignal.core.config import Settings, get_settings
from finsignal.investigations.models import Investigation
from finsignal.investigations.repository import InvestigationRepository
from finsignal.users.models import User

logger = logging.getLogger(__name__)
MAX_SNAPSHOT_RETRIES = 3


class AISummaryService:
    """Orchestrates two-phase AI summary lifecycle, provider invocation, and grounding validation."""

    def __init__(
        self,
        engine: AsyncEngine,
        session_maker: async_sessionmaker[AsyncSession],
        ai_repo: AISummaryRepository | None = None,
        inv_repo: InvestigationRepository | None = None,
        provider: BaseLLMProvider | None = None,
        prompt_manager: PromptManager | None = None,
        context_builder: EvidenceContextBuilder | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.engine = engine
        self.session_maker = session_maker
        self.ai_repo = ai_repo or AISummaryRepository()
        self.inv_repo = inv_repo or InvestigationRepository()
        self.settings = settings or get_settings()
        self.provider = provider or get_llm_provider(self.settings)
        self.prompt_manager = prompt_manager or PromptManager(
            prompt_version=CURRENT_PROMPT_VERSION
        )
        self.context_builder = context_builder or EvidenceContextBuilder()

    # -------------------------------------------------------------------------
    # Generate Summary
    # -------------------------------------------------------------------------
    async def generate_summary(
        self,
        investigation_id: uuid.UUID,
        request: AISummaryGenerateRequest,
        current_user: User,
    ) -> AISummaryResponse:
        """Execute synchronous AI summary generation across two discrete database transactions.

        Tx 1: Read consistent REPEATABLE READ snapshot, lock case, check reuse, insert PENDING record.
        Outside Tx: Call provider with timeout and validate grounded response.
        Tx 2: Execute atomic terminal CAS update and commit corresponding AuditEvent.
        """
        self._require_roles(current_user, {"ADMIN", "INVESTIGATOR"})

        # =====================================================================
        # Transaction 1: Reservation & Snapshot Assembly (REPEATABLE READ)
        # =====================================================================
        reservation_result = await self._execute_reservation_phase(
            investigation_id=investigation_id,
            request=request,
            current_user=current_user,
        )

        # Early return if existing completed summary was reused
        if isinstance(reservation_result, AISummaryResponse):
            return reservation_result

        pending_summary, context, generation_token = reservation_result

        # =====================================================================
        # Provider Execution (OUTSIDE Database Transaction)
        # =====================================================================
        system_prompt, user_prompt, _ = self.prompt_manager.render_prompts(context)
        provider_request = ProviderRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=pending_summary.model,
            timeout_seconds=self.settings.ai_timeout_seconds,
            context=context,
        )

        terminal_status: str
        validated_output: AISummaryOutput | None = None
        error_msg: str | None = None
        terminal_exception: Exception | None = None

        try:
            # Enforce hard timeout boundary
            provider_response = await asyncio.wait_for(
                self.provider.generate(provider_request),
                timeout=self.settings.ai_timeout_seconds,
            )

            # Stage 1: Structural JSON / Pydantic validation
            try:
                raw_json = json.loads(provider_response.raw_content)
                validated_output = AISummaryOutput.model_validate(raw_json)
            except (json.JSONDecodeError, PydanticValidationError) as val_err:
                raise InvalidProviderOutputError(
                    "AI provider returned malformed or non-compliant summary output.",
                    details={"error": str(val_err)},
                ) from val_err

            # Stage 2: Grounding and reference existence validation
            self._validate_grounding(validated_output, context)

            terminal_status = AISummaryStatus.COMPLETED.value

        except TimeoutError:
            terminal_status = AISummaryStatus.FAILED.value
            error_msg = f"AI provider timed out after {self.settings.ai_timeout_seconds:.1f} seconds."
            terminal_exception = ProviderTimeoutError(
                error_msg,
                details={
                    "summary_id": str(pending_summary.id),
                    "status": terminal_status,
                },
            )
        except GroundingValidationError as ground_exc:
            terminal_status = AISummaryStatus.FAILED.value
            error_msg = f"Grounding validation failure: {ground_exc.message}"
            terminal_exception = GroundingValidationError(
                error_msg,
                details={
                    "summary_id": str(pending_summary.id),
                    "status": terminal_status,
                },
            )
        except InvalidProviderOutputError as out_exc:
            terminal_status = AISummaryStatus.FAILED.value
            error_msg = f"Invalid provider output: {out_exc.message}"
            terminal_exception = InvalidProviderOutputError(
                error_msg,
                details={
                    "summary_id": str(pending_summary.id),
                    "status": terminal_status,
                },
            )
        except (MockProviderError, Exception) as prov_exc:
            terminal_status = AISummaryStatus.FAILED.value
            error_msg = f"AI provider error: {prov_exc}"
            terminal_exception = ProviderExecutionError(
                error_msg,
                details={
                    "summary_id": str(pending_summary.id),
                    "status": terminal_status,
                },
            )

        # =====================================================================
        # Transaction 2: Terminal State CAS & Audit Logging
        # =====================================================================
        now = datetime.now(UTC)
        summary_payload = (
            validated_output.model_dump(mode="json") if validated_output else None
        )

        async with self.session_maker() as session, session.begin():
            updated = await self.ai_repo.update_terminal_cas(
                session=session,
                summary_id=pending_summary.id,
                status=terminal_status,
                generation_token=generation_token,
                completed_at=now,
                summary_payload=summary_payload,
                error_message=error_msg,
            )
            if not updated:
                # Lease was revoked by recovery; discard delayed result
                logger.warning(
                    "AI generation lease expired or superseded for summary %s",
                    pending_summary.id,
                )
                raise ProviderTimeoutError(
                    "AI generation lease expired before completion.",
                    details={"summary_id": str(pending_summary.id), "status": "FAILED"},
                )

            # Atomic Audit Event in the same transaction
            audit_action = (
                "AI_SUMMARY_GENERATED"
                if terminal_status == AISummaryStatus.COMPLETED.value
                else "AI_SUMMARY_FAILED"
            )
            audit_event = AuditEvent(
                id=uuid.uuid4(),
                actor_user_id=current_user.id,
                action=audit_action,
                entity_type="investigation",
                entity_id=investigation_id,
                metadata_={
                    "summary_id": str(pending_summary.id),
                    "provider": pending_summary.provider,
                    "model": pending_summary.model,
                    "prompt_version": pending_summary.prompt_version,
                    "evidence_hash": pending_summary.evidence_hash,
                    "status": terminal_status,
                    "error_message": error_msg,
                },
            )
            session.add(audit_event)

        # If generation failed, raise the mapped API error (which carries summary_id)
        if terminal_exception is not None:
            raise terminal_exception

        # Return completed DTO
        return AISummaryResponse(
            id=pending_summary.id,
            investigation_id=pending_summary.investigation_id,
            provider=pending_summary.provider,
            model=pending_summary.model,
            prompt_version=pending_summary.prompt_version,
            evidence_hash=pending_summary.evidence_hash,
            context_hash=pending_summary.context_hash,
            status=AISummaryStatus.COMPLETED,
            summary=validated_output,
            error_message=None,
            is_stale=False,
            generated_at=pending_summary.generated_at,
            completed_at=now,
            created_at=pending_summary.created_at,
        )

    # -------------------------------------------------------------------------
    # Get Latest Summary
    # -------------------------------------------------------------------------
    async def get_latest_summary(
        self,
        investigation_id: uuid.UUID,
        current_user: User,
    ) -> AISummaryResponse:
        """Retrieve the latest summary for an investigation with dynamic staleness check."""
        self._require_roles(current_user, {"ADMIN", "ANALYST", "INVESTIGATOR"})

        async with self.session_maker() as session:
            inv = await self.inv_repo.load_complete_investigation_graph(
                session, investigation_id
            )
            if inv is None:
                raise NotFoundError(
                    f"Investigation '{investigation_id}' was not found.",
                    code="INVESTIGATION_NOT_FOUND",
                )
            self._check_investigation_authorization(inv, current_user)

            summary = await self.ai_repo.get_latest_for_investigation(
                session, investigation_id
            )
            if summary is None:
                raise NotFoundError(
                    f"No AI summary found for investigation '{investigation_id}'.",
                    code="AI_SUMMARY_NOT_FOUND",
                )

            # Recompute authoritative evidence hash for staleness detection
            latest_risk = None
            primary_tx = (
                inv.primary_association.transaction if inv.primary_association else None
            )
            if primary_tx:
                latest_risk = await self.inv_repo.get_latest_risk_for_transaction(
                    session, primary_tx.id
                )

            current_evidence_hash = (
                self.context_builder.compute_authoritative_evidence_hash(
                    investigation=inv,
                    latest_risk=latest_risk,
                )
            )
            is_stale = current_evidence_hash != summary.evidence_hash

            parsed_output = (
                AISummaryOutput.model_validate(summary.summary)
                if summary.summary and summary.status == "COMPLETED"
                else None
            )

            return AISummaryResponse(
                id=summary.id,
                investigation_id=summary.investigation_id,
                provider=summary.provider,
                model=summary.model,
                prompt_version=summary.prompt_version,
                evidence_hash=summary.evidence_hash,
                context_hash=summary.context_hash,
                status=AISummaryStatus(summary.status),
                summary=parsed_output,
                error_message=summary.error_message,
                is_stale=is_stale,
                generated_at=summary.generated_at,
                completed_at=summary.completed_at,
                created_at=summary.created_at,
            )

    # -------------------------------------------------------------------------
    # List Summary History
    # -------------------------------------------------------------------------
    async def list_summary_history(
        self,
        investigation_id: uuid.UUID,
        page: int,
        page_size: int,
        current_user: User,
    ) -> AISummaryListResponse:
        """Retrieve paginated summary history for an investigation."""
        self._require_roles(current_user, {"ADMIN", "ANALYST", "INVESTIGATOR"})

        async with self.session_maker() as session:
            inv = await self.inv_repo.get_by_id(session, investigation_id)
            if inv is None:
                raise NotFoundError(
                    f"Investigation '{investigation_id}' was not found.",
                    code="INVESTIGATION_NOT_FOUND",
                )
            self._check_investigation_authorization(inv, current_user)

            items, total, total_pages = await self.ai_repo.list_for_investigation(
                session=session,
                investigation_id=investigation_id,
                page=page,
                page_size=page_size,
            )

            dtos: list[AISummaryResponse] = []
            for s in items:
                parsed_output = (
                    AISummaryOutput.model_validate(s.summary)
                    if s.summary and s.status == "COMPLETED"
                    else None
                )
                dtos.append(
                    AISummaryResponse(
                        id=s.id,
                        investigation_id=s.investigation_id,
                        provider=s.provider,
                        model=s.model,
                        prompt_version=s.prompt_version,
                        evidence_hash=s.evidence_hash,
                        context_hash=s.context_hash,
                        status=AISummaryStatus(s.status),
                        summary=parsed_output,
                        error_message=s.error_message,
                        is_stale=False,
                        generated_at=s.generated_at,
                        completed_at=s.completed_at,
                        created_at=s.created_at,
                    )
                )

            return AISummaryListResponse(
                items=dtos,
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            )

    # -------------------------------------------------------------------------
    # Reservation Phase (Transaction 1 under REPEATABLE READ)
    # -------------------------------------------------------------------------
    def _check_investigation_authorization(
        self, inv: Investigation, current_user: User
    ) -> None:
        """Verify investigator assignment permissions."""
        if current_user.role == "INVESTIGATOR" and inv.assigned_to != current_user.id:
            raise AuthorizationError(
                "Investigators can only access AI summaries for investigations assigned to themselves.",
                code="FORBIDDEN",
            )

    async def _execute_reservation_phase(
        self,
        investigation_id: uuid.UUID,
        request: AISummaryGenerateRequest,
        current_user: User,
    ) -> tuple[AISummary, InvestigationEvidenceContext, uuid.UUID] | AISummaryResponse:
        """Execute Transaction 1 under REPEATABLE READ with retry for SQLSTATE 40001."""
        for attempt in range(MAX_SNAPSHOT_RETRIES):
            try:
                async with self.engine.connect() as raw_conn:
                    conn = await raw_conn.execution_options(
                        isolation_level="REPEATABLE READ"
                    )
                    async with (
                        AsyncSession(bind=conn, expire_on_commit=False) as session,
                        session.begin(),
                    ):
                        return await self._reserve_and_snapshot(
                            session=session,
                            investigation_id=investigation_id,
                            request=request,
                            current_user=current_user,
                        )
            except DBAPIError as exc:
                sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(
                    exc.orig, "pgcode", None
                )
                if sqlstate == "40001" and attempt < MAX_SNAPSHOT_RETRIES - 1:
                    await asyncio.sleep(0.025 * (2**attempt))
                    continue
                raise

        raise ProviderExecutionError(
            "Could not obtain consistent investigation snapshot due to transaction concurrency.",
            code="SNAPSHOT_CONCURRENCY_ERROR",
        )

    async def _reserve_and_snapshot(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        request: AISummaryGenerateRequest,
        current_user: User,
    ) -> tuple[AISummary, InvestigationEvidenceContext, uuid.UUID] | AISummaryResponse:
        """Inner reservation logic executing within an isolated REPEATABLE READ snapshot."""
        # 1. Lock investigation row for case state & assignment evaluation
        stmt = (
            select(Investigation)
            .where(Investigation.id == investigation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        res = await session.execute(stmt)
        inv = res.scalar_one_or_none()
        if inv is None:
            raise NotFoundError(
                f"Investigation '{investigation_id}' was not found.",
                code="INVESTIGATION_NOT_FOUND",
            )

        # 2. Authorization & assignment verification
        self._check_investigation_authorization(inv, current_user)

        # 3. Reject resolved or closed investigations
        if inv.status in ("RESOLVED", "CLOSED"):
            raise InvestigationResolvedError()

        # 4. Check for active PENDING attempt and recover expired ones
        cutoff = datetime.now(UTC) - timedelta(
            seconds=self.settings.ai_pending_timeout_seconds
        )
        recovered = await self.ai_repo.recover_expired_pending(
            session=session,
            investigation_id=investigation_id,
            cutoff_time=cutoff,
            actor_user_id=current_user.id,
        )
        if recovered:
            logger.info(
                "Recovered expired PENDING AI summary %s for investigation %s",
                recovered.id,
                investigation_id,
            )

        active_pending = await self.ai_repo.get_active_pending(
            session, investigation_id
        )
        if active_pending is not None:
            raise AISummaryInProgressError(
                details={
                    "active_summary_id": str(active_pending.id),
                    "generated_at": active_pending.generated_at.isoformat(),
                }
            )

        # 5. Load complete investigation graph
        full_inv = await self.inv_repo.load_complete_investigation_graph(
            session, investigation_id
        )
        assert full_inv is not None

        primary_tx = (
            full_inv.primary_association.transaction
            if full_inv.primary_association
            else None
        )
        latest_risk = None
        if primary_tx:
            latest_risk = await self.inv_repo.get_latest_risk_for_transaction(
                session, primary_tx.id
            )

        # 6. Dual fingerprinting
        authoritative_hash = self.context_builder.compute_authoritative_evidence_hash(
            investigation=full_inv,
            latest_risk=latest_risk,
        )

        context, context_hash = self.context_builder.build_bounded_context(
            investigation=full_inv,
            latest_risk=latest_risk,
            max_items=self.settings.ai_max_evidence_items,
            max_bytes=self.settings.ai_max_context_bytes,
        )

        # 7. Completed summary reuse (when force_refresh is false)
        if not request.force_refresh:
            latest_summary = await self.ai_repo.get_latest_for_investigation(
                session, investigation_id
            )
            if (
                latest_summary is not None
                and latest_summary.status == AISummaryStatus.COMPLETED.value
                and latest_summary.evidence_hash == authoritative_hash
                and latest_summary.prompt_version == self.prompt_manager.prompt_version
            ):
                parsed = (
                    AISummaryOutput.model_validate(latest_summary.summary)
                    if latest_summary.summary
                    else None
                )
                return AISummaryResponse(
                    id=latest_summary.id,
                    investigation_id=latest_summary.investigation_id,
                    provider=latest_summary.provider,
                    model=latest_summary.model,
                    prompt_version=latest_summary.prompt_version,
                    evidence_hash=latest_summary.evidence_hash,
                    context_hash=latest_summary.context_hash,
                    status=AISummaryStatus.COMPLETED,
                    summary=parsed,
                    error_message=None,
                    is_stale=False,
                    generated_at=latest_summary.generated_at,
                    completed_at=latest_summary.completed_at,
                    created_at=latest_summary.created_at,
                )

        # 8. Create PENDING summary with fresh generation token
        generation_token = uuid.uuid4()
        now = datetime.now(UTC)
        pending_summary = AISummary(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            provider=self.settings.ai_provider,
            model=self.settings.ai_model,
            prompt_version=self.prompt_manager.prompt_version,
            evidence_hash=authoritative_hash,
            context_hash=context_hash,
            generation_token=generation_token,
            status=AISummaryStatus.PENDING.value,
            summary=None,
            error_message=None,
            generated_at=now,
            completed_at=None,
            created_at=now,
        )
        await self.ai_repo.create_pending(session, pending_summary)
        return pending_summary, context, generation_token

    # -------------------------------------------------------------------------
    # Grounding Validation
    # -------------------------------------------------------------------------
    def _validate_grounding(
        self,
        output: AISummaryOutput,
        context: InvestigationEvidenceContext,
    ) -> None:
        """Verify that every cited evidence_id corresponds to a valid entity in context."""
        valid_uuids: set[str] = set()

        # Primary transaction ID
        ptx_id = context.primary_transaction.get("id")
        if ptx_id:
            valid_uuids.add(str(ptx_id).lower())

        # Related transaction IDs
        for tx in context.related_transactions:
            if "transaction_id" in tx:
                valid_uuids.add(str(tx["transaction_id"]).lower())

        # Risk factor IDs
        for f in context.risk_factors:
            if "id" in f:
                valid_uuids.add(str(f["id"]).lower())

        # Evidence item IDs
        for ev in context.evidence_items:
            if "id" in ev:
                valid_uuids.add(str(ev["id"]).lower())

        # Validate citations across observed facts and derived signals
        for fact in output.observed_facts:
            for cited_id in fact.evidence_ids:
                if str(cited_id).lower() not in valid_uuids:
                    raise GroundingValidationError(
                        f"Observed fact cites unknown or uncorroborated evidence identifier: '{cited_id}'.",
                        details={"invalid_citation": str(cited_id)},
                    )

        for signal in output.derived_signals:
            for cited_id in signal.evidence_ids:
                if str(cited_id).lower() not in valid_uuids:
                    raise GroundingValidationError(
                        f"Derived signal cites unknown or uncorroborated evidence identifier: '{cited_id}'.",
                        details={"invalid_citation": str(cited_id)},
                    )

    def _require_roles(self, current_user: User, allowed_roles: set[str]) -> None:
        """Enforce service-layer role authorization."""
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Role '{current_user.role}' is not authorized to perform this operation.",
                code="FORBIDDEN",
            )
