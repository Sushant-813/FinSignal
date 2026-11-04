"""Dataset imports API v1 router and endpoint handlers (P4.5)."""

import hashlib
import io
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.dependencies import require_roles
from finsignal.common.exceptions import PayloadTooLargeError, ValidationError
from finsignal.core.database import get_db_session
from finsignal.dataset.schemas import (
    DatasetImportDetailResponse,
    DatasetImportResponse,
)
from finsignal.dataset.service import DatasetImportService
from finsignal.users.models import User

router = APIRouter(prefix="/datasets", tags=["Datasets"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB limit
UPLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB streaming buffer (SEC-02)


async def validate_and_hash_upload(file: UploadFile) -> str:
    """Validate upload size and compute SHA-256 incrementally in bounded memory (SEC-02)."""
    filename = file.filename or "unknown.csv"
    if not filename.lower().endswith(".csv"):
        raise ValidationError(
            message="Only CSV files (.csv) are accepted for dataset import.",
            details={"filename": filename},
        )

    hasher = hashlib.sha256()
    total_bytes = 0

    while chunk := await file.read(UPLOAD_CHUNK_SIZE):
        total_bytes += len(chunk)
        if total_bytes > MAX_UPLOAD_BYTES:
            raise PayloadTooLargeError(
                message=f"File exceeds maximum allowable size of {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
                details={"file_size_bytes": total_bytes},
            )
        hasher.update(chunk)

    if total_bytes == 0:
        raise ValidationError(
            message="Uploaded CSV file is empty.",
            details={"filename": filename},
        )

    await file.seek(0)
    return hasher.hexdigest()


def get_import_service() -> DatasetImportService:
    """Dependency provider for DatasetImportService."""
    return DatasetImportService()


@router.post(
    "/imports",
    response_model=DatasetImportResponse,
    summary="Upload and ingest a transaction dataset CSV",
)
async def upload_dataset_import(
    file: Annotated[UploadFile, File(description="Transaction CSV file to ingest")],
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_roles("ADMIN", "ANALYST"))],
    import_service: Annotated[DatasetImportService, Depends(get_import_service)],
    source_namespace: Annotated[
        str, Form(description="Target namespace partition")
    ] = "SYNTHETIC",
    source_type: Annotated[str, Form(description="Dataset source type")] = "SYNTHETIC",
) -> DatasetImportResponse:
    """Upload and ingest a financial transaction dataset CSV.

    Guarantees:
    - Enforces authentication and RBAC (ADMIN or ANALYST required).
    - Computes SHA-256 stream hash over uploaded bytes.
    - Serializes concurrent identical uploads via transaction-scoped PostgreSQL advisory locks.
    - Implements namespace-scoped deduplication:
        - Completed identical upload returns HTTP 200 with existing summary.
        - Active in-progress identical upload returns HTTP 409.
        - New upload processes in bounded batches, returning HTTP 201.
    - Enforces strict canonical matching, seven core material fields, and row-level provenance.
    """
    filename = file.filename or "unknown.csv"
    file_hash = await validate_and_hash_upload(file)
    text_stream = io.TextIOWrapper(file.file, encoding="utf-8-sig")

    try:
        import_resp, is_duplicate = await import_service.import_dataset(
            session=session,
            filename=filename,
            source_namespace=source_namespace,
            source_type=source_type,
            user_id=current_user.id,
            file_source=text_stream,
            file_hash=file_hash,
        )
    finally:
        text_stream.detach()

    if is_duplicate:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED

    return import_resp


@router.get(
    "/imports/{import_id}",
    response_model=DatasetImportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dataset import details and validation errors",
)
async def get_dataset_import_details(
    import_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[
        User, Depends(require_roles("ADMIN", "ANALYST", "INVESTIGATOR"))
    ],
    import_service: Annotated[DatasetImportService, Depends(get_import_service)],
) -> DatasetImportDetailResponse:
    """Retrieve detailed execution status and error logs for a specific dataset import."""
    return await import_service.get_import_by_id(session=session, import_id=import_id)


@router.post(
    "/imports/{import_id}/recover",
    response_model=DatasetImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Recover an interrupted or failed dataset import attempt",
)
async def recover_dataset_import(
    import_id: uuid.UUID,
    file: Annotated[
        UploadFile, File(description="Original CSV file to resume/recover")
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(require_roles("ADMIN", "ANALYST"))],
    import_service: Annotated[DatasetImportService, Depends(get_import_service)],
) -> DatasetImportResponse:
    """Recover a failed or interrupted dataset import without duplicating or skipping rows."""
    file_hash = await validate_and_hash_upload(file)
    text_stream = io.TextIOWrapper(file.file, encoding="utf-8-sig")

    try:
        return await import_service.recover_import_by_id(
            session=session,
            import_id=import_id,
            file_source=text_stream,
            file_hash=file_hash,
        )
    finally:
        text_stream.detach()
