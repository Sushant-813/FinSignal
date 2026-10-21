"""Dataset quality and integrity validation engine (P4.3)."""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from finsignal.dataset.generator.schemas import GeneratedTransactionDataset

CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class ValidationReport:
    """Outcome report for dataset structural and behavioral verification."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    stats: dict[str, Any]


class DatasetQualityValidator:
    """Validates structural constraints, relational consistency, and ground truth isolation."""

    def validate(self, dataset: GeneratedTransactionDataset) -> ValidationReport:
        """Execute comprehensive validation across references, transactions, and ground truth."""
        errors: list[str] = []
        warnings: list[str] = []

        ref = dataset.reference_dataset
        txns = dataset.transactions
        gts = dataset.ground_truth

        acc_ids = ref.account_ids
        merch_ids = ref.merchant_ids
        dev_ids = ref.device_ids
        loc_ids = ref.location_ids

        # 1. 1-to-1 Mapping between Transactions and Ground Truth
        if len(txns) != len(gts):
            errors.append(
                f"Count mismatch: {len(txns)} transactions vs {len(gts)} ground truth records."
            )

        # 2. Duplicate Transaction Identifiers
        seen_txn_ids: set[str] = set()
        for idx, t in enumerate(txns):
            if t.transaction_id in seen_txn_ids:
                errors.append(
                    f"Duplicate transaction_id: '{t.transaction_id}' at index {idx}."
                )
            seen_txn_ids.add(t.transaction_id)

        # 3. Ground Truth Matching
        for idx, (t, gt) in enumerate(zip(txns, gts, strict=False)):
            if t.transaction_id != gt.transaction_id:
                errors.append(
                    f"ID alignment error at index {idx}: transaction '{t.transaction_id}' != ground truth '{gt.transaction_id}'."
                )

        # 4. Foreign Key and Referential Integrity
        for t in txns:
            # Account reference
            if t.account_id not in acc_ids:
                errors.append(
                    f"Dangling account reference in txn {t.transaction_id}: {t.account_id}"
                )

            # Counterparty reference for transfers
            if t.transaction_type == "TRANSFER":
                if not t.counterparty_account_id:
                    errors.append(
                        f"Transfer txn {t.transaction_id} is missing counterparty_account_id."
                    )
                elif t.counterparty_account_id not in acc_ids:
                    errors.append(
                        f"Dangling counterparty account in txn {t.transaction_id}: {t.counterparty_account_id}"
                    )
                elif t.counterparty_account_id == t.account_id:
                    errors.append(
                        f"Self-transfer in txn {t.transaction_id}: account matches counterparty."
                    )
                if t.merchant_id is not None:
                    errors.append(
                        f"Transfer txn {t.transaction_id} must not have merchant_id."
                    )

            # Merchant reference
            if t.merchant_id is not None and t.merchant_id not in merch_ids:
                errors.append(
                    f"Dangling merchant reference in txn {t.transaction_id}: {t.merchant_id}"
                )

            # Device reference
            if t.device_id is not None and t.device_id not in dev_ids:
                errors.append(
                    f"Dangling device reference in txn {t.transaction_id}: {t.device_id}"
                )

            # Location reference
            if t.location_id is not None and t.location_id not in loc_ids:
                errors.append(
                    f"Dangling location reference in txn {t.transaction_id}: {t.location_id}"
                )

            # Monetary constraints
            if t.amount <= Decimal("0.00"):
                errors.append(
                    f"Non-positive amount in txn {t.transaction_id}: {t.amount}"
                )

            # Direction constraint
            if t.direction not in ("DEBIT", "CREDIT"):
                errors.append(
                    f"Invalid direction in txn {t.transaction_id}: {t.direction}"
                )

            # Currency constraint
            if not CURRENCY_REGEX.match(t.currency):
                errors.append(
                    f"Invalid currency format in txn {t.transaction_id}: {t.currency}"
                )

        # 5. Fraud Rate and Distribution Check
        fraud_txns = [gt for gt in gts if gt.is_fraud]
        total_fraud = len(fraud_txns)
        achieved_rate = total_fraud / len(txns) if txns else 0.0

        target_rate = dataset.config.fraud_rate
        rate_diff = abs(achieved_rate - target_rate)
        if rate_diff > 0.03:
            warnings.append(
                f"Achieved fraud rate {achieved_rate:.4f} deviates from target {target_rate:.4f} by {rate_diff:.4f}."
            )

        stats: dict[str, Any] = {
            "total_transactions": len(txns),
            "total_accounts": len(acc_ids),
            "total_merchants": len(merch_ids),
            "total_devices": len(dev_ids),
            "total_locations": len(loc_ids),
            "total_fraud": total_fraud,
            "achieved_fraud_rate": achieved_rate,
            "scenario_breakdown": dataset.metadata.scenario_counts,
        }

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
        )
