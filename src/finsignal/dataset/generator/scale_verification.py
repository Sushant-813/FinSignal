"""Scale verification runner for progressive synthetic dataset generation (P4.3).

Supports:
- small:  100 accounts, 50 merchants, 200 devices, 20 locations, 5,000 transactions
- medium: 1,000 accounts, 250 merchants, 2,000 devices, 50 locations, 50,000 transactions
- full:   5,000 accounts, 500 merchants, 8,000 devices, 100 locations, 250,000 transactions

Usage:
    python -m finsignal.dataset.generator.scale_verification --scale small
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from finsignal.dataset.generator.config import GeneratorConfig
from finsignal.dataset.generator.csv_exporter import CSVDatasetExporter
from finsignal.dataset.generator.reference_generator import ReferenceEntityGenerator
from finsignal.dataset.generator.transaction_generator import (
    TransactionDatasetGenerator,
)
from finsignal.dataset.generator.validator import DatasetQualityValidator


def run_scale_verification(
    scale: str = "small",
    output_dir: str | Path | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Execute scale generation, export to CSV, and validate quality."""
    start_total = time.perf_counter()

    if scale == "small":
        cfg = GeneratorConfig.small(seed=seed)
    elif scale == "medium":
        cfg = GeneratorConfig.medium(seed=seed)
    elif scale == "full":
        cfg = GeneratorConfig.full(seed=seed)
    else:
        raise ValueError(
            f"Unknown scale '{scale}'. Choose 'small', 'medium', or 'full'."
        )

    # 1. Reference entity generation
    t0 = time.perf_counter()
    ref_gen = ReferenceEntityGenerator(cfg)
    ref_dataset = ref_gen.generate()
    ref_time = time.perf_counter() - t0

    # 2. Transaction generation
    t1 = time.perf_counter()
    tx_gen = TransactionDatasetGenerator(cfg, ref_dataset)
    dataset = tx_gen.generate()
    tx_time = time.perf_counter() - t1

    # 3. CSV Export
    t2 = time.perf_counter()
    if output_dir is None:
        temp_dir_ctx = tempfile.TemporaryDirectory()
        target_dir = Path(temp_dir_ctx.name)
    else:
        temp_dir_ctx = None
        target_dir = Path(output_dir)

    exporter = CSVDatasetExporter(target_dir)
    exported_paths = exporter.export(dataset)
    export_time = time.perf_counter() - t2

    # 4. Data Quality Validation
    t3 = time.perf_counter()
    validator = DatasetQualityValidator()
    report = validator.validate(dataset)
    validation_time = time.perf_counter() - t3

    total_time = time.perf_counter() - start_total

    results = {
        "scale": scale,
        "seed": seed,
        "accounts": len(ref_dataset.accounts),
        "merchants": len(ref_dataset.merchants),
        "devices": len(ref_dataset.devices),
        "locations": len(ref_dataset.locations),
        "transactions": len(dataset.transactions),
        "ground_truth_records": len(dataset.ground_truth),
        "fraud_count": dataset.metadata.fraud_count,
        "achieved_fraud_rate": dataset.metadata.achieved_fraud_rate,
        "scenario_counts": dataset.metadata.scenario_counts,
        "is_valid": report.is_valid,
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "timings": {
            "reference_generation_seconds": round(ref_time, 3),
            "transaction_generation_seconds": round(tx_time, 3),
            "csv_export_seconds": round(export_time, 3),
            "validation_seconds": round(validation_time, 3),
            "total_seconds": round(total_time, 3),
        },
        "exported_files": list(exported_paths.keys()),
    }

    if temp_dir_ctx is not None:
        temp_dir_ctx.cleanup()

    return results


def main() -> None:
    """CLI entry point for scale verification."""
    parser = argparse.ArgumentParser(description="FinSignal Dataset Scale Verification")
    parser.add_argument(
        "--scale",
        choices=["small", "medium", "full"],
        default="small",
        help="Scale target: small (5k tx), medium (50k tx), full (250k tx)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Optional directory to persist generated CSV artifacts",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic master seed",
    )
    args = parser.parse_args()

    print(f"=== Starting Scale Verification: {args.scale.upper()} ===")
    res = run_scale_verification(
        scale=args.scale, output_dir=args.output_dir, seed=args.seed
    )

    print(f"Scale: {res['scale']}")
    print(f"Accounts: {res['accounts']}")
    print(f"Merchants: {res['merchants']}")
    print(f"Devices: {res['devices']}")
    print(f"Locations: {res['locations']}")
    print(f"Transactions: {res['transactions']}")
    print(f"Fraud count: {res['fraud_count']} ({res['achieved_fraud_rate']:.4%})")
    print(f"Scenario distribution: {res['scenario_counts']}")
    print(
        f"Validation passed: {res['is_valid']} (errors: {res['error_count']}, warnings: {res['warning_count']})"
    )
    print(f"Timings: {res['timings']}")

    if not res["is_valid"]:
        print("ERROR: Dataset validation failed!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
