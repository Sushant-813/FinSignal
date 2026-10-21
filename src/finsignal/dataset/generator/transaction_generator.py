"""Deterministic transaction and fraud scenario generator (P4.2).

Synthesizes realistic legitimate behavioral distributions across account profiles
and injects controlled anomalous fraud scenarios (F001–F007) with isolated ground truth.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from finsignal.dataset.generator.config import GeneratorConfig
from finsignal.dataset.generator.identifiers import format_transaction_id
from finsignal.dataset.generator.random_streams import (
    get_domain_rng,
    get_entity_rng,
)
from finsignal.dataset.generator.schemas import (
    DatasetMetadata,
    GeneratedGroundTruth,
    GeneratedReferenceDataset,
    GeneratedTransaction,
    GeneratedTransactionDataset,
)

# Reference baseline start: 2026-01-01 00:00:00 UTC
_BASE_EPOCH = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

_TRANSACTION_TYPES: tuple[str, ...] = (
    "PURCHASE",
    "TRANSFER",
    "WITHDRAWAL",
    "BILL_PAYMENT",
)
_DIRECTIONS: tuple[str, ...] = ("DEBIT", "CREDIT")
_PAYMENT_METHODS: tuple[str, ...] = ("UPI", "DEBIT_CARD", "CREDIT_CARD", "NET_BANKING")
_CHANNELS: tuple[str, ...] = ("MOBILE_APP", "POS_TERMINAL", "WEB_PORTAL", "ATM")


@dataclass(frozen=True)
class AccountBehaviorProfile:
    """Configures characteristic spending, schedule, and category tendencies for an account."""

    profile_name: str
    mean_amount: float
    std_amount: float
    min_amount: float
    max_amount: float
    active_start_hour: int
    active_end_hour: int
    preferred_categories: tuple[str, ...]
    preferred_types: tuple[str, ...]
    preferred_payment_methods: tuple[str, ...]
    preferred_channels: tuple[str, ...]


_PROFILES: dict[str, AccountBehaviorProfile] = {
    "LOW_SPENDER": AccountBehaviorProfile(
        profile_name="LOW_SPENDER",
        mean_amount=450.0,
        std_amount=200.0,
        min_amount=50.0,
        max_amount=2500.0,
        active_start_hour=7,
        active_end_hour=22,
        preferred_categories=("FOOD", "GROCERIES", "UTILITIES"),
        preferred_types=("PURCHASE", "BILL_PAYMENT", "TRANSFER"),
        preferred_payment_methods=("UPI", "DEBIT_CARD"),
        preferred_channels=("MOBILE_APP", "POS_TERMINAL"),
    ),
    "MODERATE_SPENDER": AccountBehaviorProfile(
        profile_name="MODERATE_SPENDER",
        mean_amount=1800.0,
        std_amount=800.0,
        min_amount=100.0,
        max_amount=12000.0,
        active_start_hour=8,
        active_end_hour=23,
        preferred_categories=(
            "FOOD",
            "GROCERIES",
            "SHOPPING",
            "ENTERTAINMENT",
            "SUBSCRIPTION",
        ),
        preferred_types=("PURCHASE", "BILL_PAYMENT", "TRANSFER", "WITHDRAWAL"),
        preferred_payment_methods=("UPI", "CREDIT_CARD", "DEBIT_CARD"),
        preferred_channels=("MOBILE_APP", "POS_TERMINAL", "WEB_PORTAL"),
    ),
    "HIGH_SPENDER": AccountBehaviorProfile(
        profile_name="HIGH_SPENDER",
        mean_amount=14000.0,
        std_amount=6000.0,
        min_amount=1000.0,
        max_amount=95000.0,
        active_start_hour=9,
        active_end_hour=24,
        preferred_categories=("TRAVEL", "HOTEL", "ELECTRONICS", "SHOPPING"),
        preferred_types=("PURCHASE", "TRANSFER"),
        preferred_payment_methods=("CREDIT_CARD", "NET_BANKING"),
        preferred_channels=("WEB_PORTAL", "POS_TERMINAL"),
    ),
    "SUBSCRIPTION_HEAVY": AccountBehaviorProfile(
        profile_name="SUBSCRIPTION_HEAVY",
        mean_amount=650.0,
        std_amount=300.0,
        min_amount=99.0,
        max_amount=4500.0,
        active_start_hour=10,
        active_end_hour=22,
        preferred_categories=("SUBSCRIPTION", "ENTERTAINMENT", "UTILITIES", "FOOD"),
        preferred_types=("PURCHASE", "BILL_PAYMENT"),
        preferred_payment_methods=("CREDIT_CARD", "UPI"),
        preferred_channels=("WEB_PORTAL", "MOBILE_APP"),
    ),
    "BUSINESS_LIKE": AccountBehaviorProfile(
        profile_name="BUSINESS_LIKE",
        mean_amount=32000.0,
        std_amount=15000.0,
        min_amount=2500.0,
        max_amount=180000.0,
        active_start_hour=9,
        active_end_hour=19,
        preferred_categories=("UTILITIES", "ELECTRONICS", "TRAVEL", "OTHER"),
        preferred_types=("TRANSFER", "BILL_PAYMENT", "PURCHASE"),
        preferred_payment_methods=("NET_BANKING", "CREDIT_CARD"),
        preferred_channels=("WEB_PORTAL",),
    ),
}


class TransactionDatasetGenerator:
    """Generates deterministic transaction datasets with legitimate distributions and fraud scenarios."""

    def __init__(
        self,
        config: GeneratorConfig,
        reference_dataset: GeneratedReferenceDataset,
    ) -> None:
        self.config = config
        self.reference_dataset = reference_dataset
        self.period_start = _BASE_EPOCH
        self.period_end = _BASE_EPOCH + timedelta(days=config.period_days)

        # Lookup caches for O(1) references
        self._accounts = reference_dataset.accounts
        self._account_ids = [a.account_id for a in self._accounts]
        self._account_map = {a.account_id: a for a in self._accounts}

        self._merchants = reference_dataset.merchants
        self._merchant_ids = [m.merchant_id for m in self._merchants]

        self._devices = reference_dataset.devices
        self._device_ids = [d.device_id for d in self._devices]

        self._locations = reference_dataset.locations
        self._location_ids = [loc.location_id for loc in self._locations]

        # Account-device mapping
        self._acc_to_devices: dict[str, list[str]] = {
            a.account_id: [] for a in self._accounts
        }
        for ad in reference_dataset.account_devices:
            self._acc_to_devices[ad.account_id].append(ad.device_id)

        # Assign deterministic behavioral profile per account
        self._account_profiles: dict[str, AccountBehaviorProfile] = {}
        for idx, acc in enumerate(self._accounts, start=1):
            if acc.account_type == "BUSINESS":
                prof = _PROFILES["BUSINESS_LIKE"]
            else:
                rng = get_entity_rng(
                    self.config.seed,
                    "account_profiles",
                    idx,
                    self.config.generator_version,
                )
                choice = rng.choices(
                    [
                        "LOW_SPENDER",
                        "MODERATE_SPENDER",
                        "HIGH_SPENDER",
                        "SUBSCRIPTION_HEAVY",
                    ],
                    weights=[0.45, 0.35, 0.10, 0.10],
                )[0]
                prof = _PROFILES[choice]
            self._account_profiles[acc.account_id] = prof

    def generate(self) -> GeneratedTransactionDataset:
        """Synthesize complete transaction dataset with isolated ground truth."""
        target_count = self.config.transaction_count
        target_fraud_count = int(round(target_count * self.config.fraud_rate))

        transactions: list[GeneratedTransaction] = []
        ground_truth: list[GeneratedGroundTruth] = []

        domain_rng = get_domain_rng(
            self.config.seed, "transaction_orchestrator", self.config.generator_version
        )

        # 1. Determine scenario quotas
        scenario_weights = self.config.scenario_distribution
        scenarios = list(scenario_weights.keys())
        weights = [scenario_weights[s] for s in scenarios]

        scenario_counts: dict[str, int] = {s: 0 for s in scenarios}
        fraud_instances_planned: list[str] = []

        assigned_fraud = 0
        # When fraud quota permits, ensure base representation of each configured scenario
        if target_fraud_count >= 15:
            for scn in scenarios:
                fraud_instances_planned.append(scn)
                assigned_fraud += (
                    4 if scn in ("F005", "F006") else (3 if scn == "F007" else 1)
                )

        while assigned_fraud < target_fraud_count:
            chosen_scenario = domain_rng.choices(scenarios, weights=weights)[0]
            fraud_instances_planned.append(chosen_scenario)
            # F005, F006, F007 involve multi-transaction bursts
            if chosen_scenario in ("F005", "F006"):
                assigned_fraud += 4
            elif chosen_scenario == "F007":
                assigned_fraud += 3
            else:
                assigned_fraud += 1

        # 2. Pre-generate fraud scenario blocks
        fraud_blocks: list[
            tuple[list[GeneratedTransaction], list[GeneratedGroundTruth]]
        ] = []

        for scenario_counter, scn in enumerate(fraud_instances_planned, start=1):
            scn_id = f"SCN_{scn}_{scenario_counter:06d}"
            # Pick a target account
            acc_idx = domain_rng.randint(0, len(self._accounts) - 1)
            target_account = self._accounts[acc_idx]

            txns, gts = self._generate_scenario_instance(
                scn, scn_id, target_account, scenario_counter
            )
            fraud_blocks.append((txns, gts))
            for _ in txns:
                scenario_counts[scn] = scenario_counts.get(scn, 0) + 1

        # Flatten planned fraud transactions
        fraud_txns: list[GeneratedTransaction] = []
        fraud_gts: list[GeneratedGroundTruth] = []
        for f_txns, f_gts in fraud_blocks:
            fraud_txns.extend(f_txns)
            fraud_gts.extend(f_gts)

        # Trim if multi-transaction expansions slightly exceeded target_count
        if len(fraud_txns) > target_count:
            fraud_txns = fraud_txns[:target_count]
            fraud_gts = fraud_gts[:target_count]

        legitimate_count = target_count - len(fraud_txns)

        # 3. Generate Legitimate Transactions
        legit_txns, legit_gts = self._generate_legitimate_transactions(legitimate_count)

        # 4. Merge, assign canonical deterministic IDs, and order by occurred_at
        all_raw_pairs = list(
            zip(legit_txns + fraud_txns, legit_gts + fraud_gts, strict=True)
        )
        # Sort chronologically
        all_raw_pairs.sort(key=lambda pair: pair[0].occurred_at)

        # Assign final sequential TXN_[0-9]{8} IDs
        for idx, (t, gt) in enumerate(all_raw_pairs, start=1):
            txn_id = format_transaction_id(idx)
            final_txn = GeneratedTransaction(
                transaction_id=txn_id,
                source_namespace=self.config.source_namespace,
                account_id=t.account_id,
                counterparty_account_id=t.counterparty_account_id,
                merchant_id=t.merchant_id,
                device_id=t.device_id,
                location_id=t.location_id,
                occurred_at=t.occurred_at,
                amount=t.amount,
                currency=t.currency,
                transaction_type=t.transaction_type,
                direction=t.direction,
                category=t.category,
                payment_method=t.payment_method,
                channel=t.channel,
            )
            final_gt = GeneratedGroundTruth(
                transaction_id=txn_id,
                is_fraud=gt.is_fraud,
                fraud_scenario=gt.fraud_scenario,
                scenario_instance_id=gt.scenario_instance_id,
                anomaly_notes=gt.anomaly_notes,
            )
            transactions.append(final_txn)
            ground_truth.append(final_gt)

        total_fraud = sum(1 for gt in ground_truth if gt.is_fraud)
        achieved_rate = total_fraud / len(transactions) if transactions else 0.0

        metadata = DatasetMetadata(
            generator_version=self.config.generator_version,
            seed=self.config.seed,
            source_namespace=self.config.source_namespace,
            account_count=len(self._accounts),
            merchant_count=len(self._merchants),
            device_count=len(self._devices),
            location_count=len(self._locations),
            transaction_count=len(transactions),
            fraud_count=total_fraud,
            achieved_fraud_rate=round(achieved_rate, 5),
            scenario_counts=scenario_counts,
            period_start=self.period_start,
            period_end=self.period_end,
            config=self.config.model_dump(),
        )

        return GeneratedTransactionDataset(
            reference_dataset=self.reference_dataset,
            transactions=transactions,
            ground_truth=ground_truth,
            metadata=metadata,
        )

    def _generate_legitimate_transactions(
        self, count: int
    ) -> tuple[list[GeneratedTransaction], list[GeneratedGroundTruth]]:
        """Generate normal, legitimate transactions adhering strictly to account behavioral profiles."""
        txns: list[GeneratedTransaction] = []
        gts: list[GeneratedGroundTruth] = []
        num_accounts = len(self._accounts)

        for i in range(1, count + 1):
            rng = get_entity_rng(
                self.config.seed, "legit_txns", i, self.config.generator_version
            )

            acc_idx = (i - 1) % num_accounts
            account = self._accounts[acc_idx]
            profile = self._account_profiles[account.account_id]

            # Plausible amount from profile lognormal / normal curve
            raw_amount = rng.gauss(profile.mean_amount, profile.std_amount)
            clamped_amount = max(
                profile.min_amount, min(profile.max_amount, raw_amount)
            )
            amount = Decimal(f"{clamped_amount:.2f}")

            # Active hour sampling
            hour = rng.randint(profile.active_start_hour, profile.active_end_hour)
            minute = rng.randint(0, 59)
            second = rng.randint(0, 59)

            # Date within period, but after account creation
            total_seconds = int((self.period_end - account.created_at).total_seconds())
            if total_seconds <= 86400:
                offset_sec = 86400
            else:
                offset_sec = rng.randint(86400, total_seconds)

            occurred_at = (account.created_at + timedelta(seconds=offset_sec)).replace(
                hour=hour % 24, minute=minute, second=second
            )

            # Transaction type, payment method, category
            tx_type = rng.choices(profile.preferred_types)[0]
            direction = "DEBIT"
            counterparty_id: str | None = None
            merchant_id: str | None = None
            category: str | None = None

            if tx_type == "TRANSFER":
                # Transfer to another account
                other_idx = (acc_idx + rng.randint(1, num_accounts - 1)) % num_accounts
                counterparty_id = self._accounts[other_idx].account_id
                category = "TRANSFER"
            else:
                category = rng.choices(profile.preferred_categories)[0]
                if tx_type == "PURCHASE" and self._merchants:
                    m_idx = rng.randint(0, len(self._merchants) - 1)
                    merchant_id = self._merchants[m_idx].merchant_id

            # Device selection: primary or normal device
            devices_for_acc = self._acc_to_devices.get(account.account_id, [])
            device_id = (
                rng.choice(devices_for_acc) if devices_for_acc else self._device_ids[0]
            )

            # Location: primary home location
            location_id = account.home_location_id

            payment_method = rng.choices(profile.preferred_payment_methods)[0]
            channel = rng.choices(profile.preferred_channels)[0]

            txn = GeneratedTransaction(
                transaction_id="",  # Finalized in orchestrator
                source_namespace=self.config.source_namespace,
                account_id=account.account_id,
                counterparty_account_id=counterparty_id,
                merchant_id=merchant_id,
                device_id=device_id,
                location_id=location_id,
                occurred_at=occurred_at,
                amount=amount,
                currency="INR",
                transaction_type=tx_type,
                direction=direction,
                category=category,
                payment_method=payment_method,
                channel=channel,
            )
            gt = GeneratedGroundTruth(
                transaction_id="",
                is_fraud=False,
                fraud_scenario=None,
                scenario_instance_id=None,
                anomaly_notes=None,
            )
            txns.append(txn)
            gts.append(gt)

        return txns, gts

    def _generate_scenario_instance(
        self,
        scenario: str,
        scenario_id: str,
        account: Any,
        instance_seq: int,
    ) -> tuple[list[GeneratedTransaction], list[GeneratedGroundTruth]]:
        """Synthesize a specific fraud scenario instance F001–F007."""
        rng = get_entity_rng(
            self.config.seed,
            f"scenario_{scenario}",
            instance_seq,
            self.config.generator_version,
        )
        profile = self._account_profiles[account.account_id]
        txns: list[GeneratedTransaction] = []
        gts: list[GeneratedGroundTruth] = []

        base_time = self.period_start + timedelta(
            days=rng.randint(15, self.config.period_days - 10),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )

        acc_devices = self._acc_to_devices.get(
            account.account_id, [self._device_ids[0]]
        )
        home_loc = account.home_location_id

        if scenario == "F001":
            # Large Amount Anomaly: 8x-15x profile max
            high_amount = Decimal(f"{profile.max_amount * rng.uniform(8.0, 15.0):.2f}")
            txn = GeneratedTransaction(
                transaction_id="",
                source_namespace=self.config.source_namespace,
                account_id=account.account_id,
                counterparty_account_id=None,
                merchant_id=self._merchant_ids[0],
                device_id=acc_devices[0],
                location_id=home_loc,
                occurred_at=base_time,
                amount=high_amount,
                currency="INR",
                transaction_type="PURCHASE",
                direction="DEBIT",
                category="ELECTRONICS",
                payment_method="NET_BANKING",
                channel="WEB_PORTAL",
            )
            gt = GeneratedGroundTruth(
                transaction_id="",
                is_fraud=True,
                fraud_scenario="F001",
                scenario_instance_id=scenario_id,
                anomaly_notes="Amount exceeds 8x profile historical ceiling",
            )
            txns.append(txn)
            gts.append(gt)

        elif scenario == "F002":
            # New Device Anomaly: device not associated with this account
            novel_devices = [d for d in self._device_ids if d not in acc_devices]
            novel_dev = (
                rng.choice(novel_devices) if novel_devices else self._device_ids[-1]
            )
            txn = GeneratedTransaction(
                transaction_id="",
                source_namespace=self.config.source_namespace,
                account_id=account.account_id,
                counterparty_account_id=None,
                merchant_id=self._merchant_ids[0],
                device_id=novel_dev,
                location_id=home_loc,
                occurred_at=base_time,
                amount=Decimal(f"{profile.mean_amount * 2.5:.2f}"),
                currency="INR",
                transaction_type="PURCHASE",
                direction="DEBIT",
                category="SHOPPING",
                payment_method="CREDIT_CARD",
                channel="MOBILE_APP",
            )
            gt = GeneratedGroundTruth(
                transaction_id="",
                is_fraud=True,
                fraud_scenario="F002",
                scenario_instance_id=scenario_id,
                anomaly_notes="Transaction initiated from unprecedented new device",
            )
            txns.append(txn)
            gts.append(gt)

        elif scenario == "F003":
            # New Location Anomaly: location remote from home_location_id
            remote_locs = [
                loc_id for loc_id in self._location_ids if loc_id != home_loc
            ]
            remote_loc = rng.choice(remote_locs) if remote_locs else home_loc
            txn = GeneratedTransaction(
                transaction_id="",
                source_namespace=self.config.source_namespace,
                account_id=account.account_id,
                counterparty_account_id=None,
                merchant_id=self._merchant_ids[0],
                device_id=acc_devices[0],
                location_id=remote_loc,
                occurred_at=base_time,
                amount=Decimal(f"{profile.mean_amount * 3.0:.2f}"),
                currency="INR",
                transaction_type="PURCHASE",
                direction="DEBIT",
                category="TRAVEL",
                payment_method="DEBIT_CARD",
                channel="POS_TERMINAL",
            )
            gt = GeneratedGroundTruth(
                transaction_id="",
                is_fraud=True,
                fraud_scenario="F003",
                scenario_instance_id=scenario_id,
                anomaly_notes="Transaction in unexpected geographic location",
            )
            txns.append(txn)
            gts.append(gt)

        elif scenario == "F004":
            # Unusual Transaction Time: 02:30-04:00 AM
            night_time = base_time.replace(hour=3, minute=rng.randint(15, 45))
            txn = GeneratedTransaction(
                transaction_id="",
                source_namespace=self.config.source_namespace,
                account_id=account.account_id,
                counterparty_account_id=None,
                merchant_id=self._merchant_ids[0],
                device_id=acc_devices[0],
                location_id=home_loc,
                occurred_at=night_time,
                amount=Decimal(f"{profile.mean_amount * 2.0:.2f}"),
                currency="INR",
                transaction_type="PURCHASE",
                direction="DEBIT",
                category="ENTERTAINMENT",
                payment_method="UPI",
                channel="MOBILE_APP",
            )
            gt = GeneratedGroundTruth(
                transaction_id="",
                is_fraud=True,
                fraud_scenario="F004",
                scenario_instance_id=scenario_id,
                anomaly_notes="Activity during deep dormant night window (03:00 AM)",
            )
            txns.append(txn)
            gts.append(gt)

        elif scenario == "F005":
            # High Transaction Velocity Burst: 4 rapid transactions 1-2 mins apart
            burst_time = base_time
            for step in range(4):
                step_time = burst_time + timedelta(minutes=step * 2 + rng.randint(0, 1))
                txn = GeneratedTransaction(
                    transaction_id="",
                    source_namespace=self.config.source_namespace,
                    account_id=account.account_id,
                    counterparty_account_id=None,
                    merchant_id=self._merchant_ids[step % len(self._merchant_ids)],
                    device_id=acc_devices[0],
                    location_id=home_loc,
                    occurred_at=step_time,
                    amount=Decimal(f"{profile.mean_amount * 1.5:.2f}"),
                    currency="INR",
                    transaction_type="PURCHASE",
                    direction="DEBIT",
                    category="SHOPPING",
                    payment_method="UPI",
                    channel="MOBILE_APP",
                )
                gt = GeneratedGroundTruth(
                    transaction_id="",
                    is_fraud=True,
                    fraud_scenario="F005",
                    scenario_instance_id=scenario_id,
                    anomaly_notes=f"Rapid velocity burst sequence step {step + 1}/4",
                )
                txns.append(txn)
                gts.append(gt)

        elif scenario == "F006":
            # Account Takeover Pattern: novel device + remote location + night hour + high amount transfer
            novel_devices = [d for d in self._device_ids if d not in acc_devices]
            novel_dev = (
                rng.choice(novel_devices) if novel_devices else self._device_ids[-1]
            )
            remote_locs = [
                loc_id for loc_id in self._location_ids if loc_id != home_loc
            ]
            remote_loc = rng.choice(remote_locs) if remote_locs else home_loc
            night_time = base_time.replace(hour=2, minute=rng.randint(10, 50))

            other_accounts = [
                a for a in self._accounts if a.account_id != account.account_id
            ]
            counterparty = (
                other_accounts[0].account_id if other_accounts else account.account_id
            )

            # Multi-step takeover: probe purchase -> massive drain transfer -> withdrawal
            steps_data = [
                ("PURCHASE", Decimal("150.00"), "FOOD", None),
                (
                    "TRANSFER",
                    Decimal(f"{profile.max_amount * 5.0:.2f}"),
                    "TRANSFER",
                    counterparty,
                ),
                (
                    "TRANSFER",
                    Decimal(f"{profile.max_amount * 4.0:.2f}"),
                    "TRANSFER",
                    counterparty,
                ),
                ("WITHDRAWAL", Decimal("20000.00"), "ATM", None),
            ]
            for step_idx, (t_type, amt, cat, cp) in enumerate(steps_data):
                step_time = night_time + timedelta(minutes=step_idx * 5)
                txn = GeneratedTransaction(
                    transaction_id="",
                    source_namespace=self.config.source_namespace,
                    account_id=account.account_id,
                    counterparty_account_id=cp,
                    merchant_id=self._merchant_ids[0] if t_type == "PURCHASE" else None,
                    device_id=novel_dev,
                    location_id=remote_loc,
                    occurred_at=step_time,
                    amount=amt,
                    currency="INR",
                    transaction_type=t_type,
                    direction="DEBIT",
                    category=cat,
                    payment_method="NET_BANKING" if cp else "DEBIT_CARD",
                    channel="WEB_PORTAL",
                )
                gt = GeneratedGroundTruth(
                    transaction_id="",
                    is_fraud=True,
                    fraud_scenario="F006",
                    scenario_instance_id=scenario_id,
                    anomaly_notes=f"Account takeover sequence step {step_idx + 1}/4",
                )
                txns.append(txn)
                gts.append(gt)

        elif scenario == "F007":
            # Behavioral Spending Shift: rapid pivot to luxury/electronics across multiple transactions
            shift_time = base_time
            for step in range(3):
                step_time = shift_time + timedelta(hours=step * 4)
                txn = GeneratedTransaction(
                    transaction_id="",
                    source_namespace=self.config.source_namespace,
                    account_id=account.account_id,
                    counterparty_account_id=None,
                    merchant_id=self._merchant_ids[step % len(self._merchant_ids)],
                    device_id=acc_devices[0],
                    location_id=home_loc,
                    occurred_at=step_time,
                    amount=Decimal(f"{profile.max_amount * 2.5:.2f}"),
                    currency="INR",
                    transaction_type="PURCHASE",
                    direction="DEBIT",
                    category="ELECTRONICS",
                    payment_method="CREDIT_CARD",
                    channel="WEB_PORTAL",
                )
                gt = GeneratedGroundTruth(
                    transaction_id="",
                    is_fraud=True,
                    fraud_scenario="F007",
                    scenario_instance_id=scenario_id,
                    anomaly_notes=f"Category and spending volume shift step {step + 1}/3",
                )
                txns.append(txn)
                gts.append(gt)

        return txns, gts
