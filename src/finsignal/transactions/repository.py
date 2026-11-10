"""PostgreSQL repository for transaction querying, filtering, and detail context."""

import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from finsignal.risk.models import RiskAnalysis
from finsignal.transactions.models import Transaction


class TransactionRepository:
    """Async SQLAlchemy repository for read-only transaction exploration and detail retrieval."""

    async def verify_namespace_exists(
        self, session: AsyncSession, namespace: str
    ) -> bool:
        """Check whether a source namespace exists in accounts or dataset_imports."""
        stmt_acc = text("SELECT 1 FROM accounts WHERE source_namespace = :ns LIMIT 1")
        res_acc = await session.execute(stmt_acc, {"ns": namespace})
        if res_acc.scalar_one_or_none() is not None:
            return True

        stmt_imp = text(
            "SELECT 1 FROM dataset_imports WHERE source_namespace = :ns LIMIT 1"
        )
        res_imp = await session.execute(stmt_imp, {"ns": namespace})
        return res_imp.scalar_one_or_none() is not None

    def _build_filter_conditions(
        self,
        *,
        source_namespace: str,
        account_id: uuid.UUID | None = None,
        merchant_id: uuid.UUID | None = None,
        device_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        transaction_type: str | None = None,
        direction: str | None = None,
        category: str | None = None,
        currency: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        risk_level: str | None = None,
    ) -> list[ColumnElement[bool]]:
        """Assemble parameterized WHERE predicates shared by count and page queries."""
        conditions: list[ColumnElement[bool]] = [
            Transaction.source_namespace == source_namespace
        ]
        if account_id is not None:
            conditions.append(Transaction.account_id == account_id)
        if merchant_id is not None:
            conditions.append(Transaction.merchant_id == merchant_id)
        if device_id is not None:
            conditions.append(Transaction.device_id == device_id)
        if location_id is not None:
            conditions.append(Transaction.location_id == location_id)
        if transaction_type is not None:
            conditions.append(Transaction.transaction_type == transaction_type)
        if direction is not None:
            conditions.append(Transaction.direction == direction)
        if category is not None:
            conditions.append(Transaction.category == category)
        if currency is not None:
            conditions.append(Transaction.currency == currency)
        if from_time is not None:
            conditions.append(Transaction.occurred_at >= from_time)
        if to_time is not None:
            conditions.append(Transaction.occurred_at < to_time)
        if min_amount is not None:
            conditions.append(Transaction.amount >= min_amount)
        if max_amount is not None:
            conditions.append(Transaction.amount <= max_amount)
        if risk_level is not None:
            # Resolve latest risk analysis deterministically using (created_at DESC, id DESC)
            # to stay consistent with RiskRepository.get_latest_for_transaction.
            latest_ra_id = (
                select(RiskAnalysis.id)
                .where(RiskAnalysis.transaction_id == Transaction.id)
                .order_by(RiskAnalysis.created_at.desc(), RiskAnalysis.id.desc())
                .limit(1)
                .correlate(Transaction)
                .scalar_subquery()
            )
            conditions.append(
                exists(
                    select(1).where(
                        RiskAnalysis.id == latest_ra_id,
                        RiskAnalysis.risk_level == risk_level,
                    )
                )
            )
        return conditions

    def _build_order_by(
        self, sort_by: str, sort_order: str
    ) -> tuple[ColumnElement[Any], ...]:
        """Map whitelisted sort parameters to deterministic SQLAlchemy ORDER BY clauses."""
        is_asc = sort_order == "asc"
        if sort_by == "occurred_at":
            primary_occurred = (
                Transaction.occurred_at.asc()
                if is_asc
                else Transaction.occurred_at.desc()
            )
            return (primary_occurred, Transaction.id.desc())
        if sort_by == "amount":
            primary_amount = (
                Transaction.amount.asc() if is_asc else Transaction.amount.desc()
            )
            return (
                primary_amount,
                Transaction.occurred_at.desc(),
                Transaction.id.desc(),
            )
        if sort_by == "created_at":
            primary_created = (
                Transaction.created_at.asc()
                if is_asc
                else Transaction.created_at.desc()
            )
            return (primary_created, Transaction.id.desc())
        raise ValueError(f"Unsupported sort_by field: {sort_by}")

    async def list_transactions(
        self,
        session: AsyncSession,
        *,
        source_namespace: str,
        page: int = 1,
        page_size: int = 50,
        account_id: uuid.UUID | None = None,
        merchant_id: uuid.UUID | None = None,
        device_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        transaction_type: str | None = None,
        direction: str | None = None,
        category: str | None = None,
        currency: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        risk_level: str | None = None,
        sort_by: str = "occurred_at",
        sort_order: str = "desc",
    ) -> tuple[list[Transaction], int, int]:
        """Execute count-first paginated transaction listing with deterministic sorting."""
        conditions = self._build_filter_conditions(
            source_namespace=source_namespace,
            account_id=account_id,
            merchant_id=merchant_id,
            device_id=device_id,
            location_id=location_id,
            transaction_type=transaction_type,
            direction=direction,
            category=category,
            currency=currency,
            from_time=from_time,
            to_time=to_time,
            min_amount=min_amount,
            max_amount=max_amount,
            risk_level=risk_level,
        )

        count_stmt = select(func.count(Transaction.id)).where(*conditions)
        total: int = (await session.execute(count_stmt)).scalar_one()
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        if total == 0 or offset >= total:
            return [], total, total_pages

        order_clauses = self._build_order_by(sort_by, sort_order)
        stmt = (
            select(Transaction)
            .where(*conditions)
            .order_by(*order_clauses)
            .offset(offset)
            .limit(page_size)
        )
        items = list((await session.execute(stmt)).scalars().all())
        return items, total, total_pages

    async def get_transaction_detail(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
        *,
        source_namespace: str | None = None,
    ) -> tuple[Transaction, RiskAnalysis | None] | None:
        """Retrieve a single transaction with eager-loaded entities and latest risk snapshot."""
        conditions: list[ColumnElement[bool]] = [Transaction.id == transaction_id]
        if source_namespace is not None:
            conditions.append(Transaction.source_namespace == source_namespace)

        stmt = (
            select(Transaction)
            .options(
                joinedload(Transaction.account),
                joinedload(Transaction.counterparty_account),
                joinedload(Transaction.merchant),
                joinedload(Transaction.device),
                joinedload(Transaction.location),
            )
            .where(*conditions)
        )
        tx = (await session.execute(stmt)).scalar_one_or_none()
        if tx is None:
            return None

        risk_stmt = (
            select(RiskAnalysis)
            .options(joinedload(RiskAnalysis.model_version))
            .where(RiskAnalysis.transaction_id == tx.id)
            .order_by(RiskAnalysis.created_at.desc(), RiskAnalysis.id.desc())
            .limit(1)
        )
        latest_risk = (await session.execute(risk_stmt)).scalar_one_or_none()
        return tx, latest_risk
