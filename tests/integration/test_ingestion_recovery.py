"""PostgreSQL integration tests for durable row-level recovery and import lifecycle (P4.6).

Verifies:
1. Legal status transitions (PENDING -> PROCESSING -> COMPLETED, FAILED -> PROCESSING).
2. Rejection of illegal status transitions (e.g. COMPLETED -> PROCESSING).
3. Partial batch commit followed by simulated failure.
4. Durable row-level recovery reconciling actual committed source ordinals without skipping or duplicating rows.
5. Ingestion engine accurately reconciles final counts and provenance after recovery.
"""

import io
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.dataset.generator import (
    CSVDatasetExporter,
    GeneratorConfig,
    ReferenceEntityGenerator,
    ReferenceEntityPersistenceService,
    TransactionDatasetGenerator,
)
from finsignal.dataset.ingestion.engine import (
    TransactionIngestionEngine,
    validate_status_transition,
)
from finsignal.dataset.models import DatasetImport, DatasetImportError
from finsignal.transactions.models import Transaction, TransactionImportRecord


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
                    "TRUNCATE TABLE transaction_import_records, dataset_import_errors, dataset_imports, "
                    "transactions, account_devices, accounts, merchants, devices, locations CASCADE;"
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


def _generate_csv_text(namespace: str, count: int = 60) -> tuple[str, GeneratorConfig]:
    cfg = GeneratorConfig(
        seed=777,
        source_namespace=namespace,
        account_count=5,
        merchant_count=3,
        device_count=5,
        location_count=3,
        transaction_count=count,
    )
    ref_gen = ReferenceEntityGenerator(cfg)
    refs = ref_gen.generate()
    tx_gen = TransactionDatasetGenerator(cfg, refs)
    dataset = tx_gen.generate()

    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(dataset.transactions, out_buf)
    return out_buf.getvalue(), cfg


def test_status_transitions() -> None:
    """Verify legal status transitions and illegal transition rejections."""
    # Legal transitions
    validate_status_transition("PENDING", "PROCESSING")
    validate_status_transition("PENDING", "FAILED")
    validate_status_transition("PROCESSING", "COMPLETED")
    validate_status_transition("PROCESSING", "FAILED")
    validate_status_transition("FAILED", "PROCESSING")

    # Illegal transitions
    with pytest.raises(ValueError, match="Illegal import status transition"):
        validate_status_transition("COMPLETED", "PROCESSING")

    with pytest.raises(ValueError, match="Illegal import status transition"):
        validate_status_transition("COMPLETED", "FAILED")

    with pytest.raises(ValueError, match="Illegal import status transition"):
        validate_status_transition("PENDING", "COMPLETED")


@pytest.mark.asyncio
async def test_durable_batch_failure_and_recovery(
    disposable_db: dict[str, Any],
    async_session: AsyncSession,
) -> None:
    """Verify failure after partial batch commit can be recovered idempotently without duplicates."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)

    namespace = "RECOVERY_TEST_NS"
    csv_text, cfg = _generate_csv_text(namespace, count=50)

    # Persist reference entities
    ref_gen = ReferenceEntityGenerator(cfg)
    refs = ref_gen.generate()
    persist_svc = ReferenceEntityPersistenceService()
    await persist_svc.persist(async_session, refs)
    await async_session.commit()

    import_id = None
    import_hash = "fakehash1234567890fakehash1234567890fakehash1234567890fakehash12"

    # Step 1: Ingest with small batch size (batch_size=15), but simulate an interruption after batch 1 commits
    async with session_maker() as s1:
        imp = DatasetImport(
            source_namespace=namespace,
            filename="tx.csv",
            file_hash=import_hash,
            source_type="SYNTHETIC",
            status="PENDING",
        )
        s1.add(imp)
        await s1.commit()
        import_id = imp.id

        # Use an engine that commits per batch
        test_engine = TransactionIngestionEngine(batch_size=15, commit_per_batch=True)

        # Ingest only the first 25 lines of the CSV (header + 25 rows)
        lines = csv_text.strip().split("\n")
        partial_csv = "\n".join(lines[:26])  # header + 25 rows

        # Process the partial CSV
        await test_engine.ingest(s1, imp, io.StringIO(partial_csv))
        await s1.commit()

        # Simulate that the import failed midway (e.g. timeout / network interruption on full file)
        imp.status = "FAILED"
        s1.add(
            DatasetImportError(
                dataset_import_id=import_id,
                row_number=None,
                error_code="PROCESSING_FAILED",
                message="Simulated interruption after partial ingestion",
            )
        )
        await s1.commit()

    # Verify state after partial failure
    async with session_maker() as s2:
        stmt = (
            select(TransactionImportRecord.source_row_number)
            .where(TransactionImportRecord.dataset_import_id == import_id)
            .order_by(TransactionImportRecord.source_row_number)
        )
        committed_rows = (await s2.execute(stmt)).scalars().all()
        assert len(committed_rows) == 25
        assert set(committed_rows) == set(range(1, 26))

        # Check import record is FAILED
        imp_check = await s2.get(DatasetImport, import_id)
        assert imp_check is not None
        assert imp_check.status == "FAILED"

    # Step 2: Recover using the complete CSV (50 rows)
    async with session_maker() as s3:
        imp_to_recover = await s3.get(DatasetImport, import_id)
        assert imp_to_recover is not None

        recovery_engine = TransactionIngestionEngine(
            batch_size=15, commit_per_batch=True
        )
        summary = await recovery_engine.recover(
            session=s3,
            dataset_import=imp_to_recover,
            csv_source=io.StringIO(csv_text),
        )
        await s3.commit()

        # Step 3: Verify the recovered state
        assert summary.status == "COMPLETED"
        assert summary.total_rows == 50
        assert summary.inserted_count == 50
        assert summary.quarantined_count == 0
        assert summary.rejected_count == 0

        # Verify durable database provenance records
        stmt = (
            select(TransactionImportRecord.source_row_number)
            .where(TransactionImportRecord.dataset_import_id == import_id)
            .order_by(TransactionImportRecord.source_row_number)
        )
        all_committed_rows = (await s3.execute(stmt)).scalars().all()
        assert len(all_committed_rows) == 50
        # Exactly row numbers 1 through 50 with no gaps or duplicates
        assert all_committed_rows == list(range(1, 51))

        # Verify exactly 50 canonical transactions created
        tx_count_stmt = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.source_namespace == namespace)
        )
        tx_count = (await s3.execute(tx_count_stmt)).scalar_one()
        assert tx_count == 50

    await engine.dispose()
