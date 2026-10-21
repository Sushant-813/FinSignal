"""Schemas for dataset ingestion engine and outcome summaries (P4.4)."""

import uuid
from dataclasses import dataclass
from typing import Literal

ImportOutcome = Literal[
    "INSERTED",
    "MATCHED_EXISTING",
    "DUPLICATE_IN_IMPORT",
    "QUARANTINED",
    "REJECTED",
]


@dataclass(frozen=True)
class IngestionSummary:
    """Summary of ingested CSV transactions and provenance outcomes."""

    import_id: uuid.UUID
    source_namespace: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    inserted_count: int
    matched_existing_count: int
    duplicate_in_import_count: int
    quarantined_count: int
    rejected_count: int
    error_count: int
