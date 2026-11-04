"""Deterministic chronological partitioning respecting timestamp group boundaries."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from finsignal.ml.exceptions import MLDomainError
from finsignal.ml.schemas import TemporalSplitResult


class ChronologicalSplitter:
    """Partitions chronological datasets into train, validation, and test subsets.

    Invariants:
    1. Deterministic: identical records produce identical partitions.
    2. Zero leakage: no timestamp group is ever split across partitions.
    3. Strict temporal ordering: max(train.occurred_at) < min(val.occurred_at) <= max(val.occurred_at) < min(test.occurred_at).
    """

    def __init__(
        self,
        train_ratio: float = 0.60,
        val_ratio: float = 0.20,
        test_ratio: float = 0.20,
    ) -> None:
        if not abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-6:
            raise MLDomainError(
                f"Split ratios must sum to 1.0; got {train_ratio + val_ratio + test_ratio:.4f}"
            )
        if train_ratio <= 0 or val_ratio <= 0 or test_ratio <= 0:
            raise MLDomainError("All split ratios must be strictly positive.")

        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

    def split(
        self,
        timestamps: Sequence[datetime],
        record_ids: Sequence[Any],
    ) -> tuple[list[int], list[int], list[int], TemporalSplitResult]:
        """Chronologically split indices into train, val, test subsets.

        Parameters:
            timestamps: Sequence of transaction timestamps.
            record_ids: Sequence of record identifiers for deterministic tie-breaking.

        Returns:
            A tuple of (train_indices, val_indices, test_indices, split_metadata).

        Raises:
            MLDomainError: If input is empty, lengths mismatch, or timestamps lack sufficient distinct values.
        """
        n = len(timestamps)
        if n == 0:
            raise MLDomainError("Cannot split empty dataset.")
        if len(record_ids) != n:
            raise MLDomainError(
                f"Length mismatch: {n} timestamps vs {len(record_ids)} record IDs."
            )

        # 1. Deterministic sort key: (occurred_at, tie_breaker) supporting ints and UUIDs
        def _tie_key(rid: Any) -> tuple[int, Any]:
            if isinstance(rid, int):
                return (0, rid)
            return (1, str(rid))

        indexed_records = [
            (i, timestamps[i], _tie_key(record_ids[i])) for i in range(n)
        ]
        indexed_records.sort(key=lambda x: (x[1], x[2]))

        # 2. Group sorted indices by timestamp
        groups: list[tuple[datetime, list[int]]] = []
        current_ts: datetime | None = None
        current_indices: list[int] = []

        for idx, ts, _ in indexed_records:
            if current_ts is None:
                current_ts = ts
                current_indices = [idx]
            elif ts == current_ts:
                current_indices.append(idx)
            else:
                groups.append((current_ts, current_indices))
                current_ts = ts
                current_indices = [idx]

        if current_ts is not None and current_indices:
            groups.append((current_ts, current_indices))

        num_groups = len(groups)
        if num_groups < 3:
            raise MLDomainError(
                f"Chronological 3-way split requires at least 3 distinct timestamps; found {num_groups}."
            )

        # 3. Determine boundary cuts by timestamp group
        target_train_count = int(round(n * self.train_ratio))
        target_val_count = int(round(n * self.val_ratio))

        train_indices: list[int] = []
        val_indices: list[int] = []
        test_indices: list[int] = []

        group_idx = 0
        current_train_count = 0

        # Train partition: accumulate groups while keeping at least 2 groups remaining for val and test
        while group_idx < num_groups - 2:
            group_size = len(groups[group_idx][1])
            # If train is empty, always take the first group
            if not train_indices:
                train_indices.extend(groups[group_idx][1])
                current_train_count += group_size
                group_idx += 1
                continue

            # Check if adding this group stays closer or within target
            if current_train_count + group_size <= target_train_count:
                train_indices.extend(groups[group_idx][1])
                current_train_count += group_size
                group_idx += 1
            else:
                # Target reached or exceeded; stop train partition
                break

        # Val partition: accumulate groups while keeping at least 1 group remaining for test
        current_val_count = 0
        while group_idx < num_groups - 1:
            group_size = len(groups[group_idx][1])
            if not val_indices:
                val_indices.extend(groups[group_idx][1])
                current_val_count += group_size
                group_idx += 1
                continue

            if current_val_count + group_size <= target_val_count:
                val_indices.extend(groups[group_idx][1])
                current_val_count += group_size
                group_idx += 1
            else:
                break

        # Test partition: all remaining groups
        while group_idx < num_groups:
            test_indices.extend(groups[group_idx][1])
            group_idx += 1

        # 4. Invariant assertion
        train_ts = [timestamps[i] for i in train_indices]
        val_ts = [timestamps[i] for i in val_indices]
        test_ts = [timestamps[i] for i in test_indices]

        max_train = max(train_ts)
        min_val = min(val_ts)
        max_val = max(val_ts)
        min_test = min(test_ts)

        if not (max_train < min_val <= max_val < min_test):
            raise MLDomainError(
                f"Temporal leak detected: max_train={max_train.isoformat()} "
                f"vs min_val={min_val.isoformat()} vs min_test={min_test.isoformat()}"
            )

        metadata = TemporalSplitResult(
            total_records=n,
            train_count=len(train_indices),
            val_count=len(val_indices),
            test_count=len(test_indices),
            train_ratio=len(train_indices) / n,
            val_ratio=len(val_indices) / n,
            test_ratio=len(test_indices) / n,
            train_start=min(train_ts),
            train_end=max_train,
            val_start=min_val,
            val_end=max_val,
            test_start=min_test,
            test_end=max(test_ts),
            unique_timestamps=num_groups,
        )

        return train_indices, val_indices, test_indices, metadata
