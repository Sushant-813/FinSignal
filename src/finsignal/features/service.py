"""Service orchestrator for Phase 6 single-transaction and batch feature extraction.

Enforces:
- Online evaluation: uses repository and pure engine with strict event boundaries.
- Batch evaluation: in-memory chronological stream using dual-heaps and sliding deques,
  achieving O(N log N) dataset complexity with zero database queries during extraction.
- Determinism and equivalence: identical event-ordering and even-median conventions
  as the online database path.
"""

import heapq
import math
import uuid
from collections import Counter, deque
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.features.constants import (
    CATEGORY_WINDOW_30D_SECONDS,
)
from finsignal.features.engine import build_feature_metadata, compute_feature_vector
from finsignal.features.repository import FeatureRepository
from finsignal.features.schemas import (
    AccountProfileDTO,
    EvaluatedTransactionDTO,
    EvaluationContext,
    FeatureEvaluationResult,
    HistoricalTransactionDTO,
    LifetimeBaselineSummary,
)


def _to_utc(dt: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC datetime."""
    if dt.tzinfo is UTC:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class DirectionCurrencyRunningStats:
    """Maintains incremental running mean, sample variance (Welford's), and exact running median (dual heaps)."""

    def __init__(self) -> None:
        self.count: int = 0
        self.mean: Decimal = Decimal(0)
        self.m2: Decimal = Decimal(0)
        # Dual heaps for exact median:
        # lower_heap: max-heap storing negative values (using Decimal for exact monetary values)
        # upper_heap: min-heap storing positive values
        self.lower_heap: list[Decimal] = []
        self.upper_heap: list[Decimal] = []

    def add(self, amount: Decimal) -> None:
        """Add an observation using Welford's algorithm and dual heaps."""
        self.count += 1
        delta = amount - self.mean
        self.mean += delta / Decimal(self.count)
        delta2 = amount - self.mean
        self.m2 += delta * delta2

        # Dual heaps update for exact running median
        if not self.lower_heap or amount <= -self.lower_heap[0]:
            heapq.heappush(self.lower_heap, -amount)
        else:
            heapq.heappush(self.upper_heap, amount)

        # Balance heaps: len(lower) == len(upper) or len(lower) == len(upper) + 1
        if len(self.lower_heap) > len(self.upper_heap) + 1:
            val = -heapq.heappop(self.lower_heap)
            heapq.heappush(self.upper_heap, val)
        elif len(self.upper_heap) > len(self.lower_heap):
            val = heapq.heappop(self.upper_heap)
            heapq.heappush(self.lower_heap, -val)

    @property
    def sample_stddev(self) -> float | None:
        """Return sample standard deviation (N - 1 denominator)."""
        if self.count < 2:
            return None
        var_dec = self.m2 / Decimal(self.count - 1)
        return math.sqrt(float(var_dec))

    @property
    def median(self) -> Decimal | None:
        """Return exact median. For even count, returns arithmetic mean of the two central values."""
        if self.count == 0:
            return None
        if len(self.lower_heap) > len(self.upper_heap):
            return -self.lower_heap[0]
        # Even count: arithmetic mean of top of lower and top of upper
        return (-self.lower_heap[0] + self.upper_heap[0]) / Decimal(2)


class AccountChronologicalAccumulator:
    """Manages sliding deques, Welford statistics, and entity familiarity for a single account."""

    def __init__(self, account_profile: AccountProfileDTO) -> None:
        self.account_profile = account_profile
        # Sliding deques of HistoricalTransactionDTO
        self.history_30d: deque[HistoricalTransactionDTO] = deque()

        # Direction- and currency-matched running statistics: (currency, direction) -> RunningStats
        self.stats: dict[tuple[str, str], DirectionCurrencyRunningStats] = {}

        # Entity familiarity counters across lifetime
        self.device_counts: Counter[uuid.UUID] = Counter()
        self.merchant_counts: Counter[uuid.UUID] = Counter()
        self.location_counts: Counter[uuid.UUID] = Counter()
        self.seen_categories: set[str] = set()
        self.total_lifetime_count: int = 0

    def evict_sliding_windows(self, current_time: datetime) -> None:
        """Evict records older than 30 days from the sliding deque."""
        t_30d = current_time - timedelta(seconds=CATEGORY_WINDOW_30D_SECONDS)
        while self.history_30d and _to_utc(self.history_30d[0].occurred_at) < t_30d:
            self.history_30d.popleft()

    def get_lifetime_summary(
        self, currency: str, direction: str
    ) -> LifetimeBaselineSummary:
        """Assemble current lifetime baseline summary for given currency and direction."""
        stat = self.stats.get((currency, direction))
        if stat is None or stat.count == 0:
            count = 0
            mean = None
            stddev = None
            median = None
        else:
            count = stat.count
            mean = stat.mean
            stddev = stat.sample_stddev
            median = stat.median

        return LifetimeBaselineSummary(
            count=count,
            mean=mean,
            stddev=stddev,
            median=median,
            total_lifetime_count=self.total_lifetime_count,
            seen_devices=frozenset(self.device_counts.keys()),
            seen_merchants=frozenset(self.merchant_counts.keys()),
            seen_locations=frozenset(self.location_counts.keys()),
            seen_categories=frozenset(self.seen_categories),
            device_tx_counts=dict(self.device_counts),
            merchant_tx_counts=dict(self.merchant_counts),
            location_tx_counts=dict(self.location_counts),
        )

    def add(self, tx: HistoricalTransactionDTO) -> None:
        """Incorporate an evaluated transaction into historical state."""
        self.history_30d.append(tx)
        self.total_lifetime_count += 1

        key = (tx.currency, tx.direction)
        if key not in self.stats:
            self.stats[key] = DirectionCurrencyRunningStats()
        self.stats[key].add(tx.amount)

        if tx.device_id is not None:
            self.device_counts[tx.device_id] += 1
        if tx.merchant_id is not None:
            self.merchant_counts[tx.merchant_id] += 1
        if tx.location_id is not None:
            self.location_counts[tx.location_id] += 1
        if tx.category is not None:
            self.seen_categories.add(tx.category)


class FeatureService:
    """Domain service orchestrating point-in-time single evaluation and chronological batch extraction."""

    def __init__(self, repository: FeatureRepository | None = None) -> None:
        self.repository = repository or FeatureRepository()

    async def evaluate_transaction(
        self, session: AsyncSession, transaction_id: uuid.UUID
    ) -> FeatureEvaluationResult:
        """Perform on-demand point-in-time feature extraction for a single transaction."""
        context = await self.repository.assemble_evaluation_context(
            session, transaction_id
        )
        vector = compute_feature_vector(context)
        metadata = build_feature_metadata(context)
        return FeatureEvaluationResult(features=vector, metadata=metadata)

    def extract_batch(
        self,
        transactions: Sequence[Any],
        accounts_map: Mapping[uuid.UUID, AccountProfileDTO],
    ) -> list[FeatureEvaluationResult]:
        """Extract features chronologically across a batch in O(N log N) time without database queries.

        Guarantees:
        - Does not mutate input collection.
        - Sorts a copy by (account_id, occurred_at ASC, id ASC).
        - Independent state per account.
        - Evaluated transaction strictly excluded from its own baseline.
        """
        # Convert input objects to EvaluatedTransactionDTO if needed
        converted: list[tuple[int, EvaluatedTransactionDTO]] = []
        for idx, item in enumerate(transactions):
            if isinstance(item, EvaluatedTransactionDTO):
                tx_dto = item
            elif hasattr(item, "id") and hasattr(item, "account_id"):
                occ = _to_utc(item.occurred_at)
                tx_dto = EvaluatedTransactionDTO(
                    id=item.id,
                    account_id=item.account_id,
                    occurred_at=occ,
                    amount=item.amount,
                    currency=item.currency,
                    direction=item.direction,
                    transaction_type=getattr(item, "transaction_type", "PURCHASE"),
                    source_namespace=getattr(item, "source_namespace", "SYNTHETIC"),
                    merchant_id=getattr(item, "merchant_id", None),
                    device_id=getattr(item, "device_id", None),
                    location_id=getattr(item, "location_id", None),
                    category=getattr(item, "category", None),
                )
            else:
                msg = f"Unsupported transaction object type in batch extraction: {type(item)}"
                raise TypeError(msg)
            converted.append((idx, tx_dto))

        # Sort chronologically by (account_id, occurred_at ASC, id ASC)
        # Using id.int to guarantee exact parity with PostgreSQL B-tree UUID comparison
        chronological = sorted(
            converted,
            key=lambda item: (
                item[1].account_id.int,
                _to_utc(item[1].occurred_at),
                item[1].id.int,
            ),
        )

        accumulators: dict[uuid.UUID, AccountChronologicalAccumulator] = {}
        results_with_orig_idx: list[tuple[int, FeatureEvaluationResult]] = []

        for orig_idx, eval_tx in chronological:
            account_id = eval_tx.account_id
            if account_id not in accumulators:
                profile = accounts_map.get(account_id)
                if profile is None:
                    msg = f"AccountProfileDTO missing for account_id '{account_id}'"
                    raise ValueError(msg)
                accumulators[account_id] = AccountChronologicalAccumulator(profile)

            acc = accumulators[account_id]
            eval_t = _to_utc(eval_tx.occurred_at)
            acc.evict_sliding_windows(eval_t)

            # 1. Assemble EvaluationContext BEFORE adding eval_tx to history
            lifetime_summary = acc.get_lifetime_summary(
                currency=eval_tx.currency, direction=eval_tx.direction
            )
            # Pass a snapshot copy of current 30d sliding history
            bounded_snapshot = list(acc.history_30d)

            ctx = EvaluationContext(
                evaluated_transaction=eval_tx,
                account_profile=acc.account_profile,
                bounded_transactions=bounded_snapshot,
                lifetime_summary=lifetime_summary,
            )

            # 2. Compute features
            vector = compute_feature_vector(ctx)
            metadata = build_feature_metadata(ctx)
            result = FeatureEvaluationResult(features=vector, metadata=metadata)
            results_with_orig_idx.append((orig_idx, result))

            # 3. Incorporate eval_tx into historical accumulator
            hist_item = HistoricalTransactionDTO(
                id=eval_tx.id,
                occurred_at=eval_tx.occurred_at,
                amount=eval_tx.amount,
                currency=eval_tx.currency,
                direction=eval_tx.direction,
                transaction_type=eval_tx.transaction_type,
                merchant_id=eval_tx.merchant_id,
                device_id=eval_tx.device_id,
                location_id=eval_tx.location_id,
                category=eval_tx.category,
            )
            acc.add(hist_item)

        # Re-sort to preserve caller's original transaction input ordering
        results_with_orig_idx.sort(key=lambda x: x[0])
        return [r for _, r in results_with_orig_idx]
