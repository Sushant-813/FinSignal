"""Dataset import orchestration service with advisory locking and deduplication (P4.5)."""

import csv
import hashlib
import io
import logging
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.common.exceptions import ConflictError, NotFoundError, ValidationError
from finsignal.dataset.ingestion.engine import TransactionIngestionEngine
from finsignal.dataset.ingestion.locking import acquire_import_advisory_lock
from finsignal.dataset.models import DatasetImport, DatasetImportError
from finsignal.dataset.repository import DatasetImportRepository
from finsignal.dataset.schemas import (
    DatasetImportDetailResponse,
    DatasetImportErrorItem,
    DatasetImportListResponse,
    DatasetImportResponse,
)

logger = logging.getLogger("finsignal.dataset.service")

NAMESPACE_PATTERN = re.compile(r"^[A-Z0-9_]{3,64}$")
ALLOWED_IMPORT_STATUSES: frozenset[str] = frozenset(
    {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}
)


class DatasetImportService:
    """Orchestrates file upload verification, advisory locking, deduplication, and ingestion."""

    def __init__(
        self,
        ingestion_engine: TransactionIngestionEngine | None = None,
        import_repo: DatasetImportRepository | None = None,
    ) -> None:
        self.engine = ingestion_engine or TransactionIngestionEngine()
        self.import_repo = import_repo or DatasetImportRepository()

    def _validate_namespace(self, namespace: str) -> str:
        """Validate namespace format against canonical regex."""
        if not NAMESPACE_PATTERN.match(namespace):
            raise ValidationError(
                message=(
                    f"Invalid namespace format: '{namespace}'. "
                    "Must match ^[A-Z0-9_]{3,64}$."
                ),
                code="INVALID_NAMESPACE_FORMAT",
                details={"source_namespace": namespace},
            )
        return namespace

    def _normalize_utc_datetime(
        self, value: datetime | None, field_name: str
    ) -> datetime | None:
        """Reject naive datetimes and normalize timezone-aware datetimes to UTC."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(
                message=f"Parameter '{field_name}' must include timezone information (UTC ISO 8601).",
                code="INVALID_TIMEZONE",
                details={"field": field_name},
            )
        return value.astimezone(UTC)

    async def list_imports(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        source_namespace: str = "SYNTHETIC",
        status: str | None = None,
        source_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> DatasetImportListResponse:
        """List paginated dataset import summaries without validation error collections."""
        norm_ns = self._validate_namespace(source_namespace)
        norm_from = self._normalize_utc_datetime(from_time, "from_time")
        norm_to = self._normalize_utc_datetime(to_time, "to_time")
        if norm_from is not None and norm_to is not None and norm_from >= norm_to:
            raise ValidationError(
                message="from_time must be strictly earlier than to_time.",
                code="INVALID_DATE_RANGE",
                details={
                    "from_time": norm_from.isoformat(),
                    "to_time": norm_to.isoformat(),
                },
            )

        if status is not None and status not in ALLOWED_IMPORT_STATUSES:
            raise ValidationError(
                message=f"Invalid status '{status}'. Must be one of {sorted(ALLOWED_IMPORT_STATUSES)}.",
                code="INVALID_IMPORT_STATUS",
                details={"status": status},
            )

        exists = await self.import_repo.verify_namespace_exists(session, norm_ns)
        if not exists:
            raise NotFoundError(
                message=f"Target namespace '{norm_ns}' does not exist.",
                code="NAMESPACE_NOT_FOUND",
                details={"source_namespace": norm_ns},
            )

        rows, total, total_pages = await self.import_repo.list_imports(
            session,
            source_namespace=norm_ns,
            page=page,
            page_size=page_size,
            status=status,
            source_type=source_type,
            from_time=norm_from,
            to_time=norm_to,
        )
        items = [DatasetImportResponse.model_validate(imp) for imp in rows]
        return DatasetImportListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def import_dataset(
        self,
        session: AsyncSession,
        file_bytes: bytes | None = None,
        filename: str | None = None,
        source_namespace: str = "SYNTHETIC",
        source_type: str = "SYNTHETIC",
        user_id: uuid.UUID | None = None,
        *,
        file_source: io.TextIOBase | None = None,
        file_hash: str | None = None,
    ) -> tuple[DatasetImportResponse, bool]:
        """Process an uploaded dataset CSV with transaction-scoped locking and deduplication.

        Returns:
            tuple[DatasetImportResponse, bool]: (response_model, is_completed_duplicate)
        """
        # 1. Validate namespace
        norm_ns = source_namespace.strip()
        if not NAMESPACE_PATTERN.match(norm_ns):
            raise ValidationError(
                message=f"Invalid source_namespace '{norm_ns}'. Must match pattern ^[A-Z0-9_]{{3,64}}$",
                details={"source_namespace": norm_ns},
            )

        # 2. Compute SHA-256 over uploaded bytes if not already provided by streaming hash
        if file_hash is None:
            if file_bytes is None:
                raise ValueError(
                    "Either file_source with file_hash or file_bytes must be provided."
                )
            file_hash = hashlib.sha256(file_bytes).hexdigest()

        # 3. Acquire transaction-scoped advisory lock (pg_advisory_xact_lock)
        await acquire_import_advisory_lock(session, norm_ns, file_hash)

        # 4. Check for existing import with identical (source_namespace, file_hash)
        stmt = (
            select(DatasetImport)
            .where(
                DatasetImport.source_namespace == norm_ns,
                DatasetImport.file_hash == file_hash,
            )
            .order_by(DatasetImport.created_at.desc())
        )
        existing_imports = (await session.execute(stmt)).scalars().all()

        for imp in existing_imports:
            if imp.status == "COMPLETED":
                logger.info(
                    "Deduplication match: returning existing completed import %s for hash %s in namespace %s",
                    imp.id,
                    file_hash,
                    norm_ns,
                )
                resp = DatasetImportResponse.model_validate(imp)
                resp.is_duplicate = True
                return resp, True
            elif imp.status in ("PENDING", "PROCESSING"):
                logger.warning(
                    "Concurrent active import detected: import %s for hash %s in namespace %s",
                    imp.id,
                    file_hash,
                    norm_ns,
                )
                raise ConflictError(
                    message="An import for this file is already in progress within this namespace.",
                    code="IMPORT_IN_PROGRESS",
                    details={
                        "active_import_id": str(imp.id),
                        "source_namespace": norm_ns,
                        "file_hash": file_hash,
                    },
                )
            elif imp.status == "FAILED":
                logger.info(
                    "Retrying/recovering failed import %s for hash %s in namespace %s",
                    imp.id,
                    file_hash,
                    norm_ns,
                )
                return await self.recover_import(
                    session,
                    imp,
                    file_bytes=file_bytes,
                    file_source=file_source,
                    file_hash=file_hash,
                )

        # 5. Create new DatasetImport attempt
        import_record = DatasetImport(
            source_namespace=norm_ns,
            filename=filename,
            file_hash=file_hash,
            source_type=source_type,
            initiated_by=user_id,
            status="PENDING",
        )
        session.add(import_record)
        await session.flush()

        # 6. Stream CSV rows into ingestion engine (SEC-02: Bounded Memory)
        if file_source is not None:
            csv_source = file_source
        elif file_bytes is not None:
            try:
                csv_text = file_bytes.decode("utf-8-sig")
                csv_source = io.StringIO(csv_text)
            except UnicodeDecodeError as dec_err:
                import_record.status = "FAILED"
                await session.commit()
                raise ValidationError(
                    message=f"Uploaded file must be valid UTF-8 text: {dec_err}",
                    details={"filename": filename},
                ) from dec_err
        else:
            raise ValueError("Either file_source or file_bytes must be provided.")

        try:
            await self.engine.ingest(
                session=session,
                dataset_import=import_record,
                csv_source=csv_source,
            )
        except UnicodeDecodeError as dec_err:
            import_record_id = import_record.id
            await session.rollback()
            rec = await session.get(DatasetImport, import_record_id)
            if rec is not None:
                rec.status = "FAILED"
                await session.commit()
            raise ValidationError(
                message=f"Uploaded file must be valid UTF-8 text: {dec_err}",
                details={"filename": filename},
            ) from dec_err
        except (csv.Error, ValueError) as csv_err:
            import_record_id = import_record.id
            await session.rollback()
            rec = await session.get(DatasetImport, import_record_id)
            if rec is not None:
                rec.status = "FAILED"
                await session.commit()
            raise ValidationError(
                message=f"CSV parsing error: {csv_err}",
                details={"filename": filename, "error": str(csv_err)},
            ) from csv_err

        await session.commit()

        resp = DatasetImportResponse.model_validate(import_record)
        resp.is_duplicate = False
        return resp, False

    async def get_import_by_id(
        self,
        session: AsyncSession,
        import_id: uuid.UUID,
    ) -> DatasetImportDetailResponse:
        """Retrieve dataset import status and recorded error details."""
        stmt = select(DatasetImport).where(DatasetImport.id == import_id)
        import_record = (await session.execute(stmt)).scalar_one_or_none()
        if import_record is None:
            raise NotFoundError(
                message=f"Dataset import '{import_id}' was not found.",
                details={"import_id": str(import_id)},
            )

        err_stmt = (
            select(DatasetImportError)
            .where(DatasetImportError.dataset_import_id == import_id)
            .order_by(DatasetImportError.row_number.asc().nulls_last())
            .limit(100)
        )
        errors = (await session.execute(err_stmt)).scalars().all()
        error_items = [DatasetImportErrorItem.model_validate(e) for e in errors]

        resp = DatasetImportDetailResponse.model_validate(import_record)
        resp.errors = error_items
        return resp

    async def recover_import(
        self,
        session: AsyncSession,
        dataset_import: DatasetImport,
        file_bytes: bytes | None = None,
        *,
        file_source: io.TextIOBase | None = None,
        file_hash: str | None = None,
    ) -> tuple[DatasetImportResponse, bool]:
        """Recover an interrupted or failed dataset import attempt (SEC-02)."""
        if file_source is not None:
            csv_source = file_source
        elif file_bytes is not None:
            try:
                csv_text = file_bytes.decode("utf-8-sig")
                csv_source = io.StringIO(csv_text)
            except UnicodeDecodeError as dec_err:
                dataset_import.status = "FAILED"
                await session.commit()
                raise ValidationError(
                    message=f"Uploaded file must be valid UTF-8 text: {dec_err}",
                    details={"filename": dataset_import.filename},
                ) from dec_err
        else:
            raise ValueError("Either file_source or file_bytes must be provided.")

        try:
            await self.engine.recover(
                session=session,
                dataset_import=dataset_import,
                csv_source=csv_source,
            )
        except UnicodeDecodeError as dec_err:
            import_id = dataset_import.id
            await session.rollback()
            rec = await session.get(DatasetImport, import_id)
            if rec is not None:
                rec.status = "FAILED"
                await session.commit()
            raise ValidationError(
                message=f"Uploaded file must be valid UTF-8 text: {dec_err}",
                details={"filename": dataset_import.filename},
            ) from dec_err
        except (csv.Error, ValueError) as csv_err:
            import_id = dataset_import.id
            await session.rollback()
            rec = await session.get(DatasetImport, import_id)
            if rec is not None:
                rec.status = "FAILED"
                await session.commit()
            raise ValidationError(
                message=f"CSV parsing error: {csv_err}",
                details={"filename": dataset_import.filename, "error": str(csv_err)},
            ) from csv_err

        await session.commit()

        resp = DatasetImportResponse.model_validate(dataset_import)
        resp.is_duplicate = False
        return resp, False

    async def recover_import_by_id(
        self,
        session: AsyncSession,
        import_id: uuid.UUID,
        file_bytes: bytes | None = None,
        *,
        file_source: io.TextIOBase | None = None,
        file_hash: str | None = None,
    ) -> DatasetImportResponse:
        """Explicitly recover an import by its UUID with uploaded file bytes or stream (SEC-02)."""
        stmt = select(DatasetImport).where(DatasetImport.id == import_id)
        import_record = (await session.execute(stmt)).scalar_one_or_none()
        if import_record is None:
            raise NotFoundError(
                message=f"Dataset import '{import_id}' was not found.",
                details={"import_id": str(import_id)},
            )

        if file_hash is None:
            if file_bytes is None:
                raise ValueError(
                    "Either file_source with file_hash or file_bytes must be provided."
                )
            file_hash = hashlib.sha256(file_bytes).hexdigest()

        if import_record.file_hash and import_record.file_hash != file_hash:
            raise ValidationError(
                message="Uploaded file content does not match the original import file hash.",
                details={
                    "expected_hash": import_record.file_hash,
                    "actual_hash": file_hash,
                },
            )

        await acquire_import_advisory_lock(
            session, import_record.source_namespace, file_hash
        )
        await session.refresh(import_record)
        resp, _ = await self.recover_import(
            session,
            import_record,
            file_bytes=file_bytes,
            file_source=file_source,
            file_hash=file_hash,
        )
        return resp
