"""Synthetic dataset generator package (ADR-029, ADR-064, ADR-065)."""

from typing import Any

from finsignal.dataset.generator.config import GeneratorConfig
from finsignal.dataset.generator.csv_exporter import (
    CSVDatasetExporter,
    sanitize_csv_value,
)
from finsignal.dataset.generator.identifiers import (
    format_account_id,
    format_device_id,
    format_location_id,
    format_merchant_id,
    format_transaction_id,
    is_valid_account_id,
    is_valid_device_id,
    is_valid_location_id,
    is_valid_merchant_id,
    is_valid_transaction_id,
)
from finsignal.dataset.generator.persistence import (
    ReferenceEntityPersistenceService,
    ReferencePersistenceSummary,
)
from finsignal.dataset.generator.random_streams import (
    derive_seed,
    get_domain_rng,
    get_entity_rng,
)
from finsignal.dataset.generator.reference_generator import ReferenceEntityGenerator
from finsignal.dataset.generator.schemas import (
    DatasetMetadata,
    GeneratedAccount,
    GeneratedAccountDevice,
    GeneratedDevice,
    GeneratedGroundTruth,
    GeneratedLocation,
    GeneratedMerchant,
    GeneratedReferenceDataset,
    GeneratedTransaction,
    GeneratedTransactionDataset,
)
from finsignal.dataset.generator.transaction_generator import (
    TransactionDatasetGenerator,
)
from finsignal.dataset.generator.validator import (
    DatasetQualityValidator,
    ValidationReport,
)


def run_scale_verification(*args: Any, **kwargs: Any) -> Any:
    """Execute scale generation, export to CSV, and validate quality."""
    from finsignal.dataset.generator.scale_verification import (
        run_scale_verification as _rsv,
    )

    return _rsv(*args, **kwargs)


__all__ = [
    "CSVDatasetExporter",
    "DatasetMetadata",
    "DatasetQualityValidator",
    "GeneratedAccount",
    "GeneratedAccountDevice",
    "GeneratedDevice",
    "GeneratedGroundTruth",
    "GeneratedLocation",
    "GeneratedMerchant",
    "GeneratedReferenceDataset",
    "GeneratedTransaction",
    "GeneratedTransactionDataset",
    "GeneratorConfig",
    "ReferenceEntityGenerator",
    "ReferenceEntityPersistenceService",
    "ReferencePersistenceSummary",
    "TransactionDatasetGenerator",
    "ValidationReport",
    "run_scale_verification",
    "derive_seed",
    "format_account_id",
    "format_device_id",
    "format_location_id",
    "format_merchant_id",
    "format_transaction_id",
    "get_domain_rng",
    "get_entity_rng",
    "is_valid_account_id",
    "is_valid_device_id",
    "is_valid_location_id",
    "is_valid_merchant_id",
    "is_valid_transaction_id",
    "sanitize_csv_value",
]
