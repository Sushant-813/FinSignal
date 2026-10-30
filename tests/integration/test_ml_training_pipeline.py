"""End-to-end integration tests for ML training pipeline, artifact security, and inference."""

import io
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC
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
from finsignal.dataset.models import DatasetVersion
from finsignal.dataset.service import DatasetImportService
from finsignal.features.schemas import AccountProfileDTO
from finsignal.ml.constants import MODEL_FAMILY
from finsignal.ml.exceptions import (
    ModelIntegrityError,
    NoActiveModelError,
)
from finsignal.ml.service import MLService
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


@pytest.fixture
async def populated_dataset(
    async_session: AsyncSession,
) -> dict[str, Any]:
    """Generate and ingest a small realistic dataset (10 accounts, 300 transactions) with ground truth."""
    namespace = "ML_PIPELINE_TEST_NS"
    cfg = GeneratorConfig(
        seed=123,
        source_namespace=namespace,
        account_count=10,
        merchant_count=10,
        device_count=15,
        location_count=5,
        transaction_count=300,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(async_session, ref_ds)
    await async_session.commit()

    # Create a DatasetVersion record
    ds_version = DatasetVersion(
        id=uuid.uuid4(),
        version="v1.0.0-synthetic-test",
        source_type="SYNTHETIC",
        seed=123,
        transaction_count=300,
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
        filename="ml_test_transactions.csv",
        source_namespace=namespace,
    )
    await async_session.commit()

    # Fetch accounts map
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

    # Fetch ordered transactions
    tx_stmt = (
        select(Transaction)
        .where(Transaction.source_namespace == namespace)
        .order_by(Transaction.occurred_at.asc(), Transaction.id.asc())
    )
    db_transactions = (await async_session.execute(tx_stmt)).scalars().all()

    # Build ground truth mapping by transaction ID string
    gt_map = {gt.transaction_id: gt for gt in tx_ds.ground_truth}

    return {
        "dataset_version_id": ds_version.id,
        "accounts_map": accounts_map,
        "transactions": db_transactions,
        "ground_truth_map": gt_map,
    }


async def test_end_to_end_ml_pipeline_lifecycle(
    async_session: AsyncSession,
    populated_dataset: dict[str, Any],
    tmp_path: Any,
) -> None:
    """Full lifecycle: training -> threshold selection -> test eval -> activation -> online inference."""
    from finsignal.ml.registry import ModelArtifactStore

    artifact_store = ModelArtifactStore(base_dir=tmp_path / "artifacts")
    service = MLService(artifact_store=artifact_store)

    dataset_version_id = populated_dataset["dataset_version_id"]
    accounts_map = populated_dataset["accounts_map"]
    transactions = populated_dataset["transactions"]
    gt_map = populated_dataset["ground_truth_map"]

    # 1. Train and register candidate model
    model_record = await service.train_and_register(
        session=async_session,
        dataset_version_id=dataset_version_id,
        version="1.0.0",
        transactions=transactions,
        accounts_map=accounts_map,
        ground_truth_by_tx_id=gt_map,
        parameters={"n_estimators": 50, "random_state": 42},
        max_alert_rate=0.10,
    )
    await async_session.commit()

    # Verifications on candidate model
    assert model_record.id is not None
    assert model_record.name == MODEL_FAMILY
    assert model_record.version == "1.0.0"
    assert model_record.status == "VALIDATED"  # Must NOT be implicitly ACTIVE
    assert model_record.artifact_uri is not None
    assert model_record.artifact_hash is not None

    # Check metrics payload
    assert model_record.metrics is not None
    assert "threshold" in model_record.metrics
    assert "score_min" in model_record.metrics
    assert "score_max" in model_record.metrics
    assert isinstance(model_record.metrics["score_min"], float)
    assert isinstance(model_record.metrics["score_max"], float)
    assert model_record.metrics["score_min"] < model_record.metrics["score_max"]
    assert "validation" in model_record.metrics
    assert "test" in model_record.metrics
    assert "split" in model_record.metrics

    # 2. Verify inference fails prior to activation (no active model)
    eval_tx = transactions[0]
    with pytest.raises(NoActiveModelError, match="No active model found"):
        await service.score_transaction(async_session, eval_tx.id)

    # 3. Explicitly promote model to ACTIVE
    promoted = await service.promote_to_active(async_session, model_record.id)
    await async_session.commit()
    assert promoted.status == "ACTIVE"

    # 4. Online single-transaction inference
    pred = await service.score_transaction(async_session, eval_tx.id)
    assert pred.transaction_id == eval_tx.id
    assert pred.model_id == model_record.id
    assert pred.model_version == "1.0.0"
    assert 0.0 <= pred.anomaly_score <= 1.0
    assert pred.is_anomaly == (pred.anomaly_score >= pred.threshold)

    # 5. Batch transaction inference
    eval_batch = [tx.id for tx in transactions[:5]]
    batch_preds = await service.score_batch(async_session, eval_batch)
    assert len(batch_preds) == 5
    for bp in batch_preds:
        assert bp.model_id == model_record.id
        assert 0.0 <= bp.anomaly_score <= 1.0
        assert bp.is_anomaly == (bp.anomaly_score >= bp.threshold)


async def test_tampered_artifact_rejected(
    async_session: AsyncSession,
    populated_dataset: dict[str, Any],
    tmp_path: Any,
) -> None:
    """TG-02: Cryptographic SHA-256 verification rejects tampered artifacts prior to deserialization."""
    from finsignal.ml.registry import ModelArtifactStore

    artifact_dir = tmp_path / "artifacts_tamper"
    artifact_store = ModelArtifactStore(base_dir=artifact_dir)
    service = MLService(artifact_store=artifact_store)

    model_record = await service.train_and_register(
        session=async_session,
        dataset_version_id=populated_dataset["dataset_version_id"],
        version="1.0.0",
        transactions=populated_dataset["transactions"],
        accounts_map=populated_dataset["accounts_map"],
        ground_truth_by_tx_id=populated_dataset["ground_truth_map"],
        parameters={"n_estimators": 20},
    )
    await service.promote_to_active(async_session, model_record.id)
    await async_session.commit()

    # Clear memory cache to force disk load
    service._model_cache.clear()

    # Corrupt the artifact file on disk
    assert model_record.artifact_uri is not None
    artifact_file = artifact_dir / model_record.artifact_uri
    assert artifact_file.exists()

    with open(artifact_file, "r+b") as f:  # noqa: ASYNC230
        content = bytearray(f.read())
        content[0] = (content[0] + 1) % 256  # Flip a byte
        f.seek(0)
        f.write(content)

    # Scoring must abort with ModelIntegrityError
    eval_tx = populated_dataset["transactions"][0]
    with pytest.raises(ModelIntegrityError, match="integrity verification failed"):
        await service.score_transaction(async_session, eval_tx.id)
