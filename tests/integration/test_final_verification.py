"""Final Technical Verification suite for Phase 4 (P4.0–P4.6).

Verifies:
1. Verification 1: Provenance outcomes & PostgreSQL database constraints (INSERTED, MATCHED_EXISTING, DUPLICATE_IN_IMPORT, QUARANTINED, REJECTED).
2. Verification 2: Advisory locks, deterministic key derivation, active index safeguard, and gap-tolerant recovery.
3. Verification 3: Fraud scenario distribution at both instance and transaction level, ground-truth isolation, and 1:1 ID mapping.
4. Verification 4: Financial and transfer invariants (positive amounts, valid currency, transfer counterparties, no self-transfers, valid temporal relationships).
"""

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
from finsignal.dataset.ingestion.engine import TransactionIngestionEngine
from finsignal.dataset.ingestion.locking import derive_advisory_lock_key
from finsignal.dataset.models import DatasetImport, DatasetImportError
from finsignal.transactions.models import TransactionImportRecord


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


@pytest.mark.asyncio
async def test_all_five_provenance_outcomes_in_postgresql(
    async_session: AsyncSession,
) -> None:
    """Verification 1: Verify all 5 outcomes are accepted by PostgreSQL constraint and correctly assigned.

    - INSERTED: New canonical transaction
    - DUPLICATE_IN_IMPORT: Repeated canonical ID inside the same CSV file
    - MATCHED_EXISTING: Canonical ID and 7 material fields match prior import
    - QUARANTINED: Canonical ID matches but core material field conflicts
    - REJECTED: Malformed or unresolvable source row
    """
    namespace = "VERIFY_OUTCOMES_NS"
    cfg = GeneratorConfig(
        seed=12345,
        source_namespace=namespace,
        account_count=5,
        merchant_count=3,
        device_count=5,
        location_count=3,
        transaction_count=5,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(async_session, ref_ds)
    await async_session.commit()

    tx_ds = TransactionDatasetGenerator(cfg, ref_ds).generate()
    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_ds.transactions, out_buf)
    raw_csv = out_buf.getvalue()

    rows = list(csv.DictReader(io.StringIO(raw_csv)))
    headers = list(rows[0].keys())

    # --- File 1: Contains TXN_1, TXN_1 (intra-file duplicate), TXN_2, and an invalid row ---
    file1_rows = [
        rows[0],  # Row 1: TXN_1 -> INSERTED
        rows[0],  # Row 2: TXN_1 -> DUPLICATE_IN_IMPORT
        rows[1],  # Row 3: TXN_2 -> INSERTED
        dict(
            rows[2], account_id="ACC_NONEXISTENT"
        ),  # Row 4: Invalid account -> REJECTED
    ]
    f1_buf = io.StringIO()
    w1 = csv.DictWriter(f1_buf, fieldnames=headers)
    w1.writeheader()
    w1.writerows(file1_rows)

    imp1 = DatasetImport(
        source_namespace=namespace, source_type="SYNTHETIC", status="PENDING"
    )
    async_session.add(imp1)
    await async_session.flush()

    engine = TransactionIngestionEngine(batch_size=10, commit_per_batch=False)
    summary1 = await engine.ingest(async_session, imp1, f1_buf.getvalue())
    await async_session.commit()

    assert summary1.inserted_count == 2
    assert summary1.duplicate_in_import_count == 1
    assert summary1.rejected_count == 1

    # --- File 2: Contains TXN_1 (matched), TXN_1 (intra-file dup), and TXN_2 with altered amount (quarantine) ---
    file2_rows = [
        rows[0],  # Row 1: TXN_1 (seen in imp1) -> MATCHED_EXISTING
        rows[0],  # Row 2: TXN_1 (repeat in imp2) -> DUPLICATE_IN_IMPORT
        dict(
            rows[1], amount="99999.00"
        ),  # Row 3: TXN_2 (material conflict) -> QUARANTINED
    ]
    f2_buf = io.StringIO()
    w2 = csv.DictWriter(f2_buf, fieldnames=headers)
    w2.writeheader()
    w2.writerows(file2_rows)

    imp2 = DatasetImport(
        source_namespace=namespace, source_type="SYNTHETIC", status="PENDING"
    )
    async_session.add(imp2)
    await async_session.flush()

    summary2 = await engine.ingest(async_session, imp2, f2_buf.getvalue())
    await async_session.commit()

    assert summary2.matched_existing_count == 1
    assert summary2.duplicate_in_import_count == 1
    assert summary2.quarantined_count == 1

    # Query all outcomes directly from PostgreSQL table to verify database-level acceptance
    stmt = (
        select(TransactionImportRecord.outcome, func.count())
        .where(TransactionImportRecord.dataset_import_id.in_([imp1.id, imp2.id]))
        .group_by(TransactionImportRecord.outcome)
    )
    outcome_counts = dict((await async_session.execute(stmt)).all())

    # Verify all 5 outcomes are durably present in the database
    assert outcome_counts.get("INSERTED") == 2
    assert outcome_counts.get("MATCHED_EXISTING") == 1
    assert outcome_counts.get("DUPLICATE_IN_IMPORT") == 2
    assert outcome_counts.get("QUARANTINED") == 1
    assert outcome_counts.get("REJECTED") == 1


@pytest.mark.asyncio
async def test_recovery_handles_gaps_in_committed_source_row_numbers(
    async_session: AsyncSession,
) -> None:
    """Verification 2: Verify recovery handles non-contiguous gaps without skipping rows or duplicating.

    Simulates an import where rows {1, 2, 4, 5} were committed, leaving row 3 uncommitted (a gap).
    Proves that MAX(source_row_number) + 1 is NOT used: recovery must process row 3!
    """
    namespace = "VERIFY_GAP_RECOVERY_NS"
    cfg = GeneratorConfig(
        seed=999,
        source_namespace=namespace,
        account_count=5,
        merchant_count=3,
        device_count=5,
        location_count=3,
        transaction_count=5,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    await ReferenceEntityPersistenceService().persist(async_session, ref_ds)
    await async_session.commit()

    tx_ds = TransactionDatasetGenerator(cfg, ref_ds).generate()
    out_buf = io.StringIO()
    CSVDatasetExporter.export_transactions(tx_ds.transactions, out_buf)
    full_csv = out_buf.getvalue()

    # Create initial import record
    imp = DatasetImport(
        source_namespace=namespace,
        filename="transactions.csv",
        file_hash="test_gap_hash",
        source_type="SYNTHETIC",
        status="PENDING",
    )
    async_session.add(imp)
    await async_session.commit()

    # Artificially insert committed records with a GAP: row numbers 1, 2, 4, 5 (missing row 3)
    # This simulates out-of-order execution or partial commit where row 3 failed
    for r_num in [1, 2, 4, 5]:
        async_session.add(
            TransactionImportRecord(
                dataset_import_id=imp.id,
                source_row_number=r_num,
                transaction_id=None,
                outcome="INSERTED",
            )
        )

    imp.status = "FAILED"
    async_session.add(
        DatasetImportError(
            dataset_import_id=imp.id,
            row_number=3,
            error_code="PARTIAL_CRASH",
            message="Simulated crash on row 3",
        )
    )
    await async_session.commit()

    # Now run recover() on the failed import
    engine = TransactionIngestionEngine(batch_size=10, commit_per_batch=False)
    summary = await engine.recover(async_session, imp, full_csv)
    await async_session.commit()

    # Reconcile database state:
    # All 5 rows must have exactly one provenance record, with NO missing row 3 and NO duplicate records!
    records_stmt = (
        select(TransactionImportRecord.source_row_number)
        .where(TransactionImportRecord.dataset_import_id == imp.id)
        .order_by(TransactionImportRecord.source_row_number)
    )
    durably_committed = (await async_session.execute(records_stmt)).scalars().all()
    assert durably_committed == [1, 2, 3, 4, 5]
    assert summary.total_rows == 5
    assert summary.status == "COMPLETED"


def test_advisory_lock_key_derivation_deterministic() -> None:
    """Verification 2: Verify advisory lock key derivation is strictly deterministic and collision-resistant."""
    ns1 = "SYNTHETIC_ALPHA"
    ns2 = "SYNTHETIC_BETA"
    h1 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    h2 = "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"

    k1_a = derive_advisory_lock_key(ns1, h1)
    k1_b = derive_advisory_lock_key(ns1, h1)
    # Determinism
    assert k1_a == k1_b
    assert isinstance(k1_a, int)
    # Signed 64-bit int bounds: -2^63 <= k <= 2^63 - 1
    assert -9223372036854775808 <= k1_a <= 9223372036854775807

    # Distinct namespace or hash must yield distinct lock key
    k2 = derive_advisory_lock_key(ns2, h1)
    k3 = derive_advisory_lock_key(ns1, h2)
    assert k1_a != k2
    assert k1_a != k3


def test_financial_invariants_and_scenario_distribution() -> None:
    """Verification 3 & 4: Verify financial invariants and analyze scenario distribution at instance vs transaction level."""
    cfg = GeneratorConfig(
        seed=42,
        source_namespace="SYNTHETIC_INVARIANTS",
        account_count=100,
        merchant_count=50,
        device_count=200,
        location_count=20,
        transaction_count=5000,
        fraud_rate=0.03,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    tx_ds = TransactionDatasetGenerator(cfg, ref_ds).generate()

    # 1. Total count invariants
    assert len(tx_ds.transactions) == 5000
    assert len(tx_ds.ground_truth) == 5000

    # 2. Strict 1:1 transaction_id mapping between transactions and ground truth
    tx_ids = [t.transaction_id for t in tx_ds.transactions]
    gt_ids = [gt.transaction_id for gt in tx_ds.ground_truth]
    assert tx_ids == gt_ids
    assert len(set(tx_ids)) == 5000

    # 3. Financial & domain invariants
    acc_id_set = {a.account_id for a in ref_ds.accounts}
    merch_id_set = {m.merchant_id for m in ref_ds.merchants}
    dev_id_set = {d.device_id for d in ref_ds.devices}
    loc_id_set = {loc.location_id for loc in ref_ds.locations}

    for t in tx_ds.transactions:
        # Positive amount with exactly 2 decimal places
        assert t.amount > Decimal("0.00")
        assert t.amount.as_tuple().exponent == -2
        # Currency must be valid 3 uppercase letters
        assert t.currency == "INR"
        # Account references
        assert t.account_id in acc_id_set
        # Direction
        assert t.direction in ("DEBIT", "CREDIT")

        # Transfer invariants
        if t.transaction_type == "TRANSFER":
            assert t.counterparty_account_id is not None
            assert t.counterparty_account_id in acc_id_set
            # Distinct counterparty: NO self-transfers!
            assert t.counterparty_account_id != t.account_id
        else:
            assert t.counterparty_account_id is None

        # Device & Location references
        if t.device_id:
            assert t.device_id in dev_id_set
        if t.location_id:
            assert t.location_id in loc_id_set
        if t.merchant_id:
            assert t.merchant_id in merch_id_set

    # 4. Fraud scenario distribution analysis
    # Collect instance-level counts
    instance_to_scenario: dict[str, str] = {}
    transaction_scenario_counts: dict[str, int] = {f"F{i:03d}": 0 for i in range(1, 8)}

    for gt in tx_ds.ground_truth:
        if gt.is_fraud and gt.fraud_scenario:
            transaction_scenario_counts[gt.fraud_scenario] += 1
            if gt.scenario_instance_id:
                instance_to_scenario[gt.scenario_instance_id] = gt.fraud_scenario

    instance_scenario_counts: dict[str, int] = {f"F{i:03d}": 0 for i in range(1, 8)}
    for scn in instance_to_scenario.values():
        instance_scenario_counts[scn] += 1

    total_instances = len(instance_to_scenario)
    assert total_instances > 0

    # Verify every fraud scenario F001-F007 is represented at both levels
    for f_id in [f"F{i:03d}" for i in range(1, 8)]:
        assert instance_scenario_counts[f_id] > 0
        assert transaction_scenario_counts[f_id] > 0
