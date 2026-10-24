"""Phase 5 Full-Scale Benchmark Execution (5,000 Accounts, 250,000 Transactions).

Measures:
- Repository-level query latency (P50, P90, P95, Max) over 50 iterations (10 warmups)
- HTTP-level endpoint latency (P50, P90, P95, Max) over 50 iterations (10 warmups)
- Detailed EXPLAIN (ANALYZE, BUFFERS) query plans
"""

import asyncio
import os
import time
from datetime import UTC, datetime
from decimal import Decimal

from dotenv import dotenv_values
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text

from finsignal.analytics.repository import AnalyticsRepository
from finsignal.auth.security import create_access_token
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.main import create_app
from finsignal.users.repository import UserRepository


def calc_percentiles(latencies: list[float]) -> dict[str, float]:
    """Compute P50, P90, P95, and Max from a list of latencies in ms."""
    s = sorted(latencies)
    n = len(s)
    return {
        "p50": s[int(0.50 * n)],
        "p90": s[int(0.90 * n)],
        "p95": s[int(0.95 * n)],
        "max": max(s),
    }


ENV_VALS = dotenv_values(".env") if os.path.exists(".env") else {}
DB_PW = ENV_VALS.get("POSTGRES_PASSWORD", "test_password")


async def main() -> None:
    settings = Settings(
        app_name="FinSignalFullBenchmark",
        environment="testing",
        database_host="127.0.0.1",
        database_port=5432,
        database_name="finsignal_test",
        database_user="postgres",
        database_password=SecretStr(DB_PW),
        _env_file=None,
    )

    engine, session_maker = create_db_resources(settings)
    repo = AnalyticsRepository()

    # Create / get an admin user and auth token for HTTP testing
    async with session_maker() as session:
        user_repo = UserRepository()
        admin_user = await user_repo.get_by_email(
            session, "benchmark_admin@example.com"
        )
        if not admin_user:
            from finsignal.auth.security import hash_password

            admin_user = await user_repo.create(
                session,
                email="benchmark_admin@example.com",
                password_hash=hash_password("BenchmarkAdmin123!"),
                role="ADMIN",
                is_active=True,
            )
            await session.commit()
        token = create_access_token(user_id=admin_user.id, settings=settings)

        # Find an active account with high transaction count
        acc_stmt = text(
            """
            SELECT account_id, COUNT(*) as cnt
            FROM transactions
            WHERE source_namespace = 'SYNTHETIC' AND currency = 'INR'
            GROUP BY account_id
            ORDER BY cnt DESC
            LIMIT 1
            """
        )
        acc_row = (await session.execute(acc_stmt)).mappings().one()
        sample_account_id = acc_row["account_id"]
        sample_account_tx_count = acc_row["cnt"]

    auth_headers = {"Authorization": f"Bearer {token}"}
    app = create_app(settings)

    # 30-day reporting window in the center of the dataset
    t_start = datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    namespace = "SYNTHETIC"
    currency = "INR"

    print(
        "================================================================================"
    )
    print(
        "FINSIGNAL PHASE 5 FULL-SCALE BENCHMARK (5,000 ACCOUNTS, 250,000 TRANSACTIONS)"
    )
    print(
        "================================================================================"
    )
    print(f"Reporting window: {t_start.isoformat()} to {t_end.isoformat()} (30 days)")
    print(
        f"Sample Account ID: {sample_account_id} (Transactions: {sample_account_tx_count})"
    )

    # Verify matching count in window
    async with session_maker() as session:
        count_res = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE source_namespace = :ns
                  AND currency = :curr
                  AND occurred_at >= :t_from
                  AND occurred_at < :t_to
                """
            ),
            {"ns": namespace, "curr": currency, "t_from": t_start, "t_to": t_end},
        )
        window_count = count_res.scalar_one()
        print(f"Matching transactions in 30-day window: {window_count:,}")

    # -------------------------------------------------------------------------
    # PART 1: REPOSITORY QUERY LATENCY (10 warmups, 50 timed iterations)
    # -------------------------------------------------------------------------
    print("\n--- PART 1: REPOSITORY QUERY LATENCY (PostgreSQL Engine) ---")

    async with session_maker() as session:
        # 1. Overview Query
        for _ in range(10):
            await repo.get_overview_metrics(
                session,
                namespace=namespace,
                currency=currency,
                from_time=t_start,
                to_time=t_end,
            )
        ov_repo_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            await repo.get_overview_metrics(
                session,
                namespace=namespace,
                currency=currency,
                from_time=t_start,
                to_time=t_end,
            )
            ov_repo_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        ov_repo_stats = calc_percentiles(ov_repo_latencies)
        print(
            f"1. Overview Query (30d):   P50={ov_repo_stats['p50']:.2f}ms | P90={ov_repo_stats['p90']:.2f}ms | P95={ov_repo_stats['p95']:.2f}ms | Max={ov_repo_stats['max']:.2f}ms"
        )

        # 2. Trends Query (30 daily buckets)
        for _ in range(10):
            await repo.get_trend_buckets(
                session,
                namespace=namespace,
                currency=currency,
                from_time=t_start,
                to_time=t_end,
                interval="day",
                tz_name="UTC",
            )
        tr_repo_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            await repo.get_trend_buckets(
                session,
                namespace=namespace,
                currency=currency,
                from_time=t_start,
                to_time=t_end,
                interval="day",
                tz_name="UTC",
            )
            tr_repo_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        tr_repo_stats = calc_percentiles(tr_repo_latencies)
        print(
            f"2. Daily Trends (30 bkt):  P50={tr_repo_stats['p50']:.2f}ms | P90={tr_repo_stats['p90']:.2f}ms | P95={tr_repo_stats['p95']:.2f}ms | Max={tr_repo_stats['max']:.2f}ms"
        )

        # 3. Categories Query
        for _ in range(10):
            await repo.get_category_distribution(
                session,
                namespace=namespace,
                currency=currency,
                direction="DEBIT",
                from_time=t_start,
                to_time=t_end,
            )
        cat_repo_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            await repo.get_category_distribution(
                session,
                namespace=namespace,
                currency=currency,
                direction="DEBIT",
                from_time=t_start,
                to_time=t_end,
            )
            cat_repo_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        cat_repo_stats = calc_percentiles(cat_repo_latencies)
        print(
            f"3. Categories (30d):       P50={cat_repo_stats['p50']:.2f}ms | P90={cat_repo_stats['p90']:.2f}ms | P95={cat_repo_stats['p95']:.2f}ms | Max={cat_repo_stats['max']:.2f}ms"
        )

        # 4. Merchants Query
        for _ in range(10):
            await repo.get_merchant_distribution(
                session,
                namespace=namespace,
                currency=currency,
                from_time=t_start,
                to_time=t_end,
                sort_by="amount",
                limit=20,
                offset=0,
            )
        mch_repo_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            await repo.get_merchant_distribution(
                session,
                namespace=namespace,
                currency=currency,
                from_time=t_start,
                to_time=t_end,
                sort_by="amount",
                limit=20,
                offset=0,
            )
            mch_repo_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        mch_repo_stats = calc_percentiles(mch_repo_latencies)
        print(
            f"4. Merchants (top 20):     P50={mch_repo_stats['p50']:.2f}ms | P90={mch_repo_stats['p90']:.2f}ms | P95={mch_repo_stats['p95']:.2f}ms | Max={mch_repo_stats['max']:.2f}ms"
        )

        # 5. Account Activity
        for _ in range(10):
            await repo.get_account_activity_details(
                session,
                account_id=sample_account_id,
                namespace=namespace,
                currency=currency,
                tz_name="UTC",
                from_time=t_start,
                to_time=t_end,
            )
        act_repo_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            await repo.get_account_activity_details(
                session,
                account_id=sample_account_id,
                namespace=namespace,
                currency=currency,
                tz_name="UTC",
                from_time=t_start,
                to_time=t_end,
            )
            act_repo_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        act_repo_stats = calc_percentiles(act_repo_latencies)
        print(
            f"5. Account Activity:       P50={act_repo_stats['p50']:.2f}ms | P90={act_repo_stats['p90']:.2f}ms | P95={act_repo_stats['p95']:.2f}ms | Max={act_repo_stats['max']:.2f}ms"
        )

        # 6. Unusual Spending
        for _ in range(10):
            await repo.get_unusual_spending_outliers(
                session,
                account_id=sample_account_id,
                namespace=namespace,
                currency=currency,
                multiplier=Decimal("2.0"),
                from_time=t_start,
                to_time=t_end,
                limit=50,
                offset=0,
            )
        out_repo_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            await repo.get_unusual_spending_outliers(
                session,
                account_id=sample_account_id,
                namespace=namespace,
                currency=currency,
                multiplier=Decimal("2.0"),
                from_time=t_start,
                to_time=t_end,
                limit=50,
                offset=0,
            )
            out_repo_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        out_repo_stats = calc_percentiles(out_repo_latencies)
        print(
            f"6. Unusual Spending:       P50={out_repo_stats['p50']:.2f}ms | P90={out_repo_stats['p90']:.2f}ms | P95={out_repo_stats['p95']:.2f}ms | Max={out_repo_stats['max']:.2f}ms"
        )

    # -------------------------------------------------------------------------
    # PART 2: HTTP ENDPOINT LATENCY (FastAPI + ASGI Client)
    # -------------------------------------------------------------------------
    print("\n--- PART 2: HTTP ENDPOINT LATENCY (FastAPI Router Overhead) ---")
    t_start_iso = t_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    t_end_iso = t_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Overview HTTP
        url_ov = f"/api/v1/analytics/overview?source_namespace={namespace}&currency={currency}&from_time={t_start_iso}&to_time={t_end_iso}"
        for _ in range(10):
            r = await client.get(url_ov, headers=auth_headers)
            assert r.status_code == 200, f"Overview warm-up failed: {r.text}"
        ov_http_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            res = await client.get(url_ov, headers=auth_headers)
            assert res.status_code == 200
            ov_http_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        ov_http_stats = calc_percentiles(ov_http_latencies)
        print(
            f"1. GET /overview (HTTP):    P50={ov_http_stats['p50']:.2f}ms | P90={ov_http_stats['p90']:.2f}ms | P95={ov_http_stats['p95']:.2f}ms | Max={ov_http_stats['max']:.2f}ms"
        )

        # 2. Trends HTTP
        url_tr = f"/api/v1/analytics/trends?source_namespace={namespace}&currency={currency}&from_time={t_start_iso}&to_time={t_end_iso}&interval=day"
        for _ in range(10):
            r = await client.get(url_tr, headers=auth_headers)
            assert r.status_code == 200, f"Trends warm-up failed: {r.text}"
        tr_http_latencies: list[float] = []
        for _ in range(50):
            start = time.perf_counter_ns()
            res = await client.get(url_tr, headers=auth_headers)
            assert res.status_code == 200
            tr_http_latencies.append((time.perf_counter_ns() - start) / 1_000_000.0)
        tr_http_stats = calc_percentiles(tr_http_latencies)
        print(
            f"2. GET /trends (HTTP):      P50={tr_http_stats['p50']:.2f}ms | P90={tr_http_stats['p90']:.2f}ms | P95={tr_http_stats['p95']:.2f}ms | Max={tr_http_stats['max']:.2f}ms"
        )

    # -------------------------------------------------------------------------
    # PART 3: EXPLAIN (ANALYZE, BUFFERS) PLANS
    # -------------------------------------------------------------------------
    print("\n--- PART 3: QUERY EXECUTION PLANS (EXPLAIN ANALYZE, BUFFERS) ---")
    async with session_maker() as session:
        # Overview Explain
        sql_ov_explain = text(
            """
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT
                COUNT(*) AS total_transaction_count,
                COUNT(*) FILTER (WHERE direction = 'DEBIT') AS debit_transaction_count,
                COUNT(*) FILTER (WHERE direction = 'CREDIT') AS credit_transaction_count,
                COALESCE(SUM(amount), 0) AS total_volume_amount,
                COALESCE(SUM(amount) FILTER (WHERE direction = 'DEBIT'), 0) AS total_debit_amount,
                COALESCE(SUM(amount) FILTER (WHERE direction = 'CREDIT'), 0) AS total_credit_amount,
                ROUND(AVG(amount), 2) AS average_transaction_amount,
                ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY amount)::numeric, 2) AS median_transaction_amount
            FROM transactions
            WHERE source_namespace = :namespace
              AND currency = :currency
              AND occurred_at >= :from_time
              AND occurred_at < :to_time
            """
        )
        ov_plan_rows = (
            await session.execute(
                sql_ov_explain,
                {
                    "namespace": namespace,
                    "currency": currency,
                    "from_time": t_start,
                    "to_time": t_end,
                },
            )
        ).fetchall()
        print("\n[Overview Query Plan (250,000 scale)]:")
        print("\n".join(r[0] for r in ov_plan_rows))

        # Trends Explain
        sql_tr_explain = text(
            """
            EXPLAIN (ANALYZE, BUFFERS)
            WITH calendar_bounds AS (
                SELECT
                    (date_trunc('day', :from_time, 'UTC') AT TIME ZONE 'UTC') AS start_wall,
                    (date_trunc('day', :to_time, 'UTC') AT TIME ZONE 'UTC') AS end_wall
            ),
            series AS (
                SELECT (g AT TIME ZONE 'UTC') AS bucket_start
                FROM calendar_bounds b,
                     generate_series(b.start_wall, b.end_wall, '1 day'::interval) g
                WHERE (g AT TIME ZONE 'UTC') < :to_time
            ),
            tx_filtered AS (
                SELECT
                    date_trunc('day', occurred_at, 'UTC') AS tx_bucket,
                    direction,
                    amount
                FROM transactions
                WHERE source_namespace = :namespace
                  AND currency = :currency
                  AND occurred_at >= :from_time
                  AND occurred_at < :to_time
            )
            SELECT
                s.bucket_start,
                COUNT(t.amount) AS transaction_count,
                COALESCE(SUM(t.amount) FILTER (WHERE t.direction = 'DEBIT'), 0) AS total_debit_amount
            FROM series s
            LEFT JOIN tx_filtered t ON s.bucket_start = t.tx_bucket
            GROUP BY s.bucket_start
            ORDER BY s.bucket_start ASC
            """
        )
        tr_plan_rows = (
            await session.execute(
                sql_tr_explain,
                {
                    "namespace": namespace,
                    "currency": currency,
                    "from_time": t_start,
                    "to_time": t_end,
                },
            )
        ).fetchall()
        print("\n[Daily Trends Query Plan (250,000 scale)]:")
        print("\n".join(r[0] for r in tr_plan_rows))

    print(
        "\n================================================================================"
    )
    print("BENCHMARK COMPLETED SUCCESSFULLY")
    print(
        "================================================================================"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
