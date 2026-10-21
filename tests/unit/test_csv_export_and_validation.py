"""Unit tests for CSV dataset export, formula injection sanitization, and quality validation (P4.3)."""

import csv
import json
import tempfile
from pathlib import Path

from finsignal.dataset.generator import (
    CSVDatasetExporter,
    DatasetQualityValidator,
    GeneratorConfig,
    ReferenceEntityGenerator,
    TransactionDatasetGenerator,
    sanitize_csv_value,
)


def test_sanitize_csv_value() -> None:
    """Verify formula injection characters are escaped with an apostrophe."""
    assert sanitize_csv_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_csv_value("+cmd|'/c calc'!A0") == "'+cmd|'/c calc'!A0"
    assert sanitize_csv_value("-12345") == "'-12345"
    assert sanitize_csv_value("@SUM(B1)") == "'@SUM(B1)"
    assert sanitize_csv_value("\tcmd") == "'\tcmd"
    assert sanitize_csv_value("Normal Text") == "Normal Text"
    assert sanitize_csv_value(1234) == 1234


def test_csv_export_creates_all_artifacts() -> None:
    """Verify CSV exporter produces all canonical artifacts and validates ground truth isolation."""
    cfg = GeneratorConfig(
        seed=123,
        source_namespace="SYNTHETIC",
        account_count=10,
        merchant_count=5,
        device_count=15,
        location_count=3,
        transaction_count=50,
        fraud_rate=0.06,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    dataset = TransactionDatasetGenerator(cfg, ref_ds).generate()

    with tempfile.TemporaryDirectory() as tmp_dir:
        exporter = CSVDatasetExporter(tmp_dir)
        exported = exporter.export(dataset)

        assert "accounts" in exported
        assert "merchants" in exported
        assert "devices" in exported
        assert "locations" in exported
        assert "transactions" in exported
        assert "ground_truth" in exported
        assert "metadata" in exported

        # 1. Verify transactions.csv has NO ground truth columns
        tx_path = Path(exported["transactions"])
        assert tx_path.exists()
        with open(tx_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert "is_fraud" not in headers
            assert "fraud_scenario" not in headers
            assert "scenario_instance_id" not in headers
            rows = list(reader)
            assert len(rows) == 50

        # 2. Verify transactions_ground_truth.csv
        gt_path = Path(exported["ground_truth"])
        assert gt_path.exists()
        with open(gt_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            gt_headers = next(reader)
            assert gt_headers == [
                "transaction_id",
                "is_fraud",
                "fraud_scenario",
                "scenario_instance_id",
                "anomaly_notes",
            ]
            gt_rows = list(reader)
            assert len(gt_rows) == 50

        # 3. Verify metadata.json
        meta_path = Path(exported["metadata"])
        assert meta_path.exists()
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
            assert meta["transaction_count"] == 50
            assert meta["source_namespace"] == "SYNTHETIC"
            assert "scenario_counts" in meta


def test_dataset_quality_validator_passes() -> None:
    """Verify validator accepts clean generated dataset."""
    cfg = GeneratorConfig(
        seed=456,
        source_namespace="SYNTHETIC",
        account_count=8,
        merchant_count=5,
        device_count=12,
        location_count=3,
        transaction_count=40,
        fraud_rate=0.05,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    dataset = TransactionDatasetGenerator(cfg, ref_ds).generate()

    validator = DatasetQualityValidator()
    report = validator.validate(dataset)

    assert report.is_valid
    assert len(report.errors) == 0
    assert report.stats["total_transactions"] == 40
    assert report.stats["total_accounts"] == 8
