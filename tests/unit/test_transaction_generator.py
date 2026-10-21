"""Unit tests for transaction generation and fraud scenarios F001-F007 (P4.2)."""

from decimal import Decimal
from typing import Any

from finsignal.dataset.generator import (
    GeneratorConfig,
    ReferenceEntityGenerator,
    TransactionDatasetGenerator,
)
from finsignal.dataset.generator.identifiers import (
    is_valid_account_id,
    is_valid_device_id,
    is_valid_location_id,
    is_valid_merchant_id,
    is_valid_transaction_id,
)


def _generate_test_dataset(
    seed: int = 42, txn_count: int = 300, fraud_rate: float = 0.05
) -> Any:

    cfg = GeneratorConfig(
        seed=seed,
        source_namespace="SYNTHETIC",
        account_count=15,
        merchant_count=10,
        device_count=25,
        location_count=5,
        transaction_count=txn_count,
        fraud_rate=fraud_rate,
        period_days=60,
    )
    ref_ds = ReferenceEntityGenerator(cfg).generate()
    tx_gen = TransactionDatasetGenerator(cfg, ref_ds)
    return cfg, ref_ds, tx_gen.generate()


def test_transaction_generator_counts_and_identifiers() -> None:
    """Verify that generated transaction count and identifiers adhere to specifications."""
    _, _, dataset = _generate_test_dataset(txn_count=200)

    assert len(dataset.transactions) == 200
    assert len(dataset.ground_truth) == 200

    ref_acc_ids = dataset.reference_dataset.account_ids
    ref_merch_ids = dataset.reference_dataset.merchant_ids
    ref_dev_ids = dataset.reference_dataset.device_ids
    ref_loc_ids = dataset.reference_dataset.location_ids

    for t in dataset.transactions:
        assert is_valid_transaction_id(t.transaction_id)
        assert is_valid_account_id(t.account_id)
        assert t.account_id in ref_acc_ids

        assert t.amount > Decimal("0.00")
        assert t.currency == "INR"
        assert t.direction in ("DEBIT", "CREDIT")
        assert t.transaction_type in (
            "PURCHASE",
            "TRANSFER",
            "WITHDRAWAL",
            "BILL_PAYMENT",
        )

        if t.transaction_type == "TRANSFER":
            assert t.counterparty_account_id is not None
            assert is_valid_account_id(t.counterparty_account_id)
            assert t.counterparty_account_id in ref_acc_ids
            assert t.account_id != t.counterparty_account_id
            assert t.merchant_id is None
        elif t.transaction_type == "PURCHASE" and t.merchant_id is not None:
            assert is_valid_merchant_id(t.merchant_id)
            assert t.merchant_id in ref_merch_ids
            assert t.counterparty_account_id is None

        if t.device_id is not None:
            assert is_valid_device_id(t.device_id)
            assert t.device_id in ref_dev_ids

        if t.location_id is not None:
            assert is_valid_location_id(t.location_id)
            assert t.location_id in ref_loc_ids


def test_ground_truth_isolation() -> None:
    """Verify ground truth is strictly decoupled and never leaked into transaction entities."""
    _, _, dataset = _generate_test_dataset(txn_count=100, fraud_rate=0.10)

    for t in dataset.transactions:
        # Transactions must not have fraud attributes
        assert not hasattr(t, "is_fraud")
        assert not hasattr(t, "fraud_scenario")
        assert not hasattr(t, "scenario_instance_id")

    for gt in dataset.ground_truth:
        assert isinstance(gt.is_fraud, bool)
        if gt.is_fraud:
            assert gt.fraud_scenario in (
                "F001",
                "F002",
                "F003",
                "F004",
                "F005",
                "F006",
                "F007",
            )
            assert gt.scenario_instance_id is not None
        else:
            assert gt.fraud_scenario is None
            assert gt.scenario_instance_id is None


def test_all_seven_fraud_scenarios_generated() -> None:
    """Verify that all scenarios F001 through F007 appear in a sufficient dataset."""
    _, _, dataset = _generate_test_dataset(txn_count=500, fraud_rate=0.08)

    observed_scenarios = {
        gt.fraud_scenario for gt in dataset.ground_truth if gt.is_fraud
    }
    expected_scenarios = {"F001", "F002", "F003", "F004", "F005", "F006", "F007"}
    assert expected_scenarios.issubset(observed_scenarios)


def test_transaction_generator_determinism() -> None:
    """Verify identical seeds produce identical transaction sequences and amounts."""
    cfg1, _, ds1 = _generate_test_dataset(seed=999, txn_count=150)
    cfg2, _, ds2 = _generate_test_dataset(seed=999, txn_count=150)

    assert ds1.transactions == ds2.transactions
    assert ds1.ground_truth == ds2.ground_truth
    assert ds1.metadata.achieved_fraud_rate == ds2.metadata.achieved_fraud_rate


def test_transaction_to_ground_truth_mapping_and_sequence_integrity() -> None:
    """Verify 1:1 mapping, multi-step scenario sequence consistency, and isolation."""
    from collections import defaultdict

    _, _, dataset = _generate_test_dataset(txn_count=1000, fraud_rate=0.10)

    # 1. Exact 1:1 matching of transaction IDs in exact sequence
    tx_ids = [t.transaction_id for t in dataset.transactions]
    gt_ids = [gt.transaction_id for gt in dataset.ground_truth]
    assert tx_ids == gt_ids
    assert len(set(tx_ids)) == 1000

    # 2. Consistency of labels and scenario instance membership
    tx_map = {t.transaction_id: t for t in dataset.transactions}
    scenario_instance_txns = defaultdict(list)

    for gt in dataset.ground_truth:
        t = tx_map[gt.transaction_id]
        if gt.is_fraud:
            assert gt.fraud_scenario in {f"F{i:03d}" for i in range(1, 8)}
            assert gt.scenario_instance_id is not None
            assert gt.anomaly_notes is not None
            scenario_instance_txns[gt.scenario_instance_id].append((t, gt))
        else:
            assert gt.fraud_scenario is None
            assert gt.scenario_instance_id is None
            assert gt.anomaly_notes is None

    # 3. Multi-transaction scenario validation (F005, F006, F007)
    for instance_id, members in scenario_instance_txns.items():
        scenarios = {gt.fraud_scenario for _, gt in members}
        assert len(scenarios) == 1, (
            f"Instance {instance_id} has mixed scenarios: {scenarios}"
        )
        scn = scenarios.pop()

        if scn in ("F005", "F006"):
            assert len(members) == 4, (
                f"Scenario {scn} instance {instance_id} expected 4 txns, got {len(members)}"
            )
        elif scn == "F007":
            assert len(members) == 3, (
                f"Scenario F007 instance {instance_id} expected 3 txns, got {len(members)}"
            )
        else:
            assert len(members) == 1, (
                f"Scenario {scn} instance {instance_id} expected 1 txn, got {len(members)}"
            )

        # Check chronological consistency of multi-transaction steps
        member_times = [t.occurred_at for t, _ in members]
        assert member_times == sorted(member_times), (
            f"Instance {instance_id} steps not chronological"
        )
