"""Transaction ingestion engine and canonical provenance ledger (P4.4).

Resolves CSV rows against operational PostgreSQL schema, enforces canonical
transaction uniqueness, verifies the seven core material fields, records
row-level provenance, and isolates material conflicts into quarantine.
"""

import csv
import io
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
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
        csv_source: str | io.StringIO,
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

        # 1. Preload reference entity lookup maps for this namespace
        acc_stmt = select(Account).where(Account.source_namespace == namespace)
        accounts_list = (await session.execute(acc_stmt)).scalars().all()
        account_map: dict[str, Account] = {
            acc.external_account_id: acc
            for acc in accounts_list
            if acc.external_account_id is not None
        }

        merch_stmt = select(Merchant)
        merchants_list = (await session.execute(merch_stmt)).scalars().all()
        merchant_map: dict[str, Merchant] = {
            m.external_merchant_id: m
            for m in merchants_list
            if m.external_merchant_id is not None
        }

        dev_stmt = select(Device)
        devices_list = (await session.execute(dev_stmt)).scalars().all()
        device_map: dict[str, Device] = {
            d.external_device_id: d
            for d in devices_list
            if d.external_device_id is not None
        }

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

        for raw_row in reader:
            row_number += 1
            total_rows += 1

            # Skip rows already processed in a prior partial run if resuming
            if resume_row_ordinals is not None and row_number in resume_row_ordinals:
                continue

            try:
                # 2. Parse & Validate Row
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
                payment_method = (raw_row.get("payment_method") or "").strip() or None
                channel = (raw_row.get("channel") or "").strip() or None
                occurred_str = (raw_row.get("occurred_at") or "").strip()

                if not ext_tx_id or not row_ns or not ext_acc_id:
                    raise ValueError(
                        "Missing essential identifier (transaction_id, source_namespace, or account_id)."
                    )

                # Validate namespace consistency between row and import
                if row_ns != namespace:
                    raise ValueError(
                        f"Row namespace '{row_ns}' does not match import namespace '{namespace}'."
                    )

                # Resolve Account
                account = account_map.get(ext_acc_id)
                if account is None:
                    raise ValueError(
                        f"Referenced account '{ext_acc_id}' not found in namespace '{namespace}'."
                    )

                # Enforce layered namespace validation
                validate_transaction_account_namespace(account.source_namespace, row_ns)

                # Resolve Counterparty Account if transfer
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

                # Resolve Merchant
                merchant_uuid: uuid.UUID | None = None
                if ext_merch_id and ext_merch_id in merchant_map:
                    merchant_uuid = merchant_map[ext_merch_id].id

                # Resolve Device
                device_uuid: uuid.UUID | None = None
                if ext_dev_id and ext_dev_id in device_map:
                    device_uuid = device_map[ext_dev_id].id

                # Resolve Location (from merchant location or account home location)
                location_uuid: uuid.UUID | None = None
                if ext_merch_id and ext_merch_id in merchant_map:
                    location_uuid = merchant_map[ext_merch_id].location_id
                if location_uuid is None:
                    location_uuid = account.home_location_id

                # Parse Amount
                try:
                    amount = Decimal(amount_str).quantize(Decimal("0.01"))
                    if amount <= Decimal("0.00"):
                        raise ValueError("Amount must be positive.")
                except Exception as err:
                    raise ValueError(
                        f"Invalid monetary amount '{amount_str}': {err}"
                    ) from err

                # Parse occurred_at
                try:
                    occurred_at = datetime.fromisoformat(occurred_str)
                    if occurred_at.tzinfo is None:
                        occurred_at = occurred_at.replace(tzinfo=UTC)
                except Exception as err:
                    raise ValueError(
                        f"Invalid ISO 8601 occurred_at '{occurred_str}': {err}"
                    ) from err

                # Compute canonical row hash for provenance
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

                # 3. Canonical Matching & Duplicate Check
                canonical_key = (namespace, account.id, ext_tx_id)

                # Case A: Duplicate within the same import attempt
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

                # Query existing canonical transaction from database
                existing_tx_stmt = select(Transaction).where(
                    Transaction.source_namespace == namespace,
                    Transaction.account_id == account.id,
                    Transaction.external_transaction_id == ext_tx_id,
                )
                existing_tx = (
                    await session.execute(existing_tx_stmt)
                ).scalar_one_or_none()

                if existing_tx is not None:
                    # Canonical match found! Evaluate the 7 core material fields
                    material_match = (
                        existing_tx.account_id == account.id
                        and existing_tx.amount == amount
                        and existing_tx.currency == currency
                        and existing_tx.occurred_at == occurred_at
                        and existing_tx.transaction_type == tx_type
                        and existing_tx.direction == direction
                        and existing_tx.counterparty_account_id == cp_account_id
                    )

                    if material_match:
                        # Case B: Contextual Metadata Divergence -> MATCHED_EXISTING
                        # Preserve immutable canonical transaction facts
                        matched_existing_count += 1
                        valid_rows += 1
                        import_seen_canonical[canonical_key] = existing_tx.id
                        batch_records.append(
                            TransactionImportRecord(
                                dataset_import_id=import_id,
                                source_row_number=row_number,
                                transaction_id=existing_tx.id,
                                row_hash=row_hash,
                                outcome="MATCHED_EXISTING",
                            )
                        )
                    else:
                        # Case C: Core Material Conflict -> QUARANTINED
                        quarantined_count += 1
                        invalid_rows += 1
                        error_count += 1
                        import_seen_canonical[canonical_key] = None
                        batch_records.append(
                            TransactionImportRecord(
                                dataset_import_id=import_id,
                                source_row_number=row_number,
                                transaction_id=None,
                                row_hash=row_hash,
                                outcome="QUARANTINED",
                            )
                        )
                        batch_errors.append(
                            DatasetImportError(
                                dataset_import_id=import_id,
                                row_number=row_number,
                                field_name="amount",
                                error_code="MATERIAL_CONFLICT",
                                message=(
                                    f"Row collides with existing canonical transaction '{ext_tx_id}' "
                                    "but core material fields differ. Quarantined."
                                ),
                            )
                        )
                else:
                    # Case D: New Canonical Transaction -> INSERTED
                    new_txn = Transaction(
                        source_namespace=namespace,
                        external_transaction_id=ext_tx_id,
                        first_seen_import_id=import_id,
                        account_id=account.id,
                        counterparty_account_id=cp_account_id,
                        merchant_id=merchant_uuid,
                        device_id=device_uuid,
                        location_id=location_uuid,
                        occurred_at=occurred_at,
                        amount=amount,
                        currency=currency,
                        transaction_type=tx_type,
                        direction=direction,
                        category=category,
                        payment_method=payment_method,
                        channel=channel,
                    )
                    session.add(new_txn)
                    await session.flush()

                    inserted_count += 1
                    valid_rows += 1
                    import_seen_canonical[canonical_key] = new_txn.id

                    batch_records.append(
                        TransactionImportRecord(
                            dataset_import_id=import_id,
                            source_row_number=row_number,
                            transaction_id=new_txn.id,
                            row_hash=row_hash,
                            outcome="INSERTED",
                        )
                    )

            except Exception as row_err:
                # Case E: Rejected / Malformed Source Row
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

            # Flush batch
            if len(batch_records) >= self.batch_size:
                session.add_all(batch_records)
                session.add_all(batch_errors)
                if self.commit_per_batch:
                    await session.commit()
                else:
                    await session.flush()
                batch_records.clear()
                batch_errors.clear()

        # Flush any remaining items in final batch
        if batch_records:
            session.add_all(batch_records)
        if batch_errors:
            session.add_all(batch_errors)
        if self.commit_per_batch:
            await session.commit()
        else:
            await session.flush()

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
        csv_source: str | io.StringIO,
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
