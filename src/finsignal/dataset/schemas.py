"""Pydantic schemas for dataset imports API (P4.5)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetImportResponse(BaseModel):
    """Summary of a dataset import."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_namespace: str
    status: str
    source_type: str
    filename: str | None = None
    file_hash: str | None = None
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    started_at: datetime
    completed_at: datetime | None = None
    is_duplicate: bool = Field(
        default=False,
        description="True if this response reflects an existing completed identical upload.",
    )


class DatasetImportErrorItem(BaseModel):
    """Validation or processing error record."""

    model_config = ConfigDict(from_attributes=True)

    row_number: int | None = None
    field_name: str | None = None
    error_code: str
    message: str


class DatasetImportDetailResponse(DatasetImportResponse):
    """Detailed summary of a dataset import including recorded errors."""

    errors: list[DatasetImportErrorItem] = Field(default_factory=list)
