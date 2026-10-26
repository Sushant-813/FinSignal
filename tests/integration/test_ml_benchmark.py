"""Performance benchmarks for Phase 7 ML anomaly detection workflow.

Measures:
1. Feature vectorization latency (N=1,000).
2. Pure model scoring latency (single item P50, P90, P95).
3. Pure batch scoring throughput (transactions / second).
4. Model training duration (N=5,000 samples).
5. End-to-end online inference latency (including feature extraction and DB lookups).
"""

import io
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC
from typing import Any

import numpy as np
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
from finsignal.dataset.models import DatasetVersion
from finsignal.dataset.service import DatasetImportService
from finsignal.features.schemas import AccountProfileDTO, FeatureVector
from finsignal.ml.model import IsolationForestModel
from finsignal.ml.registry import ModelArtifactStore
from finsignal.ml.service import MLService
from finsignal.ml.vectorizer import FeatureVectorizer
from finsignal.transactions.models import Transaction


@pytest.fixture
async def async_session(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound to the disposable test database."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        yield session
        try:
            await session.rollback()
            await session.execute(
                text(
                    "TRUNCATE TABLE model_versions, transactions, dataset_imports, "
                    "dataset_versions, account_devices, accounts, merchants, devices, locations CASCADE;"
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


def _make_dummy_vector(idx: int) -> FeatureVector:
    return FeatureVector(
        amount=100.0 + (idx % 50),
        amount_log=4.6,
        account_age_days=30.0,
        velocity_5m_count=1,
        velocity_1h_count=2,
        velocity_24h_count=5,
        velocity_5m_amount=100.0,
        velocity_1h_amount=200.0,
        velocity_24h_amount=500.0,
        amount_vs_mean_ratio=1.0,
        amount_vs_median_ratio=1.0,
        amount_zscore=0.0,
        is_amount_different_from_constant_baseline=0,
        has_direction_baseline=1,
        has_zero_variance_baseline=0,
        is_cold_start=0,
        has_device=1,
        is_new_device=0,
        device_tx_count=10,
        has_merchant=1,
        is_new_merchant=0,
        merchant_tx_count=5,
        has_location=1,
        is_home_location=1,
        is_new_location=0,
        location_tx_count=8,
        location_frequency=0.8,
        has_category=1,
        is_new_category=0,
        category_spend_share_30d=0.45,
        hour_of_day=14,
        day_of_week=2,
        is_weekend=0,
        is_unusual_hour=0,
    )


def test_benchmark_vectorization_latency() -> None:
    """Benchmark conversion of FeatureVector instances into (N, 34) numpy matrix."""
    n_samples = 1000
    vectors = [_make_dummy_vector(i) for i in range(n_samples)]

    start = time.perf_counter()
    matrix = FeatureVectorizer.to_numpy(vectors)
    elapsed = time.perf_counter() - start

    assert matrix.shape == (n_samples, 34)
    per_item_us = (elapsed / n_samples) * 1_000_000
    print(
        f"\n[BENCHMARK] Vectorization ({n_samples} items): total={elapsed * 1000:.2f}ms, per-item={per_item_us:.2f}us"
    )
    assert elapsed < 1.0  # Sanity bound


def test_benchmark_pure_model_scoring() -> None:
    """Benchmark pure IsolationForestModel scoring latency and batch throughput."""
    n_train = 1000
    X_train = np.random.randn(n_train, 34).astype(np.float64)

    model = IsolationForestModel(n_estimators=100, random_state=42)
    model.fit(X_train)

    # 1. Single-sample latency percentiles
    latencies: list[float] = []
    n_single = 200
    for _ in range(n_single):
        x_single = np.random.randn(1, 34).astype(np.float64)
        t0 = time.perf_counter()
        _ = model.score_samples(x_single)
        latencies.append((time.perf_counter() - t0) * 1000)  # ms

    p50 = float(np.percentile(latencies, 50))
    p90 = float(np.percentile(latencies, 90))
    p95 = float(np.percentile(latencies, 95))
    print(
        f"\n[BENCHMARK] Pure Model Scoring (N={n_single}): P50={p50:.3f}ms, P90={p90:.3f}ms, P95={p95:.3f}ms"
    )

    # 2. Batch throughput (10,000 transactions)
    n_batch = 10000
    X_batch = np.random.randn(n_batch, 34).astype(np.float64)
    t_start = time.perf_counter()
    _ = model.score_samples(X_batch)
    t_elapsed = time.perf_counter() - t_start
    throughput = n_batch / t_elapsed
    print(
        f"[BENCHMARK] Pure Batch Scoring (N={n_batch}): elapsed={t_elapsed * 1000:.2f}ms, throughput={throughput:.1f} tx/sec"
    )
    assert throughput > 1000  # Sanity bound


def test_benchmark_training_duration() -> None:
    """Benchmark IsolationForest training duration on 5,000 transactions."""
    n_samples = 5000
    X_train = np.random.randn(n_samples, 34).astype(np.float64)

    t0 = time.perf_counter()
    model = IsolationForestModel(n_estimators=100, random_state=42)
    model.fit(X_train)
    t_elapsed = time.perf_counter() - t0

    print(f"\n[BENCHMARK] Training Duration (5,000 tx, 100 trees): {t_elapsed:.3f}s")
    assert t_elapsed < 15.0  # Safe sanity bound


async def test_benchmark_end_to_end_inference_latency(
    async_session: AsyncSession,
    tmp_path: Any,
) -> None:
    """Benchmark end-to-end online scoring latency (feature extraction + DB read + model scoring)."""
    namespace = "BENCH_E2E_NS"
    cfg = GeneratorConfig(
        seed=42,
        source_namespace=namespace,
        account_count=5,
        merchant_count=5,
        device_count=5,
        location_count=5,
        transaction_count=100,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(async_session, ref_ds)
    await async_session.commit()

    ds_version = DatasetVersion(
        id=uuid.uuid4(),
        version="v1.0.0-bench",
        source_type="SYNTHETIC",
        seed=42,
        transaction_count=100,
    )
    async_session.add(ds_version)
    await async_session.commit()

    tx_ds = TransactionDatasetGenerator(cfg, ref_ds).generate()
    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_ds.transactions, out_buf)
    csv_bytes = out_buf.getvalue().encode("utf-8")

    import_svc = DatasetImportService()
    await import_svc.import_dataset(
        async_session,
        file_bytes=csv_bytes,
        filename="bench_tx.csv",
        source_namespace=namespace,
    )
    await async_session.commit()

    acc_stmt = select(Account).where(Account.source_namespace == namespace)
    accounts = (await async_session.execute(acc_stmt)).scalars().all()
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
    db_transactions = (await async_session.execute(tx_stmt)).scalars().all()
    gt_map = {str(gt.transaction_id): gt for gt in tx_ds.ground_truth}

    artifact_store = ModelArtifactStore(base_dir=tmp_path / "bench_artifacts")
    service = MLService(artifact_store=artifact_store)

    model_record = await service.train_and_register(
        session=async_session,
        dataset_version_id=ds_version.id,
        version="1.0.0",
        transactions=db_transactions,
        accounts_map=accounts_map,
        ground_truth_by_tx_id=gt_map,
        parameters={"n_estimators": 50},
    )
    await service.promote_to_active(async_session, model_record.id)
    await async_session.commit()

    # Warm up cache with 1 scoring call
    await service.score_transaction(async_session, db_transactions[0].id)

    # Measure single transaction online scoring latencies
    sample_txs = db_transactions[1:51]
    e2e_latencies: list[float] = []
    for tx in sample_txs:
        t0 = time.perf_counter()
        _ = await service.score_transaction(async_session, tx.id)
        e2e_latencies.append((time.perf_counter() - t0) * 1000)

    p50 = float(np.percentile(e2e_latencies, 50))
    p90 = float(np.percentile(e2e_latencies, 90))
    p95 = float(np.percentile(e2e_latencies, 95))
    print(
        f"\n[BENCHMARK] End-to-End Online Scoring (N={len(sample_txs)}): P50={p50:.2f}ms, P90={p90:.2f}ms, P95={p95:.2f}ms"
    )
    assert p50 < 100.0  # Sanity bound
