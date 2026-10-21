"""Integration tests for TransactionIngestionEngine on disposable PostgreSQL (P4.4)."""

import csv
import io
from collections.abc import AsyncGenerator
from decimal import Decimal
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
from finsignal.dataset.ingestion import TransactionIngestionEngine
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
        # Clean up database tables for complete test isolation
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


@pytest.mark.asyncio
async def test_ingest_transactions_success(async_session: AsyncSession) -> None:
    """Verify clean transaction ingestion creates transactions and INSERTED provenance records."""
    namespace = "SYNTHETIC_INGEST_1"
    cfg = GeneratorConfig(
        seed=101,
        source_namespace=namespace,
        account_count=5,
        merchant_count=3,
        device_count=5,
        location_count=2,
        transaction_count=20,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    # 1. Persist reference entities first
    ref_service = ReferenceEntityPersistenceService()
    await ref_service.persist(async_session, ref_ds)
    await async_session.commit()

    # 2. Generate transactions
    tx_dataset = TransactionDatasetGenerator(cfg, ref_ds).generate()

    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_dataset.transactions, out_buf)
    csv_content = out_buf.getvalue()

    # 3. Create DatasetImport record
    ds_import = DatasetImport(
        source_namespace=namespace,
        source_type="SYNTHETIC",
        status="PENDING",
    )
    async_session.add(ds_import)
    await async_session.flush()

    # 4. Ingest transactions
    engine = TransactionIngestionEngine(batch_size=10)
    summary = await engine.ingest(async_session, ds_import, csv_content)
    await async_session.commit()

    assert summary.total_rows == 20
    assert summary.inserted_count == 20
    assert summary.valid_rows == 20
    assert summary.invalid_rows == 0
    assert summary.status == "COMPLETED"

    # Verify transactions in DB
    tx_count = (
        await async_session.execute(select(func.count(Transaction.id)))
    ).scalar()
    assert tx_count == 20

    # Verify provenance records
    rec_count = (
        await async_session.execute(select(func.count(TransactionImportRecord.id)))
    ).scalar()
    assert rec_count == 20

    outcomes = (
        (await async_session.execute(select(TransactionImportRecord.outcome)))
        .scalars()
        .all()
    )
    assert all(o == "INSERTED" for o in outcomes)


@pytest.mark.asyncio
async def test_ingest_matched_existing_and_quarantine(
    async_session: AsyncSession,
) -> None:
    """Verify duplicate row in second import receives MATCHED_EXISTING, while material conflict is QUARANTINED."""
    namespace = "SYNTHETIC_INGEST_2"
    cfg = GeneratorConfig(
        seed=202,
        source_namespace=namespace,
        account_count=5,
        merchant_count=2,
        device_count=5,
        location_count=2,
        transaction_count=5,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(async_session, ref_ds)
    await async_session.commit()

    tx_dataset = TransactionDatasetGenerator(cfg, ref_ds).generate()

    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_dataset.transactions, out_buf)
    csv_content = out_buf.getvalue()

    # First Import
    imp1 = DatasetImport(source_namespace=namespace, source_type="SYNTHETIC")
    async_session.add(imp1)
    await async_session.flush()

    engine = TransactionIngestionEngine()
    s1 = await engine.ingest(async_session, imp1, csv_content)
    await async_session.commit()
    assert s1.inserted_count == 5

    # Prepare second CSV with:
    # Row 1: identical -> MATCHED_EXISTING
    # Row 2: same canonical ID (TXN_00000002) but changed amount -> QUARANTINED
    # Row 3: non-existent account -> REJECTED
    reader = list(csv.DictReader(io.StringIO(csv_content)))
    headers = list(reader[0].keys())

    modified_rows = []
    # Row 1: identical
    modified_rows.append(reader[0])
    # Row 2: material conflict on amount
    conflicting_row = dict(reader[1])
    conflicting_row["amount"] = "99999.99"
    modified_rows.append(conflicting_row)
    # Row 3: non-existent account
    rejected_row = dict(reader[2])
    rejected_row["account_id"] = "ACC_999999"
    modified_rows.append(rejected_row)

    out_csv = io.StringIO()
    writer = csv.DictWriter(out_csv, fieldnames=headers)
    writer.writeheader()
    writer.writerows(modified_rows)

    # Second Import
    imp2 = DatasetImport(source_namespace=namespace, source_type="SYNTHETIC")
    async_session.add(imp2)
    await async_session.flush()

    s2 = await engine.ingest(async_session, imp2, out_csv.getvalue())
    await async_session.commit()

    assert s2.total_rows == 3
    assert s2.matched_existing_count == 1
    assert s2.quarantined_count == 1
    assert s2.rejected_count == 1

    # Verify canonical transaction 2 was NOT mutated
    tx2 = (
        await async_session.execute(
            select(Transaction).where(
                Transaction.external_transaction_id == reader[1]["transaction_id"]
            )
        )
    ).scalar_one()
    assert tx2.amount != Decimal("99999.99")
    assert tx2.amount == Decimal(reader[1]["amount"])

    # Verify error recorded in dataset_import_errors
    errors = (
        (
            await async_session.execute(
                select(DatasetImportError).where(
                    DatasetImportError.dataset_import_id == imp2.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(errors) == 2
    error_codes = {e.error_code for e in errors}
    assert "MATERIAL_CONFLICT" in error_codes
    assert "VALIDATION_ERROR" in error_codes
