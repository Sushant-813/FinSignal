"""Deterministic CSV exporter with ground truth isolation and formula-injection defenses (P4.3)."""

import csv
import json
from pathlib import Path
from typing import Any

from finsignal.dataset.generator.schemas import GeneratedTransactionDataset


def sanitize_csv_value(val: Any) -> Any:
    """Neutralize spreadsheet formula-injection prefixes without corrupting data values.

    Prefixes '=', '+', '-', '@', '\t', '\r' are escaped with an apostrophe if present in strings.
    """
    if isinstance(val, str) and val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        # Prefix with single quote for spreadsheet safety if string starts with command char
        # Only escape if not a standard numeric negative string (e.g. not monetary, which are positive)
        return f"'{val}"
    return val


class CSVDatasetExporter:
    """Exports GeneratedTransactionDataset to deterministic, stable CSV and JSON artifacts."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def export(self, dataset: GeneratedTransactionDataset) -> dict[str, str]:
        """Export all 6 canonical artifacts and metadata.json into the target directory.

        Output files:
        1. accounts.csv
        2. merchants.csv
        3. devices.csv
        4. locations.csv
        5. transactions.csv (Production-facing, ZERO ground truth)
        6. transactions_ground_truth.csv (Ground truth isolation)
        7. metadata.json
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, str] = {}

        ref = dataset.reference_dataset

        # 1. accounts.csv
        acc_path = self.output_dir / "accounts.csv"
        with open(acc_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "account_id",
                    "source_namespace",
                    "account_type",
                    "customer_age",
                    "home_location_id",
                    "status",
                    "created_at",
                ]
            )
            for a in ref.accounts:
                writer.writerow(
                    [
                        a.account_id,
                        a.source_namespace,
                        a.account_type,
                        a.customer_age if a.customer_age is not None else "",
                        a.home_location_id,
                        a.status,
                        a.created_at.isoformat(),
                    ]
                )
        results["accounts"] = str(acc_path)

        # 2. merchants.csv
        merch_path = self.output_dir / "merchants.csv"
        with open(merch_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["merchant_id", "merchant_name", "merchant_category", "location_id"]
            )
            for m in ref.merchants:
                writer.writerow(
                    [
                        m.merchant_id,
                        sanitize_csv_value(m.merchant_name),
                        m.merchant_category,
                        m.location_id,
                    ]
                )
        results["merchants"] = str(merch_path)

        # 3. devices.csv
        dev_path = self.output_dir / "devices.csv"
        with open(dev_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["device_id", "device_type", "operating_system", "first_seen_at"]
            )
            for d in ref.devices:
                writer.writerow(
                    [
                        d.device_id,
                        d.device_type,
                        d.operating_system,
                        d.first_seen_at.isoformat(),
                    ]
                )
        results["devices"] = str(dev_path)

        # 4. locations.csv
        loc_path = self.output_dir / "locations.csv"
        with open(loc_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["location_id", "city", "state", "country", "latitude", "longitude"]
            )
            for loc in ref.locations:
                writer.writerow(
                    [
                        loc.location_id,
                        sanitize_csv_value(loc.city),
                        sanitize_csv_value(loc.state) if loc.state else "",
                        loc.country,
                        str(loc.latitude) if loc.latitude is not None else "",
                        str(loc.longitude) if loc.longitude is not None else "",
                    ]
                )
        results["locations"] = str(loc_path)

        # 5. transactions.csv (Strictly Production-Facing - ZERO Ground Truth)
        tx_path = self.output_dir / "transactions.csv"
        with open(tx_path, "w", newline="", encoding="utf-8") as f:
            self.export_transactions(dataset.transactions, f)
        results["transactions"] = str(tx_path)

        # 6. transactions_ground_truth.csv (Ground truth isolation)
        gt_path = self.output_dir / "transactions_ground_truth.csv"
        with open(gt_path, "w", newline="", encoding="utf-8") as f:
            self.export_ground_truth(dataset.ground_truth, f)
        results["ground_truth"] = str(gt_path)

        # 7. metadata.json
        meta_path = self.output_dir / "metadata.json"
        meta_dict = {
            "generator_version": dataset.metadata.generator_version,
            "seed": dataset.metadata.seed,
            "source_namespace": dataset.metadata.source_namespace,
            "account_count": dataset.metadata.account_count,
            "merchant_count": dataset.metadata.merchant_count,
            "device_count": dataset.metadata.device_count,
            "location_count": dataset.metadata.location_count,
            "transaction_count": dataset.metadata.transaction_count,
            "fraud_count": dataset.metadata.fraud_count,
            "achieved_fraud_rate": dataset.metadata.achieved_fraud_rate,
            "scenario_counts": dataset.metadata.scenario_counts,
            "period_start": dataset.metadata.period_start.isoformat(),
            "period_end": dataset.metadata.period_end.isoformat(),
            "config": dataset.metadata.config,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_dict, f, indent=2, sort_keys=True)
        results["metadata"] = str(meta_path)

        return results

    @staticmethod
    def export_transactions(transactions: list[Any], stream: Any) -> None:
        """Write production-facing transactions to a CSV text stream without ground truth."""
        writer = csv.writer(stream)
        writer.writerow(
            [
                "transaction_id",
                "source_namespace",
                "account_id",
                "counterparty_account_id",
                "merchant_id",
                "device_id",
                "location_id",
                "occurred_at",
                "amount",
                "currency",
                "transaction_type",
                "direction",
                "category",
                "payment_method",
                "channel",
            ]
        )
        for t in transactions:
            writer.writerow(
                [
                    t.transaction_id,
                    t.source_namespace,
                    t.account_id,
                    t.counterparty_account_id or "",
                    t.merchant_id or "",
                    t.device_id or "",
                    t.location_id or "",
                    t.occurred_at.isoformat(),
                    str(t.amount),
                    t.currency,
                    t.transaction_type,
                    t.direction,
                    t.category or "",
                    t.payment_method or "",
                    t.channel or "",
                ]
            )

    @staticmethod
    def export_ground_truth(ground_truth: list[Any], stream: Any) -> None:
        """Write ground-truth labels to an isolated CSV text stream."""
        writer = csv.writer(stream)
        writer.writerow(
            [
                "transaction_id",
                "is_fraud",
                "fraud_scenario",
                "scenario_instance_id",
                "anomaly_notes",
            ]
        )
        for gt in ground_truth:
            writer.writerow(
                [
                    gt.transaction_id,
                    "1" if gt.is_fraud else "0",
                    gt.fraud_scenario or "",
                    gt.scenario_instance_id or "",
                    sanitize_csv_value(gt.anomaly_notes) if gt.anomaly_notes else "",
                ]
            )
