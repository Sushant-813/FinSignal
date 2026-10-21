"""Dataset ingestion package (ADR-064, ADR-065)."""

from finsignal.dataset.ingestion.engine import TransactionIngestionEngine
from finsignal.dataset.ingestion.schemas import ImportOutcome, IngestionSummary

__all__ = [
    "ImportOutcome",
    "IngestionSummary",
    "TransactionIngestionEngine",
]
