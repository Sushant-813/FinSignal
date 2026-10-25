"""Phase 6 Feature Engineering Reproducible Performance Benchmark and Query Plan Analyzer.

Protocol:
- Medium dataset: 100 accounts, 5,000 transactions, seed=42
- Evaluates:
  1. Single-transaction evaluation latency percentiles (P50, P90, P95).
  2. Batch extraction runtime on 5,000 transactions.
  3. Online-versus-batch numerical agreement.
  4. Memory consumption of batch state.
  5. PostgreSQL EXPLAIN (ANALYZE, BUFFERS) execution plans.
"""

import io
import time
import tracemalloc
from datetime import UTC, timedelta
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
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
from finsignal.features.schemas import AccountProfileDTO
from finsignal.features.service import FeatureService
from finsignal.transactions.models import Transaction


async def run_feature_benchmark(session: AsyncSession) -> dict[str, Any]:
    """Execute the Phase 6 feature benchmark protocol on the active session."""
    namespace = "FEATURE_BENCHMARK_NS"

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
        filename="benchmark_transactions.csv",
        source_namespace=namespace,
    )
    await session.commit()

    # Query all imported accounts and transactions
    acc_stmt = select(Account).where(Account.source_namespace == namespace)
    accounts = (await session.execute(acc_stmt)).scalars().all()
    accounts_map = {
        acc.id: AccountProfileDTO(
            id=acc.id,
            source_namespace=acc.source_namespace,
            home_location_id=acc.home_location_id,
            created_at=(
                acc.created_at.astimezone(UTC)
                if acc.created_at.tzinfo
                else acc.created_at.replace(tzinfo=UTC)
            ),
        )
        for acc in accounts
    }

    tx_stmt = (
        select(Transaction)
        .where(Transaction.source_namespace == namespace)
        .order_by(Transaction.occurred_at.asc(), Transaction.id.asc())
    )
    tx_models = (await session.execute(tx_stmt)).scalars().all()

    service = FeatureService()

    # 1. Benchmark Batch Extraction (5,000 transactions)
    # Warmup and memory measurement on 500 transactions
    tracemalloc.start()
    service.extract_batch(tx_models[:500], accounts_map)
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mem_mb = (peak_mem * 10) / (1024 * 1024)  # Extrapolated for 5,000 scale

    # Timed extraction of all 5,000 transactions without tracemalloc overhead
    t_batch_start = time.perf_counter()
    batch_results = service.extract_batch(tx_models, accounts_map)
    t_batch_end = time.perf_counter()
    batch_duration_sec = t_batch_end - t_batch_start

    # 2. Benchmark Single Evaluation Latency (50 sample iterations)
    sample_indices = [i * 100 for i in range(50)]
    latencies_ms: list[float] = []

    # Warmup
    for idx in sample_indices[:5]:
        await service.evaluate_transaction(session, tx_models[idx].id)

    for idx in sample_indices:
        t0 = time.perf_counter()
        await service.evaluate_transaction(session, tx_models[idx].id)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies_ms.sort()
    p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
    p90 = latencies_ms[int(len(latencies_ms) * 0.90)]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    max_lat = max(latencies_ms)

    # 3. Numerical Agreement Check on Sample Transactions
    for idx in sample_indices[:10]:
        single_res = await service.evaluate_transaction(session, tx_models[idx].id)
        batch_vec = batch_results[idx].features
        single_vec = single_res.features

        # Assert exact agreement on integer counts & categories
        assert single_vec.velocity_5m_count == batch_vec.velocity_5m_count
        assert single_vec.velocity_1h_count == batch_vec.velocity_1h_count
        assert single_vec.velocity_24h_count == batch_vec.velocity_24h_count
        assert single_vec.has_direction_baseline == batch_vec.has_direction_baseline
        assert single_vec.is_cold_start == batch_vec.is_cold_start
        assert single_vec.is_new_device == batch_vec.is_new_device
        assert single_vec.hour_of_day == batch_vec.hour_of_day
        assert single_vec.day_of_week == batch_vec.day_of_week

    # 4. PostgreSQL Query Plan Inspection: Bounded Historical Query
    sample_tx = tx_models[2500]
    eval_t = (
        sample_tx.occurred_at.astimezone(UTC)
        if sample_tx.occurred_at.tzinfo
        else sample_tx.occurred_at.replace(tzinfo=UTC)
    )
    window_start = eval_t - timedelta(days=30)

    explain_sql = text(
        """
        EXPLAIN (ANALYZE, BUFFERS)
        SELECT id, occurred_at, amount, currency, direction
        FROM transactions
        WHERE account_id = :account_id
          AND occurred_at >= :window_start
          AND occurred_at <= :eval_occurred_at
          AND NOT (occurred_at = :eval_occurred_at AND id >= :eval_id)
        ORDER BY occurred_at ASC, id ASC;
        """
    )
    plan_res = await session.execute(
        explain_sql,
        {
            "account_id": sample_tx.account_id,
            "window_start": window_start,
            "eval_occurred_at": eval_t,
            "eval_id": sample_tx.id,
        },
    )
    plan_text = "\n".join([r[0] for r in plan_res.fetchall()])

    return {
        "dataset_size": len(tx_models),
        "account_count": len(accounts),
        "batch_duration_sec": batch_duration_sec,
        "peak_mem_mb": peak_mem_mb,
        "single_eval": {
            "p50": p50,
            "p90": p90,
            "p95": p95,
            "max": max_lat,
        },
        "query_plan": plan_text,
    }


@pytest.mark.asyncio
async def test_feature_engineering_benchmark(
    disposable_db: dict[str, Any],
) -> None:
    """Run benchmark against disposable test database and verify empirical acceptance goals."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        results = await run_feature_benchmark(session)

        # Empirical acceptance goals
        print("\n[Feature Benchmark Results]")
        print(f"Batch 5,000 txs: {results['batch_duration_sec']:.3f}s")
        print(
            f"Single Eval P50: {results['single_eval']['p50']:.2f}ms, P90: {results['single_eval']['p90']:.2f}ms, P95: {results['single_eval']['p95']:.2f}ms"
        )
        print(f"Peak Memory: {results['peak_mem_mb']:.2f}MB")

        assert results["batch_duration_sec"] <= 10.0, (
            f"Batch extraction exceeded empirical budget: {results['batch_duration_sec']}s"
        )

        # Memory goal: peak memory <= 50 MB for batch processing
        assert results["peak_mem_mb"] <= 50.0, (
            f"Peak memory exceeded 50MB: {results['peak_mem_mb']}MB"
        )

        # Confirm query plan uses index scan on transactions
        assert (
            "ix_transactions_account_occurred" in results["query_plan"]
            or "Index Scan" in results["query_plan"]
            or "Bitmap Index Scan" in results["query_plan"]
        ), f"Expected index scan in query plan:\n{results['query_plan']}"

    await engine.dispose()
