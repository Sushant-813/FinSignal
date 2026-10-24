"""PostgreSQL aggregation repository for financial analytics (Phase 5)."""

import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account


class AnalyticsRepository:
    """Handles PostgreSQL financial aggregation queries using async SQLAlchemy."""

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

    async def get_account_by_id(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> Account | None:
        """Retrieve an account by its primary key UUID."""
        stmt = select(Account).where(Account.id == account_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_available_currencies(
        self, session: AsyncSession, *, account_id: uuid.UUID, namespace: str
    ) -> list[str]:
        """List distinct currencies transacted by an account in its namespace."""
        stmt = text(
            """
            SELECT DISTINCT currency
            FROM transactions
            WHERE account_id = :account_id
              AND source_namespace = :namespace
            ORDER BY currency ASC
            """
        )
        result = await session.execute(
            stmt, {"account_id": account_id, "namespace": namespace}
        )
        return [row[0] for row in result.fetchall()]

    async def get_overview_metrics(
        self,
        session: AsyncSession,
        *,
        namespace: str,
        currency: str,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        account_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Execute single-roundtrip financial macro-aggregates over [from_time, to_time)."""
        conditions = [
            "source_namespace = :namespace",
            "currency = :currency",
        ]
        params: dict[str, Any] = {
            "namespace": namespace,
            "currency": currency,
        }
        if account_id is not None:
            conditions.append("account_id = :account_id")
            params["account_id"] = account_id
        if from_time is not None:
            conditions.append("occurred_at >= :from_time")
            params["from_time"] = from_time
        if to_time is not None:
            conditions.append("occurred_at < :to_time")
            params["to_time"] = to_time

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                COUNT(*) AS total_transaction_count,
                COUNT(*) FILTER (WHERE direction = 'DEBIT') AS debit_transaction_count,
                COUNT(*) FILTER (WHERE direction = 'CREDIT') AS credit_transaction_count,
                COALESCE(SUM(amount), 0) AS total_volume_amount,
                COALESCE(SUM(amount) FILTER (WHERE direction = 'DEBIT'), 0) AS total_debit_amount,
                COALESCE(SUM(amount) FILTER (WHERE direction = 'CREDIT'), 0) AS total_credit_amount,
                COALESCE(SUM(amount) FILTER (WHERE direction = 'CREDIT'), 0) -
                COALESCE(SUM(amount) FILTER (WHERE direction = 'DEBIT'), 0) AS net_cash_flow,
                ROUND(AVG(amount), 2) AS average_transaction_amount,
                ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY amount)::numeric, 2) AS median_transaction_amount,
                ROUND(AVG(amount) FILTER (WHERE direction = 'DEBIT'), 2) AS debit_average_amount,
                ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY amount) FILTER (WHERE direction = 'DEBIT')::numeric, 2) AS debit_median_amount,
                ROUND(AVG(amount) FILTER (WHERE direction = 'CREDIT'), 2) AS credit_average_amount,
                ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY amount) FILTER (WHERE direction = 'CREDIT')::numeric, 2) AS credit_median_amount,
                MIN(amount) AS min_transaction_amount,
                MAX(amount) AS max_transaction_amount
            FROM transactions
            WHERE {where_clause}
        """
        res = await session.execute(text(query), params)
        row = res.mappings().one()
        return dict(row)

    async def get_trend_buckets(
        self,
        session: AsyncSession,
        *,
        namespace: str,
        currency: str,
        from_time: datetime,
        to_time: datetime,
        interval: str,
        tz_name: str,
        account_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Generate contiguous zero-filled calendar trend buckets in target timezone."""
        if interval not in ("day", "month"):
            raise ValueError(f"Invalid interval: {interval}")
        interval_step = f"1 {interval}"
        tx_conditions = [
            "source_namespace = :namespace",
            "currency = :currency",
            "occurred_at >= :from_time",
            "occurred_at < :to_time",
        ]
        params: dict[str, Any] = {
            "interval": interval,
            "tz": tz_name,
            "namespace": namespace,
            "currency": currency,
            "from_time": from_time,
            "to_time": to_time,
        }
        if account_id is not None:
            tx_conditions.append("account_id = :account_id")
            params["account_id"] = account_id

        tx_where = " AND ".join(tx_conditions)

        query = f"""
            WITH calendar_bounds AS (
                SELECT
                    (date_trunc(:interval, :from_time, :tz) AT TIME ZONE :tz) AS start_wall,
                    (date_trunc(:interval, :to_time, :tz) AT TIME ZONE :tz) AS end_wall
            ),
            series AS (
                SELECT (g AT TIME ZONE :tz) AS bucket_start
                FROM calendar_bounds b,
                     generate_series(b.start_wall, b.end_wall, '{interval_step}'::interval) g
                WHERE (g AT TIME ZONE :tz) < :to_time
            ),
            tx_filtered AS (
                SELECT
                    date_trunc(:interval, occurred_at, :tz) AS tx_bucket,
                    direction,
                    amount
                FROM transactions
                WHERE {tx_where}
            )
            SELECT
                s.bucket_start,
                COUNT(t.amount) AS transaction_count,
                COUNT(t.amount) FILTER (WHERE t.direction = 'DEBIT') AS debit_count,
                COUNT(t.amount) FILTER (WHERE t.direction = 'CREDIT') AS credit_count,
                COALESCE(SUM(t.amount) FILTER (WHERE t.direction = 'DEBIT'), 0) AS total_debit_amount,
                COALESCE(SUM(t.amount) FILTER (WHERE t.direction = 'CREDIT'), 0) AS total_credit_amount,
                COALESCE(SUM(t.amount) FILTER (WHERE t.direction = 'CREDIT'), 0) -
                COALESCE(SUM(t.amount) FILTER (WHERE t.direction = 'DEBIT'), 0) AS net_cash_flow
            FROM series s
            LEFT JOIN tx_filtered t ON s.bucket_start = t.tx_bucket
            GROUP BY s.bucket_start
            ORDER BY s.bucket_start ASC
        """
        res = await session.execute(text(query), params)
        return [dict(row) for row in res.mappings().all()]

    async def get_category_distribution(
        self,
        session: AsyncSession,
        *,
        namespace: str,
        currency: str,
        direction: str,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        account_id: uuid.UUID | None = None,
    ) -> tuple[Decimal, list[dict[str, Any]]]:
        """Aggregate spending by category with deterministic tie-breaking.

        Returns total directional amount and category breakdown rows.
        """
        conditions = [
            "source_namespace = :namespace",
            "currency = :currency",
            "direction = :direction",
        ]
        params: dict[str, Any] = {
            "namespace": namespace,
            "currency": currency,
            "direction": direction,
        }
        if account_id is not None:
            conditions.append("account_id = :account_id")
            params["account_id"] = account_id
        if from_time is not None:
            conditions.append("occurred_at >= :from_time")
            params["from_time"] = from_time
        if to_time is not None:
            conditions.append("occurred_at < :to_time")
            params["to_time"] = to_time

        where_clause = " AND ".join(conditions)

        stmt_total = f"""
            SELECT COALESCE(SUM(amount), 0) AS total_amount
            FROM transactions
            WHERE {where_clause}
        """
        total_res = await session.execute(text(stmt_total), params)
        total_directional_amount = Decimal(str(total_res.scalar_one()))

        stmt_cats = f"""
            SELECT
                COALESCE(category, 'UNCATEGORIZED') AS category_name,
                COUNT(*) AS transaction_count,
                SUM(amount) AS total_amount,
                ROUND(AVG(amount), 2) AS average_amount
            FROM transactions
            WHERE {where_clause}
            GROUP BY COALESCE(category, 'UNCATEGORIZED')
            ORDER BY total_amount DESC, category_name ASC
        """
        cats_res = await session.execute(text(stmt_cats), params)
        cats = [dict(row) for row in cats_res.mappings().all()]
        return total_directional_amount, cats

    async def get_merchant_distribution(
        self,
        session: AsyncSession,
        *,
        namespace: str,
        currency: str,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        sort_by: str = "amount",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Decimal, Decimal, Decimal, list[dict[str, Any]]]:
        """Rank merchants by debit volume or frequency with dual denominator metrics."""
        conditions = [
            "source_namespace = :namespace",
            "currency = :currency",
        ]
        params_totals: dict[str, Any] = {
            "namespace": namespace,
            "currency": currency,
        }
        if from_time is not None:
            conditions.append("occurred_at >= :from_time")
            params_totals["from_time"] = from_time
        if to_time is not None:
            conditions.append("occurred_at < :to_time")
            params_totals["to_time"] = to_time

        where_totals = " AND ".join(conditions)

        stmt_totals = f"""
            SELECT
                COALESCE(SUM(amount) FILTER (WHERE direction = 'DEBIT'), 0) AS total_debit,
                COALESCE(SUM(amount) FILTER (WHERE direction = 'DEBIT' AND merchant_id IS NOT NULL), 0) AS total_merchant_debit
            FROM transactions
            WHERE {where_totals}
        """
        totals_res = await session.execute(text(stmt_totals), params_totals)
        tot_row = totals_res.mappings().one()
        total_debit = Decimal(str(tot_row["total_debit"]))
        total_merchant_debit = Decimal(str(tot_row["total_merchant_debit"]))
        non_merchant_debit = total_debit - total_merchant_debit

        m_conditions = [
            "t.source_namespace = :namespace",
            "t.currency = :currency",
            "t.direction = 'DEBIT'",
        ]
        params_merchants = {
            **params_totals,
            "sort_by": sort_by,
            "limit": limit,
            "offset": offset,
        }
        if from_time is not None:
            m_conditions.append("t.occurred_at >= :from_time")
        if to_time is not None:
            m_conditions.append("t.occurred_at < :to_time")

        where_merchants = " AND ".join(m_conditions)

        stmt_merchants = f"""
            SELECT
                m.id AS merchant_id,
                m.merchant_name,
                m.merchant_category,
                COUNT(t.id) AS transaction_count,
                SUM(t.amount) AS total_amount,
                ROUND(AVG(t.amount), 2) AS average_amount
            FROM transactions t
            JOIN merchants m ON t.merchant_id = m.id
            WHERE {where_merchants}
            GROUP BY m.id, m.merchant_name, m.merchant_category
            ORDER BY
                CASE WHEN :sort_by = 'amount' THEN SUM(t.amount) END DESC,
                CASE WHEN :sort_by = 'count' THEN COUNT(t.id) END DESC,
                m.id ASC
            LIMIT :limit OFFSET :offset
        """
        merch_res = await session.execute(text(stmt_merchants), params_merchants)
        merchants = [dict(row) for row in merch_res.mappings().all()]
        return total_debit, total_merchant_debit, non_merchant_debit, merchants

    async def get_account_activity_details(
        self,
        session: AsyncSession,
        *,
        account_id: uuid.UUID,
        namespace: str,
        currency: str,
        tz_name: str,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Retrieve account activity timestamps, active days, top categories, and top merchants."""
        conditions = [
            "account_id = :account_id",
            "source_namespace = :namespace",
            "currency = :currency",
        ]
        params: dict[str, Any] = {
            "account_id": account_id,
            "namespace": namespace,
            "currency": currency,
            "tz": tz_name,
        }
        if from_time is not None:
            conditions.append("occurred_at >= :from_time")
            params["from_time"] = from_time
        if to_time is not None:
            conditions.append("occurred_at < :to_time")
            params["to_time"] = to_time

        where_clause = " AND ".join(conditions)

        # 1. First/last transaction and active calendar days
        stmt_temporal = f"""
            SELECT
                MIN(occurred_at) AS first_tx,
                MAX(occurred_at) AS last_tx,
                COUNT(DISTINCT date_trunc('day', occurred_at, :tz)) AS active_days
            FROM transactions
            WHERE {where_clause}
        """
        temp_res = await session.execute(text(stmt_temporal), params)
        temp_row = temp_res.mappings().one()

        # 2. Top 5 debit categories
        cat_conditions = [
            *conditions,
            "direction = 'DEBIT'",
        ]
        cat_where = " AND ".join(cat_conditions)

        stmt_top_cats = f"""
            SELECT
                COALESCE(category, 'UNCATEGORIZED') AS category_name,
                COUNT(*) AS transaction_count,
                SUM(amount) AS total_amount
            FROM transactions
            WHERE {cat_where}
            GROUP BY COALESCE(category, 'UNCATEGORIZED')
            ORDER BY total_amount DESC, category_name ASC
            LIMIT 5
        """
        cats_res = await session.execute(text(stmt_top_cats), params)
        top_cats = [dict(row) for row in cats_res.mappings().all()]

        # 3. Top 5 debit merchants
        t_conditions = [
            "t.account_id = :account_id",
            "t.source_namespace = :namespace",
            "t.currency = :currency",
            "t.direction = 'DEBIT'",
        ]
        if from_time is not None:
            t_conditions.append("t.occurred_at >= :from_time")
        if to_time is not None:
            t_conditions.append("t.occurred_at < :to_time")

        t_where = " AND ".join(t_conditions)

        stmt_top_merchants = f"""
            SELECT
                m.id AS merchant_id,
                m.merchant_name,
                m.merchant_category,
                COUNT(t.id) AS transaction_count,
                SUM(t.amount) AS total_amount
            FROM transactions t
            JOIN merchants m ON t.merchant_id = m.id
            WHERE {t_where}
            GROUP BY m.id, m.merchant_name, m.merchant_category
            ORDER BY total_amount DESC, m.id ASC
            LIMIT 5
        """
        merch_res = await session.execute(text(stmt_top_merchants), params)
        top_merchants = [dict(row) for row in merch_res.mappings().all()]

        return {
            "first_transaction_at": temp_row["first_tx"],
            "last_transaction_at": temp_row["last_tx"],
            "active_days_count": int(temp_row["active_days"]),
            "top_categories": top_cats,
            "top_merchants": top_merchants,
        }

    async def get_unusual_spending_outliers(
        self,
        session: AsyncSession,
        *,
        account_id: uuid.UUID,
        namespace: str,
        currency: str,
        multiplier: Decimal,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Decimal | None, Decimal | None, int, list[dict[str, Any]]]:
        """Compute reporting-window debit median and retrieve matching statistical outliers.

        Returns (median_debit, threshold_amount, total_outlier_count_before_pagination, paginated_items).
        """
        conditions = [
            "account_id = :account_id",
            "source_namespace = :namespace",
            "currency = :currency",
            "direction = 'DEBIT'",
        ]
        params_base: dict[str, Any] = {
            "account_id": account_id,
            "namespace": namespace,
            "currency": currency,
        }
        if from_time is not None:
            conditions.append("occurred_at >= :from_time")
            params_base["from_time"] = from_time
        if to_time is not None:
            conditions.append("occurred_at < :to_time")
            params_base["to_time"] = to_time

        where_base = " AND ".join(conditions)

        # 1. Compute exact median over the requested window
        stmt_median = f"""
            SELECT
                ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY amount)::numeric, 2) AS median_debit
            FROM transactions
            WHERE {where_base}
        """
        med_res = await session.execute(text(stmt_median), params_base)
        med_val = med_res.scalar_one_or_none()
        if med_val is None:
            return None, None, 0, []

        median_debit = Decimal(str(med_val))
        threshold = (median_debit * multiplier).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # 2. Total outlier count before pagination
        stmt_count = f"""
            SELECT COUNT(*) AS total_outlier_count
            FROM transactions
            WHERE {where_base}
              AND amount >= :threshold
        """
        count_res = await session.execute(
            text(stmt_count), {**params_base, "threshold": threshold}
        )
        total_outliers = int(count_res.scalar_one())

        if total_outliers == 0:
            return median_debit, threshold, 0, []

        # 3. Retrieve paginated outliers with deterministic tie-breaking
        stmt_rows = f"""
            SELECT
                id AS transaction_id,
                external_transaction_id,
                occurred_at,
                amount,
                currency,
                transaction_type,
                direction,
                category,
                ROUND((amount / :median_debit), 2) AS deviation_ratio
            FROM transactions
            WHERE {where_base}
              AND amount >= :threshold
            ORDER BY amount DESC, occurred_at DESC, transaction_id ASC
            LIMIT :limit OFFSET :offset
        """
        params_rows = {
            **params_base,
            "median_debit": median_debit,
            "threshold": threshold,
            "limit": limit,
            "offset": offset,
        }
        rows_res = await session.execute(text(stmt_rows), params_rows)
        items = [dict(row) for row in rows_res.mappings().all()]

        return median_debit, threshold, total_outliers, items
