"""PostgreSQL repository for bounded historical context and lifetime baseline queries.

Enforces:
- Separation of bounded window retrieval (30 days) from lifetime statistical summaries.
- Deterministic event ordering and sub-second UUID tie-breaking.
- Strict self-exclusion and future data exclusion.
- Absolute isolation from synthetic ground-truth evaluation labels.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
from finsignal.common.exceptions import NotFoundError
from finsignal.features.constants import CATEGORY_WINDOW_30D_SECONDS
from finsignal.features.schemas import (
    AccountProfileDTO,
    EvaluatedTransactionDTO,
    EvaluationContext,
    HistoricalTransactionDTO,
    LifetimeBaselineSummary,
)
from finsignal.transactions.models import Transaction


class FeatureRepository:
    """Async SQLAlchemy repository for point-in-time historical feature context."""

    async def get_account_profile(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> AccountProfileDTO | None:
        """Fetch account reference attributes by primary key UUID."""
        stmt = select(Account).where(Account.id == account_id)
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            return None

        created = (
            account.created_at.astimezone(UTC)
            if account.created_at.tzinfo
            else account.created_at.replace(tzinfo=UTC)
        )
        return AccountProfileDTO(
            id=account.id,
            source_namespace=account.source_namespace,
            home_location_id=account.home_location_id,
            created_at=created,
        )

    async def get_transaction_by_id(
        self, session: AsyncSession, transaction_id: uuid.UUID
    ) -> EvaluatedTransactionDTO | None:
        """Fetch evaluated transaction facts by primary key UUID."""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await session.execute(stmt)
        tx = result.scalar_one_or_none()
        if tx is None:
            return None

        occurred = (
            tx.occurred_at.astimezone(UTC)
            if tx.occurred_at.tzinfo
            else tx.occurred_at.replace(tzinfo=UTC)
        )
        return EvaluatedTransactionDTO(
            id=tx.id,
            account_id=tx.account_id,
            occurred_at=occurred,
            amount=tx.amount,
            currency=tx.currency,
            direction=tx.direction,
            transaction_type=tx.transaction_type,
            source_namespace=tx.source_namespace,
            merchant_id=tx.merchant_id,
            device_id=tx.device_id,
            location_id=tx.location_id,
            category=tx.category,
        )

    async def get_bounded_historical_transactions(
        self,
        session: AsyncSession,
        *,
        account_id: uuid.UUID,
        eval_occurred_at: datetime,
        eval_id: uuid.UUID,
        window_seconds: int = CATEGORY_WINDOW_30D_SECONDS,
    ) -> list[HistoricalTransactionDTO]:
        """Fetch historical transactions in bounded window [eval_t - window_seconds, eval_t)*.

        Uses PostgreSQL index scan on ix_transactions_account_occurred with range pushdown.
        """
        eval_t = (
            eval_occurred_at.astimezone(UTC)
            if eval_occurred_at.tzinfo
            else eval_occurred_at.replace(tzinfo=UTC)
        )
        window_start = eval_t - timedelta(seconds=window_seconds)

        # Range filter preserves index prefix on (account_id, occurred_at)
        stmt = text(
            """
            SELECT
                id,
                occurred_at,
                amount,
                currency,
                direction,
                transaction_type,
                merchant_id,
                device_id,
                location_id,
                category
            FROM transactions
            WHERE account_id = :account_id
              AND occurred_at >= :window_start
              AND occurred_at <= :eval_occurred_at
              AND NOT (occurred_at = :eval_occurred_at AND id >= :eval_id)
            ORDER BY occurred_at ASC, id ASC;
            """
        )
        result = await session.execute(
            stmt,
            {
                "account_id": account_id,
                "window_start": window_start,
                "eval_occurred_at": eval_t,
                "eval_id": eval_id,
            },
        )
        rows = result.fetchall()

        dtos: list[HistoricalTransactionDTO] = []
        for r in rows:
            occ = (
                r.occurred_at.astimezone(UTC)
                if r.occurred_at.tzinfo
                else r.occurred_at.replace(tzinfo=UTC)
            )
            dtos.append(
                HistoricalTransactionDTO(
                    id=r.id,
                    occurred_at=occ,
                    amount=r.amount,
                    currency=r.currency,
                    direction=r.direction,
                    transaction_type=r.transaction_type,
                    merchant_id=r.merchant_id,
                    device_id=r.device_id,
                    location_id=r.location_id,
                    category=r.category,
                )
            )
        return dtos

    async def get_lifetime_baseline_summary(
        self,
        session: AsyncSession,
        *,
        account_id: uuid.UUID,
        currency: str,
        direction: str,
        eval_occurred_at: datetime,
        eval_id: uuid.UUID,
    ) -> LifetimeBaselineSummary:
        """Fetch direction- and currency-matched lifetime summary stats directly via PostgreSQL aggregates."""
        eval_t = (
            eval_occurred_at.astimezone(UTC)
            if eval_occurred_at.tzinfo
            else eval_occurred_at.replace(tzinfo=UTC)
        )
        params = {
            "account_id": account_id,
            "currency": currency,
            "direction": direction,
            "eval_occurred_at": eval_t,
            "eval_id": eval_id,
        }

        # 1. Lifetime aggregates for matching direction and currency
        stats_stmt = text(
            """
            SELECT
                COUNT(*) AS count,
                AVG(amount) AS mean,
                STDDEV_SAMP(amount) AS stddev,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY amount)::numeric AS median
            FROM transactions
            WHERE account_id = :account_id
              AND currency = :currency
              AND direction = :direction
              AND (
                  occurred_at < :eval_occurred_at
                  OR (occurred_at = :eval_occurred_at AND id < :eval_id)
              );
            """
        )
        stats_res = (await session.execute(stats_stmt, params)).mappings().one()

        count = int(stats_res["count"])
        mean = (
            Decimal(str(stats_res["mean"])) if stats_res["mean"] is not None else None
        )
        stddev = float(stats_res["stddev"]) if stats_res["stddev"] is not None else None
        median = (
            Decimal(str(stats_res["median"]))
            if stats_res["median"] is not None
            else None
        )

        # 2. Total lifetime transaction count (all directions, all currencies)
        tot_stmt = text(
            """
            SELECT COUNT(*) AS total_count
            FROM transactions
            WHERE account_id = :account_id
              AND (
                  occurred_at < :eval_occurred_at
                  OR (occurred_at = :eval_occurred_at AND id < :eval_id)
              );
            """
        )
        tot_count: int = (await session.execute(tot_stmt, params)).scalar_one()

        # 3. Entity frequencies across lifetime history pushed down to SQL aggregates (PERF-03)
        ent_stmt = text(
            """
            SELECT
                (
                    SELECT COALESCE(jsonb_object_agg(device_id::text, cnt), '{}'::jsonb)
                    FROM (
                        SELECT device_id, COUNT(*) AS cnt
                        FROM transactions
                        WHERE account_id = :account_id
                          AND (occurred_at < :eval_occurred_at OR (occurred_at = :eval_occurred_at AND id < :eval_id))
                          AND device_id IS NOT NULL
                        GROUP BY device_id
                    ) sub_d
                ) AS device_counts,
                (
                    SELECT COALESCE(jsonb_object_agg(merchant_id::text, cnt), '{}'::jsonb)
                    FROM (
                        SELECT merchant_id, COUNT(*) AS cnt
                        FROM transactions
                        WHERE account_id = :account_id
                          AND (occurred_at < :eval_occurred_at OR (occurred_at = :eval_occurred_at AND id < :eval_id))
                          AND merchant_id IS NOT NULL
                        GROUP BY merchant_id
                    ) sub_m
                ) AS merchant_counts,
                (
                    SELECT COALESCE(jsonb_object_agg(location_id::text, cnt), '{}'::jsonb)
                    FROM (
                        SELECT location_id, COUNT(*) AS cnt
                        FROM transactions
                        WHERE account_id = :account_id
                          AND (occurred_at < :eval_occurred_at OR (occurred_at = :eval_occurred_at AND id < :eval_id))
                          AND location_id IS NOT NULL
                        GROUP BY location_id
                    ) sub_l
                ) AS location_counts,
                (
                    SELECT COALESCE(jsonb_agg(DISTINCT category), '[]'::jsonb)
                    FROM transactions
                    WHERE account_id = :account_id
                      AND (occurred_at < :eval_occurred_at OR (occurred_at = :eval_occurred_at AND id < :eval_id))
                      AND category IS NOT NULL
                ) AS categories;
            """
        )
        ent_res = (await session.execute(ent_stmt, params)).mappings().one()

        raw_device_counts = ent_res["device_counts"] or {}
        device_tx_counts: dict[uuid.UUID, int] = {
            uuid.UUID(k): int(v) for k, v in raw_device_counts.items()
        }

        raw_merchant_counts = ent_res["merchant_counts"] or {}
        merchant_tx_counts: dict[uuid.UUID, int] = {
            uuid.UUID(k): int(v) for k, v in raw_merchant_counts.items()
        }

        raw_location_counts = ent_res["location_counts"] or {}
        location_tx_counts: dict[uuid.UUID, int] = {
            uuid.UUID(k): int(v) for k, v in raw_location_counts.items()
        }

        raw_categories = ent_res["categories"] or []
        seen_categories: set[str] = {str(c) for c in raw_categories}

        return LifetimeBaselineSummary(
            count=count,
            mean=mean,
            stddev=stddev,
            median=median,
            total_lifetime_count=int(tot_count),
            seen_devices=frozenset(device_tx_counts.keys()),
            seen_merchants=frozenset(merchant_tx_counts.keys()),
            seen_locations=frozenset(location_tx_counts.keys()),
            seen_categories=frozenset(seen_categories),
            device_tx_counts=device_tx_counts,
            merchant_tx_counts=merchant_tx_counts,
            location_tx_counts=location_tx_counts,
        )

    async def assemble_evaluation_context(
        self, session: AsyncSession, transaction_id: uuid.UUID
    ) -> EvaluationContext:
        """Assemble complete point-in-time evaluation context for a transaction."""
        eval_tx = await self.get_transaction_by_id(session, transaction_id)
        if eval_tx is None:
            raise NotFoundError(
                message=f"Transaction '{transaction_id}' was not found.",
                code="TRANSACTION_NOT_FOUND",
                details={"transaction_id": str(transaction_id)},
            )

        account = await self.get_account_profile(session, eval_tx.account_id)
        if account is None:
            raise NotFoundError(
                message=f"Account '{eval_tx.account_id}' referenced by transaction was not found.",
                code="ACCOUNT_NOT_FOUND",
                details={"account_id": str(eval_tx.account_id)},
            )

        bounded_txs = await self.get_bounded_historical_transactions(
            session,
            account_id=eval_tx.account_id,
            eval_occurred_at=eval_tx.occurred_at,
            eval_id=eval_tx.id,
            window_seconds=CATEGORY_WINDOW_30D_SECONDS,
        )

        lifetime_summary = await self.get_lifetime_baseline_summary(
            session,
            account_id=eval_tx.account_id,
            currency=eval_tx.currency,
            direction=eval_tx.direction,
            eval_occurred_at=eval_tx.occurred_at,
            eval_id=eval_tx.id,
        )

        return EvaluationContext(
            evaluated_transaction=eval_tx,
            account_profile=account,
            bounded_transactions=bounded_txs,
            lifetime_summary=lifetime_summary,
        )
