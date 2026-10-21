"""Dataset import orchestration service with advisory locking and deduplication (P4.5)."""

import hashlib
import io
import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.common.exceptions import ConflictError, NotFoundError, ValidationError
from finsignal.dataset.ingestion.engine import TransactionIngestionEngine
from finsignal.dataset.ingestion.locking import acquire_import_advisory_lock
from finsignal.dataset.models import DatasetImport, DatasetImportError
from finsignal.dataset.schemas import (
    DatasetImportDetailResponse,
    DatasetImportErrorItem,
    DatasetImportResponse,
)

logger = logging.getLogger("finsignal.dataset.service")

NAMESPACE_PATTERN = re.compile(r"^[A-Z0-9_]{3,64}$")


class DatasetImportService:
    """Orchestrates file upload verification, advisory locking, deduplication, and ingestion."""

    def __init__(
        self, ingestion_engine: TransactionIngestionEngine | None = None
    ) -> None:
        self.engine = ingestion_engine or TransactionIngestionEngine()

    async def import_dataset(
        self,
        session: AsyncSession,
        file_bytes: bytes,
        filename: str | None,
        source_namespace: str,
        source_type: str = "SYNTHETIC",
        user_id: uuid.UUID | None = None,
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

        # 2. Compute SHA-256 over uploaded bytes
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
                return await self.recover_import(session, imp, file_bytes)

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

        # 6. Decode bytes and run ingestion
        try:
            csv_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as dec_err:
            import_record.status = "FAILED"
            await session.flush()
            raise ValidationError(
                message=f"Uploaded file must be valid UTF-8 text: {dec_err}",
                details={"filename": filename},
            ) from dec_err

        await self.engine.ingest(
            session=session,
            dataset_import=import_record,
            csv_source=io.StringIO(csv_text),
        )

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
        file_bytes: bytes,
    ) -> tuple[DatasetImportResponse, bool]:
        """Recover an interrupted or failed dataset import attempt."""
        try:
            csv_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as dec_err:
            raise ValidationError(
                message=f"Uploaded file must be valid UTF-8 text: {dec_err}",
                details={"filename": dataset_import.filename},
            ) from dec_err

        await self.engine.recover(
            session=session,
            dataset_import=dataset_import,
            csv_source=io.StringIO(csv_text),
        )
        await session.commit()

        resp = DatasetImportResponse.model_validate(dataset_import)
        resp.is_duplicate = False
        return resp, False

    async def recover_import_by_id(
        self,
        session: AsyncSession,
        import_id: uuid.UUID,
        file_bytes: bytes,
    ) -> DatasetImportResponse:
        """Explicitly recover an import by its UUID with uploaded file bytes."""
        stmt = select(DatasetImport).where(DatasetImport.id == import_id)
        import_record = (await session.execute(stmt)).scalar_one_or_none()
        if import_record is None:
            raise NotFoundError(
                message=f"Dataset import '{import_id}' was not found.",
                details={"import_id": str(import_id)},
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
        resp, _ = await self.recover_import(session, import_record, file_bytes)
        return resp
