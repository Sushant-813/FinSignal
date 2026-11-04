"""Transaction ingestion engine and canonical provenance ledger (P4.4).

Resolves CSV rows against operational PostgreSQL schema, enforces canonical
transaction uniqueness, verifies the seven core material fields, records
row-level provenance, and isolates material conflicts into quarantine.
"""

import csv
import io
import logging
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.accounts.models import Account
from finsignal.dataset.ingestion.schemas import IngestionSummary
from finsignal.dataset.models import DatasetImport, DatasetImportError
from finsignal.devices.models import Device
from finsignal.merchants.models import Merchant
from finsignal.transactions.hashing import compute_canonical_row_hash
from finsignal.transactions.models import Transaction, TransactionImportRecord
from finsignal.transactions.validation import validate_transaction_account_namespace

logger = logging.getLogger("finsignal.dataset.ingestion.engine")

_REQUIRED_HEADERS = {
    "transaction_id",
    "source_namespace",
    "account_id",
    "occurred_at",
    "amount",
    "currency",
    "transaction_type",
    "direction",
}

_LEGAL_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"PROCESSING", "FAILED"},
    "PROCESSING": {"COMPLETED", "FAILED"},
    "FAILED": {"PROCESSING"},
    "COMPLETED": set(),
}


def validate_status_transition(current: str, target: str) -> None:
    """Validate whether an import status transition is permitted."""
    allowed = _LEGAL_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"Illegal import status transition from '{current}' to '{target}'."
        )


class TransactionIngestionEngine:
    """Ingests transaction CSV records and records complete row-level provenance."""

    def __init__(self, batch_size: int = 500, commit_per_batch: bool = True) -> None:
        self.batch_size = max(50, min(batch_size, 5000))
        self.commit_per_batch = commit_per_batch

    async def ingest(
        self,
        session: AsyncSession,
        dataset_import: DatasetImport,
        csv_source: str | io.StringIO | io.TextIOBase,
        *,
        skip_header: bool = True,
        resume_row_ordinals: set[int] | None = None,
    ) -> IngestionSummary:
        """Execute CSV ingestion with canonical identity matching and provenance tracking."""
        namespace = dataset_import.source_namespace
        import_id = dataset_import.id

        # Validate and transition status to PROCESSING
        validate_status_transition(dataset_import.status, "PROCESSING")
        dataset_import.status = "PROCESSING"
        if self.commit_per_batch:
            await session.commit()
        else:
            await session.flush()

        # 1. Bounded on-demand reference entity caches (PERF-02)
        account_map: dict[str, Account] = {}
        merchant_map: dict[str, Merchant] = {}
        device_map: dict[str, Device] = {}
        missing_account_ids: set[str] = set()
        missing_merchant_ids: set[str] = set()
        missing_device_ids: set[str] = set()

        # Counters
        total_rows = 0
        valid_rows = 0
        invalid_rows = 0
        inserted_count = 0
        matched_existing_count = 0
        duplicate_in_import_count = 0
        quarantined_count = 0
        rejected_count = 0
        error_count = 0

        # In-import deduplication tracker: (source_namespace, account_id, external_transaction_id) -> transaction UUID
        import_seen_canonical: dict[tuple[str, uuid.UUID, str], uuid.UUID | None] = {}
        if resume_row_ordinals:
            prior_tx_stmt = (
                select(
                    Transaction.source_namespace,
                    Transaction.account_id,
                    Transaction.external_transaction_id,
                    Transaction.id,
                )
                .join(
                    TransactionImportRecord,
                    TransactionImportRecord.transaction_id == Transaction.id,
                )
                .where(TransactionImportRecord.dataset_import_id == import_id)
            )
            for ns_val, acc_uuid, ext_id, tx_uuid in (
                await session.execute(prior_tx_stmt)
            ).all():
                import_seen_canonical[(ns_val, acc_uuid, ext_id)] = tx_uuid

        if isinstance(csv_source, str):
            if csv_source.startswith("\ufeff"):
                csv_source = csv_source[1:]
            reader = csv.DictReader(io.StringIO(csv_source))
        else:
            reader = csv.DictReader(csv_source)

        if reader.fieldnames is None:
            validate_status_transition(dataset_import.status, "FAILED")
            dataset_import.status = "FAILED"
            dataset_import.completed_at = datetime.now(UTC)
            session.add(
                DatasetImportError(
                    dataset_import_id=import_id,
                    row_number=None,
                    field_name=None,
                    error_code="HEADER_ERROR",
                    message="CSV source is empty or missing headers.",
                )
            )
            if self.commit_per_batch:
                await session.commit()
            else:
                await session.flush()
            raise ValueError("CSV source is empty or missing headers.")

        missing_headers = _REQUIRED_HEADERS - set(reader.fieldnames)
        if missing_headers:
            validate_status_transition(dataset_import.status, "FAILED")
            dataset_import.status = "FAILED"
            dataset_import.completed_at = datetime.now(UTC)
            session.add(
                DatasetImportError(
                    dataset_import_id=import_id,
                    row_number=None,
                    field_name=None,
                    error_code="HEADER_ERROR",
                    message=f"CSV missing required headers: {sorted(missing_headers)}",
                )
            )
            if self.commit_per_batch:
                await session.commit()
            else:
                await session.flush()
            raise ValueError(f"CSV missing required headers: {sorted(missing_headers)}")

        row_number = 0
        batch_records: list[TransactionImportRecord] = []
        batch_errors: list[DatasetImportError] = []
        new_transactions: list[Transaction] = []

        def _chunked_reader(
            r: csv.DictReader[str], size: int
        ) -> Iterator[list[dict[str, str]]]:
            chunk: list[dict[str, str]] = []
            for row in r:
                chunk.append(row)
                if len(chunk) >= size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk

        for raw_batch in _chunked_reader(reader, self.batch_size):
            # A. Bulk resolve missing reference entities for this batch (PERF-02)
            needed_acc_ids: set[str] = set()
            needed_merch_ids: set[str] = set()
            needed_dev_ids: set[str] = set()
            for raw_row in raw_batch:
                aid = (raw_row.get("account_id") or "").strip()
                if aid:
                    needed_acc_ids.add(aid)
                cpid = (raw_row.get("counterparty_account_id") or "").strip()
                if cpid:
                    needed_acc_ids.add(cpid)
                mid = (raw_row.get("merchant_id") or "").strip()
                if mid:
                    needed_merch_ids.add(mid)
                did = (raw_row.get("device_id") or "").strip()
                if did:
                    needed_dev_ids.add(did)

            fetch_acc = (needed_acc_ids - set(account_map.keys())) - missing_account_ids
            if fetch_acc:
                acc_stmt = select(Account).where(
                    Account.source_namespace == namespace,
                    Account.external_account_id.in_(fetch_acc),
                )
                for a in (await session.execute(acc_stmt)).scalars():
                    if a.external_account_id:
                        account_map[a.external_account_id] = a
                for aid in fetch_acc:
                    if aid not in account_map:
                        missing_account_ids.add(aid)

            fetch_merch = (
                needed_merch_ids - set(merchant_map.keys())
            ) - missing_merchant_ids
            if fetch_merch:
                merch_stmt = select(Merchant).where(
                    Merchant.external_merchant_id.in_(fetch_merch)
                )
                for m in (await session.execute(merch_stmt)).scalars():
                    if m.external_merchant_id:
                        merchant_map[m.external_merchant_id] = m
                for mid in fetch_merch:
                    if mid not in merchant_map:
                        missing_merchant_ids.add(mid)

            fetch_dev = (needed_dev_ids - set(device_map.keys())) - missing_device_ids
            if fetch_dev:
                dev_stmt = select(Device).where(
                    Device.external_device_id.in_(fetch_dev)
                )
                for d in (await session.execute(dev_stmt)).scalars():
                    if d.external_device_id:
                        device_map[d.external_device_id] = d
                for did in fetch_dev:
                    if did not in device_map:
                        missing_device_ids.add(did)

            # Evict oldest keys if cache grows excessively
            if len(account_map) > 20000:
                for k in list(account_map.keys())[:10000]:
                    del account_map[k]

            # B. Parse and validate rows in this batch
            valid_candidates: list[
                tuple[
                    int,
                    dict[str, Any],
                    dict[str, Any],
                    tuple[str, uuid.UUID, str],
                    tuple[uuid.UUID, str],
                ]
            ] = []
            intra_batch_duplicates: list[
                tuple[int, str, tuple[str, uuid.UUID, str]]
            ] = []
            batch_first_seen: set[tuple[str, uuid.UUID, str]] = set()

            for raw_row in raw_batch:
                row_number += 1
                total_rows += 1

                # Skip rows already processed in a prior partial run if resuming
                if (
                    resume_row_ordinals is not None
                    and row_number in resume_row_ordinals
                ):
                    continue

                try:
                    ext_tx_id = (raw_row.get("transaction_id") or "").strip()
                    row_ns = (raw_row.get("source_namespace") or "").strip()
                    ext_acc_id = (raw_row.get("account_id") or "").strip()
                    ext_cp_id = (
                        raw_row.get("counterparty_account_id") or ""
                    ).strip() or None
                    ext_merch_id = (raw_row.get("merchant_id") or "").strip() or None
                    ext_dev_id = (raw_row.get("device_id") or "").strip() or None

                    amount_str = (raw_row.get("amount") or "").strip()
                    currency = (raw_row.get("currency") or "").strip()
                    tx_type = (raw_row.get("transaction_type") or "").strip()
                    direction = (raw_row.get("direction") or "").strip()
                    category = (raw_row.get("category") or "").strip() or None
                    payment_method = (
                        raw_row.get("payment_method") or ""
                    ).strip() or None
                    channel = (raw_row.get("channel") or "").strip() or None
                    occurred_str = (raw_row.get("occurred_at") or "").strip()

                    if not ext_tx_id or not row_ns or not ext_acc_id:
                        raise ValueError(
                            "Missing essential identifier (transaction_id, source_namespace, or account_id)."
                        )

                    if row_ns != namespace:
                        raise ValueError(
                            f"Row namespace '{row_ns}' does not match import namespace '{namespace}'."
                        )

                    account = account_map.get(ext_acc_id)
                    if account is None:
                        raise ValueError(
                            f"Referenced account '{ext_acc_id}' not found in namespace '{namespace}'."
                        )

                    validate_transaction_account_namespace(
                        account.source_namespace, row_ns
                    )

                    cp_account_id: uuid.UUID | None = None
                    if ext_cp_id:
                        cp_account = account_map.get(ext_cp_id)
                        if cp_account is None:
                            raise ValueError(
                                f"Counterparty account '{ext_cp_id}' not found in namespace '{namespace}'."
                            )
                        if cp_account.id == account.id:
                            raise ValueError(
                                f"Self-transfer forbidden: account matches counterparty '{ext_cp_id}'."
                            )
                        cp_account_id = cp_account.id
                    elif tx_type == "TRANSFER":
                        raise ValueError(
                            "Transfer transaction requires a valid counterparty_account_id."
                        )

                    merchant_uuid: uuid.UUID | None = None
                    if ext_merch_id and ext_merch_id in merchant_map:
                        merchant_uuid = merchant_map[ext_merch_id].id

                    device_uuid: uuid.UUID | None = None
                    if ext_dev_id and ext_dev_id in device_map:
                        device_uuid = device_map[ext_dev_id].id

                    location_uuid: uuid.UUID | None = None
                    if ext_merch_id and ext_merch_id in merchant_map:
                        location_uuid = merchant_map[ext_merch_id].location_id
                    if location_uuid is None:
                        location_uuid = account.home_location_id

                    try:
                        amount = Decimal(amount_str).quantize(Decimal("0.01"))
                        if amount <= Decimal("0.00"):
                            raise ValueError("Amount must be positive.")
                    except Exception as err:
                        raise ValueError(
                            f"Invalid monetary amount '{amount_str}': {err}"
                        ) from err

                    try:
                        occurred_at = datetime.fromisoformat(occurred_str)
                        if occurred_at.tzinfo is None:
                            occurred_at = occurred_at.replace(tzinfo=UTC)
                    except Exception as err:
                        raise ValueError(
                            f"Invalid ISO 8601 occurred_at '{occurred_str}': {err}"
                        ) from err

                    canonical_dict = {
                        "source_namespace": namespace,
                        "external_transaction_id": ext_tx_id,
                        "account_id": account.id,
                        "counterparty_account_id": cp_account_id,
                        "merchant_id": merchant_uuid,
                        "device_id": device_uuid,
                        "location_id": location_uuid,
                        "occurred_at": occurred_at,
                        "amount": amount,
                        "currency": currency,
                        "transaction_type": tx_type,
                        "direction": direction,
                        "category": category,
                        "payment_method": payment_method,
                        "channel": channel,
                    }
                    row_hash = compute_canonical_row_hash(canonical_dict)
                    canonical_key = (namespace, account.id, ext_tx_id)

                    if canonical_key in import_seen_canonical:
                        duplicate_in_import_count += 1
                        valid_rows += 1
                        batch_records.append(
                            TransactionImportRecord(
                                dataset_import_id=import_id,
                                source_row_number=row_number,
                                transaction_id=import_seen_canonical[canonical_key],
                                row_hash=row_hash,
                                outcome="DUPLICATE_IN_IMPORT",
                            )
                        )
                        continue

                    if canonical_key in batch_first_seen:
                        intra_batch_duplicates.append(
                            (row_number, row_hash, canonical_key)
                        )
                        continue

                    batch_first_seen.add(canonical_key)

                    parsed_dict = {
                        "ext_tx_id": ext_tx_id,
                        "account_id": account.id,
                        "cp_account_id": cp_account_id,
                        "merchant_uuid": merchant_uuid,
                        "device_uuid": device_uuid,
                        "location_uuid": location_uuid,
                        "occurred_at": occurred_at,
                        "amount": amount,
                        "currency": currency,
                        "tx_type": tx_type,
                        "direction": direction,
                        "category": category,
                        "payment_method": payment_method,
                        "channel": channel,
                        "row_hash": row_hash,
                    }
                    valid_candidates.append(
                        (
                            row_number,
                            parsed_dict,
                            canonical_dict,
                            canonical_key,
                            (account.id, ext_tx_id),
                        )
                    )

                except Exception as row_err:
                    rejected_count += 1
                    invalid_rows += 1
                    error_count += 1
                    batch_records.append(
                        TransactionImportRecord(
                            dataset_import_id=import_id,
                            source_row_number=row_number,
                            transaction_id=None,
                            row_hash=None,
                            outcome="REJECTED",
                        )
                    )
                    batch_errors.append(
                        DatasetImportError(
                            dataset_import_id=import_id,
                            row_number=row_number,
                            field_name=None,
                            error_code="VALIDATION_ERROR",
                            message=str(row_err)[:250],
                        )
                    )

            # C. Batch query existing transactions for all valid candidates (PERF-01)
            if valid_candidates:
                needed_pairs = list({c[4] for c in valid_candidates})
                existing_tx_map: dict[tuple[uuid.UUID, str], Transaction] = {}
                for chunk_start in range(0, len(needed_pairs), 2000):
                    chunk_keys = needed_pairs[chunk_start : chunk_start + 2000]
                    tx_stmt = select(Transaction).where(
                        Transaction.source_namespace == namespace,
                        tuple_(
                            Transaction.account_id, Transaction.external_transaction_id
                        ).in_(chunk_keys),
                    )
                    for tx in (await session.execute(tx_stmt)).scalars():
                        existing_tx_map[(tx.account_id, tx.external_transaction_id)] = (
                            tx
                        )

                for row_num, p, _c_dict, c_key, pair in valid_candidates:
                    existing_tx = existing_tx_map.get(pair)
                    if existing_tx is not None:
                        material_match = (
                            existing_tx.account_id == p["account_id"]
                            and existing_tx.amount == p["amount"]
                            and existing_tx.currency == p["currency"]
                            and existing_tx.occurred_at == p["occurred_at"]
                            and existing_tx.transaction_type == p["tx_type"]
                            and existing_tx.direction == p["direction"]
                            and existing_tx.counterparty_account_id
                            == p["cp_account_id"]
                        )
                        if material_match:
                            matched_existing_count += 1
                            valid_rows += 1
                            import_seen_canonical[c_key] = existing_tx.id
                            batch_records.append(
                                TransactionImportRecord(
                                    dataset_import_id=import_id,
                                    source_row_number=row_num,
                                    transaction_id=existing_tx.id,
                                    row_hash=p["row_hash"],
                                    outcome="MATCHED_EXISTING",
                                )
                            )
                        else:
                            quarantined_count += 1
                            invalid_rows += 1
                            error_count += 1
                            import_seen_canonical[c_key] = None
                            batch_records.append(
                                TransactionImportRecord(
                                    dataset_import_id=import_id,
                                    source_row_number=row_num,
                                    transaction_id=None,
                                    row_hash=p["row_hash"],
                                    outcome="QUARANTINED",
                                )
                            )
                            batch_errors.append(
                                DatasetImportError(
                                    dataset_import_id=import_id,
                                    row_number=row_num,
                                    field_name="amount",
                                    error_code="MATERIAL_CONFLICT",
                                    message=(
                                        f"Row collides with existing canonical transaction '{p['ext_tx_id']}' "
                                        "but core material fields differ. Quarantined."
                                    ),
                                )
                            )
                    else:
                        new_txn = Transaction(
                            id=uuid.uuid4(),
                            source_namespace=namespace,
                            external_transaction_id=p["ext_tx_id"],
                            first_seen_import_id=import_id,
                            account_id=p["account_id"],
                            counterparty_account_id=p["cp_account_id"],
                            merchant_id=p["merchant_uuid"],
                            device_id=p["device_uuid"],
                            location_id=p["location_uuid"],
                            occurred_at=p["occurred_at"],
                            amount=p["amount"],
                            currency=p["currency"],
                            transaction_type=p["tx_type"],
                            direction=p["direction"],
                            category=p["category"],
                            payment_method=p["payment_method"],
                            channel=p["channel"],
                        )
                        new_transactions.append(new_txn)
                        inserted_count += 1
                        valid_rows += 1
                        import_seen_canonical[c_key] = new_txn.id
                        batch_records.append(
                            TransactionImportRecord(
                                dataset_import_id=import_id,
                                source_row_number=row_num,
                                transaction_id=new_txn.id,
                                row_hash=p["row_hash"],
                                outcome="INSERTED",
                            )
                        )

            for dup_row_num, dup_row_hash, dup_c_key in intra_batch_duplicates:
                duplicate_in_import_count += 1
                valid_rows += 1
                batch_records.append(
                    TransactionImportRecord(
                        dataset_import_id=import_id,
                        source_row_number=dup_row_num,
                        transaction_id=import_seen_canonical.get(dup_c_key),
                        row_hash=dup_row_hash,
                        outcome="DUPLICATE_IN_IMPORT",
                    )
                )

            # Flush batch to database
            if new_transactions:
                session.add_all(new_transactions)
            if batch_records:
                session.add_all(batch_records)
            if batch_errors:
                session.add_all(batch_errors)
            if self.commit_per_batch:
                await session.commit()
            else:
                await session.flush()
            new_transactions.clear()
            batch_records.clear()
            batch_errors.clear()

        # Update DatasetImport summary counters directly from durable provenance records
        outcome_stmt = (
            select(TransactionImportRecord.outcome, func.count())
            .where(TransactionImportRecord.dataset_import_id == import_id)
            .group_by(TransactionImportRecord.outcome)
        )
        counts_res = await session.execute(outcome_stmt)
        counts_map = dict(counts_res.all())

        inserted_count = counts_map.get("INSERTED", 0)
        matched_existing_count = counts_map.get("MATCHED_EXISTING", 0)
        duplicate_in_import_count = counts_map.get("DUPLICATE_IN_IMPORT", 0)
        quarantined_count = counts_map.get("QUARANTINED", 0)
        rejected_count = counts_map.get("REJECTED", 0)

        valid_rows = inserted_count + matched_existing_count + duplicate_in_import_count
        invalid_rows = quarantined_count + rejected_count
        total_rows = valid_rows + invalid_rows

        validate_status_transition(dataset_import.status, "COMPLETED")
        dataset_import.total_rows = total_rows
        dataset_import.valid_rows = valid_rows
        dataset_import.invalid_rows = invalid_rows
        dataset_import.status = "COMPLETED"
        dataset_import.completed_at = datetime.now(UTC)
        if self.commit_per_batch:
            await session.commit()
        else:
            await session.flush()

        err_stmt = (
            select(func.count())
            .select_from(DatasetImportError)
            .where(DatasetImportError.dataset_import_id == import_id)
        )
        err_res = await session.execute(err_stmt)
        error_count = err_res.scalar_one()

        logger.info(
            "Ingestion completed: import_id=%s total=%d inserted=%d matched=%d duplicate=%d quarantined=%d rejected=%d",
            import_id,
            total_rows,
            inserted_count,
            matched_existing_count,
            duplicate_in_import_count,
            quarantined_count,
            rejected_count,
        )

        return IngestionSummary(
            import_id=import_id,
            source_namespace=namespace,
            status=dataset_import.status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            inserted_count=inserted_count,
            matched_existing_count=matched_existing_count,
            duplicate_in_import_count=duplicate_in_import_count,
            quarantined_count=quarantined_count,
            rejected_count=rejected_count,
            error_count=error_count,
        )

    async def recover(
        self,
        session: AsyncSession,
        dataset_import: DatasetImport,
        csv_source: str | io.StringIO | io.TextIOBase,
    ) -> IngestionSummary:
        """Durable row-level recovery for interrupted or failed imports."""
        if dataset_import.status == "COMPLETED":
            logger.info(
                "Import %s already COMPLETED, returning existing summary",
                dataset_import.id,
            )
            return await self.get_summary(session, dataset_import)

        # Reconcile actual committed source row ordinals for this import ID
        stmt = select(TransactionImportRecord.source_row_number).where(
            TransactionImportRecord.dataset_import_id == dataset_import.id
        )
        committed_rows = set((await session.execute(stmt)).scalars().all())

        logger.info(
            "Recovering import %s: found %d already committed rows",
            dataset_import.id,
            len(committed_rows),
        )

        return await self.ingest(
            session=session,
            dataset_import=dataset_import,
            csv_source=csv_source,
            resume_row_ordinals=committed_rows,
        )

    async def get_summary(
        self,
        session: AsyncSession,
        dataset_import: DatasetImport,
    ) -> IngestionSummary:
        """Derive authoritative summary from transaction_import_records."""
        outcome_stmt = (
            select(TransactionImportRecord.outcome, func.count())
            .where(TransactionImportRecord.dataset_import_id == dataset_import.id)
            .group_by(TransactionImportRecord.outcome)
        )
        counts_res = await session.execute(outcome_stmt)
        counts_map = dict(counts_res.all())

        inserted_count = counts_map.get("INSERTED", 0)
        matched_existing_count = counts_map.get("MATCHED_EXISTING", 0)
        duplicate_in_import_count = counts_map.get("DUPLICATE_IN_IMPORT", 0)
        quarantined_count = counts_map.get("QUARANTINED", 0)
        rejected_count = counts_map.get("REJECTED", 0)

        valid_rows = inserted_count + matched_existing_count + duplicate_in_import_count
        invalid_rows = quarantined_count + rejected_count
        total_rows = valid_rows + invalid_rows

        err_stmt = (
            select(func.count())
            .select_from(DatasetImportError)
            .where(DatasetImportError.dataset_import_id == dataset_import.id)
        )
        err_res = await session.execute(err_stmt)
        error_count = err_res.scalar_one()

        return IngestionSummary(
            import_id=dataset_import.id,
            source_namespace=dataset_import.source_namespace,
            status=dataset_import.status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            inserted_count=inserted_count,
            matched_existing_count=matched_existing_count,
            duplicate_in_import_count=duplicate_in_import_count,
            quarantined_count=quarantined_count,
            rejected_count=rejected_count,
            error_count=error_count,
        )
