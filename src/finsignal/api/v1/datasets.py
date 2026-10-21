"""Dataset imports API v1 router and endpoint handlers (P4.5)."""

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
from finsignal.common.exceptions import ValidationError
from finsignal.core.database import get_db_session
from finsignal.dataset.schemas import (
    DatasetImportDetailResponse,
    DatasetImportResponse,
)
from finsignal.dataset.service import DatasetImportService
from finsignal.users.models import User

router = APIRouter(prefix="/datasets", tags=["Datasets"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB limit


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
    if not filename.lower().endswith(".csv"):
        raise ValidationError(
            message="Only CSV files (.csv) are accepted for dataset import.",
            details={"filename": filename},
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValidationError(
            message=f"File exceeds maximum allowable size of {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
            details={"file_size_bytes": len(file_bytes)},
        )

    if not file_bytes:
        raise ValidationError(
            message="Uploaded CSV file is empty.",
            details={"filename": filename},
        )

    import_resp, is_duplicate = await import_service.import_dataset(
        session=session,
        file_bytes=file_bytes,
        filename=filename,
        source_namespace=source_namespace,
        source_type=source_type,
        user_id=current_user.id,
    )

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
    filename = file.filename or "unknown.csv"
    if not filename.lower().endswith(".csv"):
        raise ValidationError(
            message="Only CSV files (.csv) are accepted for dataset import recovery.",
            details={"filename": filename},
        )
    file_bytes = await file.read()
    if not file_bytes:
        raise ValidationError(
            message="Uploaded CSV file is empty.",
            details={"filename": filename},
        )
    return await import_service.recover_import_by_id(
        session=session,
        import_id=import_id,
        file_bytes=file_bytes,
    )
