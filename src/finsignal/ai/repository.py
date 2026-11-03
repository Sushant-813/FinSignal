"""Asynchronous database repository for Phase 10 AI Investigation Assistant persistence."""

import math
import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.ai.models import AISummary
from finsignal.audit.models import AuditEvent
from finsignal.common.exceptions import ConflictError


class AISummaryRepository:
    """Encapsulates SQLAlchemy persistence queries for AI summaries, lifecycle transitions, and fencing."""

    async def create_pending(
        self,
        session: AsyncSession,
        summary: AISummary,
    ) -> AISummary:
        """Persist a new PENDING summary record.

        Translates database partial unique index violations on
        'uq_ai_summaries_one_pending_per_investigation' into ConflictError.
        """
        session.add(summary)
        try:
            await session.flush()
        except IntegrityError as exc:
            orig_msg = str(getattr(exc, "orig", exc))
            if "uq_ai_summaries_one_pending_per_investigation" in orig_msg:
                raise ConflictError(
                    "An AI summary generation attempt is already in progress for this investigation.",
                    code="AI_SUMMARY_IN_PROGRESS",
                    details={"investigation_id": str(summary.investigation_id)},
                ) from exc
            raise
        return summary

    async def get_by_id(
        self,
        session: AsyncSession,
        summary_id: uuid.UUID,
    ) -> AISummary | None:
        """Fetch AI summary by primary key."""
        stmt = select(AISummary).where(AISummary.id == summary_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_investigation(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
    ) -> AISummary | None:
        """Retrieve the latest summary for an investigation ordered deterministically."""
        stmt = (
            select(AISummary)
            .where(AISummary.investigation_id == investigation_id)
            .order_by(AISummary.created_at.desc(), AISummary.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_pending(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
    ) -> AISummary | None:
        """Query for an active PENDING summary on an investigation."""
        stmt = (
            select(AISummary)
            .where(
                AISummary.investigation_id == investigation_id,
                AISummary.status == "PENDING",
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_investigation(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AISummary], int, int]:
        """Query paginated summaries for an investigation in deterministic order.

        Returns (items, total_count, total_pages).
        """
        count_stmt = select(func.count(AISummary.id)).where(
            AISummary.investigation_id == investigation_id
        )
        total_res = await session.execute(count_stmt)
        total: int = total_res.scalar_one()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        stmt = (
            select(AISummary)
            .where(AISummary.investigation_id == investigation_id)
            .order_by(AISummary.created_at.desc(), AISummary.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        items = list(result.scalars().all())
        return items, total, total_pages

    async def recover_expired_pending(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        cutoff_time: datetime,
        actor_user_id: uuid.UUID | None = None,
    ) -> AISummary | None:
        """Atomically transition an expired PENDING record to FAILED and log an AuditEvent.

        Rotates generation_token to fence out any delayed responses.
        Returns the recovered record if one was expired and transitioned.
        """
        pending = await self.get_active_pending(session, investigation_id)
        if pending is None or pending.generated_at >= cutoff_time:
            return None

        new_token = uuid.uuid4()
        now = datetime.now(cutoff_time.tzinfo)
        stmt = (
            update(AISummary)
            .where(
                AISummary.id == pending.id,
                AISummary.status == "PENDING",
                AISummary.generation_token == pending.generation_token,
            )
            .values(
                status="FAILED",
                error_message="Generation attempt timed out and was recovered by system.",
                completed_at=now,
                generation_token=new_token,
            )
        )
        res = await session.execute(stmt)
        cursor_res = cast(CursorResult[Any], res)
        if cursor_res.rowcount == 1:
            audit_event = AuditEvent(
                id=uuid.uuid4(),
                actor_user_id=actor_user_id,
                action="AI_SUMMARY_FAILED",
                entity_type="investigation",
                entity_id=investigation_id,
                metadata_={
                    "summary_id": str(pending.id),
                    "provider": pending.provider,
                    "model": pending.model,
                    "prompt_version": pending.prompt_version,
                    "evidence_hash": pending.evidence_hash,
                    "status": "FAILED",
                    "error_message": "Generation attempt timed out and was recovered by system.",
                    "recovery": True,
                },
            )
            session.add(audit_event)
            await session.flush()
            # Refresh pending instance
            return await self.get_by_id(session, pending.id)
        return None

    async def update_terminal_cas(
        self,
        session: AsyncSession,
        summary_id: uuid.UUID,
        status: str,
        generation_token: uuid.UUID,
        completed_at: datetime,
        summary_payload: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Execute atomic Compare-And-Set (CAS) transition to terminal state (COMPLETED or FAILED).

        Guarantees:
        - Target record exists.
        - Status is currently PENDING.
        - Generation token strictly matches the active lease.
        - Rotates generation_token on terminal write to prevent double-completion.

        Returns True if exactly 1 row was updated, False otherwise (lease expired or superseded).
        """
        stmt = (
            update(AISummary)
            .where(
                AISummary.id == summary_id,
                AISummary.status == "PENDING",
                AISummary.generation_token == generation_token,
            )
            .values(
                status=status,
                summary=summary_payload,
                error_message=error_message,
                completed_at=completed_at,
                generation_token=uuid.uuid4(),
            )
        )
        result = await session.execute(stmt)
        cursor_res = cast(CursorResult[Any], result)
        return bool(cursor_res.rowcount == 1)
