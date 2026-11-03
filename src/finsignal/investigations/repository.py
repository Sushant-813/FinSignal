"""Asynchronous database repository for Phase 9 Investigation & Evidence persistence."""

import math
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from finsignal.accounts.models import Account, AccountDevice
from finsignal.devices.models import Device
from finsignal.investigations.models import (
    Investigation,
    InvestigationEvidence,
    InvestigationTransaction,
)
from finsignal.investigations.schemas import (
    InvestigationPriority,
    InvestigationStatus,
)
from finsignal.risk.models import RiskAnalysis, RiskFactor
from finsignal.transactions.models import Transaction
from finsignal.users.models import User


class InvestigationRepository:
    """Encapsulates SQLAlchemy persistence queries for investigations, links, and evidence."""

    async def create_atomic(
        self,
        session: AsyncSession,
        investigation: Investigation,
        primary_link: InvestigationTransaction,
    ) -> Investigation:
        """Persist a new investigation and its PRIMARY transaction link atomically."""
        session.add(investigation)
        session.add(primary_link)
        await session.flush()
        return investigation

    async def get_by_id(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
    ) -> Investigation | None:
        """Fetch investigation by primary key without locking."""
        stmt = select(Investigation).where(Investigation.id == investigation_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_update(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
    ) -> Investigation | None:
        """Acquire a row-level lock on the investigation record (SELECT ... FOR UPDATE)."""
        stmt = (
            select(Investigation)
            .where(Investigation.id == investigation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_workspace_detail(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
    ) -> Investigation | None:
        """Load complete investigation workspace context avoiding N+1 query loops.

        Eagerly loads assigned user, primary transaction association with its account,
        and linked transaction associations.
        """
        stmt = (
            select(Investigation)
            .where(Investigation.id == investigation_id)
            .options(
                joinedload(Investigation.assigned_user),
                joinedload(Investigation.primary_association)
                .joinedload(InvestigationTransaction.transaction)
                .joinedload(Transaction.account),
                selectinload(Investigation.transaction_associations).joinedload(
                    InvestigationTransaction.transaction
                ),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def load_complete_investigation_graph(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
    ) -> Investigation | None:
        """Load the complete investigation case graph for AI context construction.

        Eagerly loads:
        - assigned_user
        - primary_association -> transaction -> account
        - transaction_associations -> transaction -> account
        - evidence
        """
        stmt = (
            select(Investigation)
            .where(Investigation.id == investigation_id)
            .options(
                joinedload(Investigation.assigned_user),
                joinedload(Investigation.primary_association)
                .joinedload(InvestigationTransaction.transaction)
                .joinedload(Transaction.account),
                selectinload(Investigation.transaction_associations)
                .joinedload(InvestigationTransaction.transaction)
                .joinedload(Transaction.account),
                selectinload(Investigation.evidence),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_risk_for_transaction(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
    ) -> RiskAnalysis | None:
        """Retrieve the latest risk analysis record for a transaction with its model version and factors."""
        stmt = (
            select(RiskAnalysis)
            .options(
                joinedload(RiskAnalysis.model_version),
                selectinload(RiskAnalysis.factors),
            )
            .where(RiskAnalysis.transaction_id == transaction_id)
            .order_by(RiskAnalysis.created_at.desc(), RiskAnalysis.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_investigations(
        self,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 25,
        status: InvestigationStatus | None = None,
        priority: InvestigationPriority | None = None,
        assigned_to: uuid.UUID | None = None,
        unassigned: bool | None = None,
    ) -> tuple[list[Investigation], int, int]:
        """Query paginated investigations with dynamic filtering and deterministic ordering.

        Returns (items, total_count, total_pages).
        """
        conditions: list[Any] = []
        if status is not None:
            conditions.append(Investigation.status == status.value)
        if priority is not None:
            conditions.append(Investigation.priority == priority.value)
        if unassigned is True:
            conditions.append(Investigation.assigned_to.is_(None))
        elif assigned_to is not None:
            conditions.append(Investigation.assigned_to == assigned_to)

        # 1. Total count query
        count_stmt = select(func.count(Investigation.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total_result = await session.execute(count_stmt)
        total: int = total_result.scalar_one()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        # 2. Paginated item query
        stmt = (
            select(Investigation)
            .options(
                joinedload(Investigation.primary_association).joinedload(
                    InvestigationTransaction.transaction
                )
            )
            .order_by(Investigation.created_at.desc(), Investigation.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        if conditions:
            stmt = stmt.where(*conditions)

        result = await session.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total, total_pages

    async def add_transaction_link(
        self,
        session: AsyncSession,
        link: InvestigationTransaction,
    ) -> InvestigationTransaction:
        """Persist a new transaction association link."""
        session.add(link)
        await session.flush()
        return link

    async def get_transaction_links(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
    ) -> list[InvestigationTransaction]:
        """Retrieve all transaction associations for an investigation in deterministic order."""
        stmt = (
            select(InvestigationTransaction)
            .options(joinedload(InvestigationTransaction.transaction))
            .where(InvestigationTransaction.investigation_id == investigation_id)
            .order_by(
                InvestigationTransaction.created_at.asc(),
                InvestigationTransaction.transaction_id.asc(),
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def is_transaction_linked(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> bool:
        """Check if a transaction is already associated with an investigation."""
        stmt = select(func.count(InvestigationTransaction.investigation_id)).where(
            InvestigationTransaction.investigation_id == investigation_id,
            InvestigationTransaction.transaction_id == transaction_id,
        )
        result = await session.execute(stmt)
        count: int = result.scalar_one()
        return count > 0

    async def add_evidence(
        self,
        session: AsyncSession,
        evidence: InvestigationEvidence,
    ) -> InvestigationEvidence:
        """Persist an append-only evidence record."""
        session.add(evidence)
        await session.flush()
        return evidence

    async def list_evidence(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[InvestigationEvidence], int, int]:
        """Query paginated evidence records for an investigation with deterministic ordering."""
        count_stmt = select(func.count(InvestigationEvidence.id)).where(
            InvestigationEvidence.investigation_id == investigation_id
        )
        total_result = await session.execute(count_stmt)
        total: int = total_result.scalar_one()
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        offset = (page - 1) * page_size
        stmt = (
            select(InvestigationEvidence)
            .where(InvestigationEvidence.investigation_id == investigation_id)
            .order_by(
                InvestigationEvidence.created_at.asc(), InvestigationEvidence.id.asc()
            )
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        items = list(result.scalars().all())
        return items, total, total_pages

    # -------------------------------------------------------------------------
    # Domain Source Entity Inspection Queries
    # -------------------------------------------------------------------------
    async def get_transaction(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
    ) -> Transaction | None:
        """Retrieve authoritative transaction record."""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_risk_analysis(
        self,
        session: AsyncSession,
        analysis_id: uuid.UUID,
    ) -> RiskAnalysis | None:
        """Retrieve authoritative risk analysis record with model version."""
        stmt = (
            select(RiskAnalysis)
            .options(joinedload(RiskAnalysis.model_version))
            .where(RiskAnalysis.id == analysis_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_risk_factor(
        self,
        session: AsyncSession,
        factor_id: uuid.UUID,
    ) -> RiskFactor | None:
        """Retrieve authoritative risk factor record with parent risk analysis."""
        stmt = (
            select(RiskFactor)
            .options(joinedload(RiskFactor.risk_analysis))
            .where(RiskFactor.id == factor_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_account(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
    ) -> Account | None:
        """Retrieve authoritative account record."""
        stmt = select(Account).where(Account.id == account_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_device(
        self,
        session: AsyncSession,
        device_id: uuid.UUID,
    ) -> Device | None:
        """Retrieve authoritative device record."""
        stmt = select(Device).where(Device.id == device_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_device_linked_to_accounts(
        self,
        session: AsyncSession,
        device_id: uuid.UUID,
        account_ids: list[uuid.UUID],
    ) -> bool:
        """Verify device is linked to at least one of the specified accounts in account_devices."""
        if not account_ids:
            return False
        stmt = select(func.count(AccountDevice.device_id)).where(
            AccountDevice.device_id == device_id,
            AccountDevice.account_id.in_(account_ids),
        )
        result = await session.execute(stmt)
        count: int = result.scalar_one()
        return count > 0

    async def get_user(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> User | None:
        """Retrieve user record by id."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
