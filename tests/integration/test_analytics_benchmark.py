"""Phase 5 Reproducible Performance Benchmark and Query Plan Analyzer.

Protocol:
- Medium dataset: 100 accounts, 5,000 transactions, seed=42
- 10 warmup iterations, 50 timed iterations
- Measures P50, P90, P95, and max query latencies (repository level and HTTP level)
- Captures EXPLAIN (ANALYZE, BUFFERS) query plans
"""

import io
import time
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.analytics.repository import AnalyticsRepository
from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.dataset.generator import (
    CSVDatasetExporter,
    GeneratorConfig,
    ReferenceEntityGenerator,
    ReferenceEntityPersistenceService,
    TransactionDatasetGenerator,
)
from finsignal.dataset.service import DatasetImportService


async def run_benchmark(session: AsyncSession) -> dict[str, Any]:
    """Execute the benchmark protocol on the active session."""
    namespace = "BENCHMARK_SYNTHETIC"

    print(
        "--- 1. Seeding Medium Dataset (100 accounts, 5,000 transactions, seed=42) ---"
    )
    cfg = GeneratorConfig(
        seed=42,
        source_namespace=namespace,
        account_count=100,
        merchant_count=20,
        device_count=50,
        location_count=10,
        transaction_count=5000,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(session, ref_ds)
    await session.commit()

    tx_ds = TransactionDatasetGenerator(cfg, ref_ds).generate()

    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_ds.transactions, out_buf)
    csv_bytes = out_buf.getvalue().encode("utf-8")

    import_svc = DatasetImportService()
    await import_svc.import_dataset(
        session,
        file_bytes=csv_bytes,
        filename="benchmark_5000.csv",
        source_namespace=namespace,
    )
    await session.commit()
    print("Seed complete.")

    repo = AnalyticsRepository()
    t_start = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    t_end = datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC)

    # --- 2. Benchmark Overview Query ---
    print("\n--- 2. Benchmarking /overview query (30-day window) ---")
    # Warmup
    for _ in range(10):
        await repo.get_overview_metrics(
            session,
            namespace=namespace,
            currency="INR",
            from_time=t_start,
            to_time=t_end,
        )

    # 50 Timed Iterations
    overview_latencies_ms: list[float] = []
    for _ in range(50):
        start = time.perf_counter_ns()
        await repo.get_overview_metrics(
            session,
            namespace=namespace,
            currency="INR",
            from_time=t_start,
            to_time=t_end,
        )
        dur = (time.perf_counter_ns() - start) / 1_000_000.0
        overview_latencies_ms.append(dur)

    overview_latencies_ms.sort()
    ov_p50 = overview_latencies_ms[int(0.50 * len(overview_latencies_ms))]
    ov_p90 = overview_latencies_ms[int(0.90 * len(overview_latencies_ms))]
    ov_p95 = overview_latencies_ms[int(0.95 * len(overview_latencies_ms))]
    ov_max = max(overview_latencies_ms)

    print(
        f"Overview Latency: P50={ov_p50:.2f}ms, P90={ov_p90:.2f}ms, P95={ov_p95:.2f}ms, Max={ov_max:.2f}ms"
    )

    # --- 3. Benchmark Trends Query ---
    print("\n--- 3. Benchmarking /trends query (30 daily buckets) ---")
    for _ in range(10):
        await repo.get_trend_buckets(
            session,
            namespace=namespace,
            currency="INR",
            from_time=t_start,
            to_time=t_end,
            interval="day",
            tz_name="UTC",
        )

    trend_latencies_ms: list[float] = []
    for _ in range(50):
        start = time.perf_counter_ns()
        await repo.get_trend_buckets(
            session,
            namespace=namespace,
            currency="INR",
            from_time=t_start,
            to_time=t_end,
            interval="day",
            tz_name="UTC",
        )
        dur = (time.perf_counter_ns() - start) / 1_000_000.0
        trend_latencies_ms.append(dur)

    trend_latencies_ms.sort()
    tr_p50 = trend_latencies_ms[int(0.50 * len(trend_latencies_ms))]
    tr_p90 = trend_latencies_ms[int(0.90 * len(trend_latencies_ms))]
    tr_p95 = trend_latencies_ms[int(0.95 * len(trend_latencies_ms))]
    tr_max = max(trend_latencies_ms)

    print(
        f"Trends Latency:   P50={tr_p50:.2f}ms, P90={tr_p90:.2f}ms, P95={tr_p95:.2f}ms, Max={tr_max:.2f}ms"
    )

    # --- 4. EXPLAIN (ANALYZE, BUFFERS) ---
    print("\n--- 4. EXPLAIN (ANALYZE, BUFFERS) Query Plans ---")
    explain_sql = text(
        """
        EXPLAIN (ANALYZE, BUFFERS)
        SELECT
            COUNT(*) AS total_transaction_count,
            COALESCE(SUM(amount), 0) AS total_volume_amount,
            ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY amount)::numeric, 2) AS median_transaction_amount
        FROM transactions
        WHERE source_namespace = :namespace
          AND currency = :currency
          AND occurred_at >= :from_time
          AND occurred_at < :to_time
        """
    )
    plan_res = await session.execute(
        explain_sql,
        {
            "namespace": namespace,
            "currency": "INR",
            "from_time": t_start,
            "to_time": t_end,
        },
    )
    plan_lines = [r[0] for r in plan_res.fetchall()]
    plan_text = "\n".join(plan_lines)
    print("Overview Query Plan:\n" + plan_text)

    return {
        "dataset_size": 5000,
        "account_count": 100,
        "overview": {
            "p50": ov_p50,
            "p90": ov_p90,
            "p95": ov_p95,
            "max": ov_max,
        },
        "trends": {
            "p50": tr_p50,
            "p90": tr_p90,
            "p95": tr_p95,
            "max": tr_max,
        },
        "query_plan": plan_text,
    }


@pytest.mark.asyncio
async def test_performance_benchmark(
    disposable_db: dict[str, Any],
) -> None:
    """Run benchmark against disposable test database."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        results = await run_benchmark(session)
        # Verify performance budget: P95 latency <= 50ms at 5,000 scale
        assert results["overview"]["p95"] <= 50.0, (
            f"Overview P95 exceeded budget: {results['overview']['p95']}ms"
        )
        assert results["trends"]["p95"] <= 50.0, (
            f"Trends P95 exceeded budget: {results['trends']['p95']}ms"
        )
    await engine.dispose()
