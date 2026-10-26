"""Unit tests for chronological dataset splitting with timestamp group preservation."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from finsignal.ml.exceptions import MLDomainError
from finsignal.ml.split import ChronologicalSplitter


def test_chronological_splitter_basic() -> None:
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    # 10 distinct timestamps, 1 record each
    timestamps = [base_time + timedelta(hours=i) for i in range(10)]
    record_ids = [uuid.uuid4() for _ in range(10)]

    splitter = ChronologicalSplitter(train_ratio=0.60, val_ratio=0.20, test_ratio=0.20)
    train_idx, val_idx, test_idx, meta = splitter.split(timestamps, record_ids)

    assert meta.total_records == 10
    assert meta.train_count == 6
    assert meta.val_count == 2
    assert meta.test_count == 2
    assert len(train_idx) == 6
    assert len(val_idx) == 2
    assert len(test_idx) == 2

    # Check temporal strictness
    max_train = max(timestamps[i] for i in train_idx)
    min_val = min(timestamps[i] for i in val_idx)
    max_val = max(timestamps[i] for i in val_idx)
    min_test = min(timestamps[i] for i in test_idx)

    assert max_train < min_val
    assert max_val < min_test


def test_chronological_splitter_never_splits_identical_timestamps() -> None:
    """TG-03: Identical timestamps must not be partitioned across subsets."""
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    t1 = base_time
    t2 = base_time + timedelta(hours=1)
    t3 = base_time + timedelta(hours=2)

    # 4 records at t1, 4 records at t2, 4 records at t3 -> total 12 records, 3 unique timestamps
    timestamps = [t1] * 4 + [t2] * 4 + [t3] * 4
    record_ids = [uuid.uuid4() for _ in range(12)]

    splitter = ChronologicalSplitter(train_ratio=0.60, val_ratio=0.20, test_ratio=0.20)
    train_idx, val_idx, test_idx, meta = splitter.split(timestamps, record_ids)

    train_ts = {timestamps[i] for i in train_idx}
    val_ts = {timestamps[i] for i in val_idx}
    test_ts = {timestamps[i] for i in test_idx}

    # Intersections must be completely empty
    assert len(train_ts.intersection(val_ts)) == 0
    assert len(val_ts.intersection(test_ts)) == 0
    assert len(train_ts.intersection(test_ts)) == 0

    assert meta.unique_timestamps == 3
    assert len(train_idx) + len(val_idx) + len(test_idx) == 12


def test_chronological_splitter_deterministic_ordering() -> None:
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    timestamps = [base_time + timedelta(minutes=i % 5) for i in range(20)]
    record_ids = [uuid.uuid4() for _ in range(20)]

    splitter = ChronologicalSplitter()
    t1, v1, s1, _ = splitter.split(timestamps, record_ids)
    t2, v2, s2, _ = splitter.split(timestamps, record_ids)

    assert t1 == t2
    assert v1 == v2
    assert s1 == s2


def test_chronological_splitter_insufficient_timestamps() -> None:
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    # Only 2 distinct timestamps
    timestamps = [base_time, base_time, base_time + timedelta(hours=1)]
    record_ids = [uuid.uuid4() for _ in range(3)]

    splitter = ChronologicalSplitter()
    with pytest.raises(MLDomainError, match="requires at least 3 distinct timestamps"):
        splitter.split(timestamps, record_ids)


def test_chronological_splitter_empty_input() -> None:
    splitter = ChronologicalSplitter()
    with pytest.raises(MLDomainError, match="Cannot split empty"):
        splitter.split([], [])


def test_chronological_splitter_invalid_ratios() -> None:
    with pytest.raises(MLDomainError, match="must sum to 1.0"):
        ChronologicalSplitter(train_ratio=0.5, val_ratio=0.2, test_ratio=0.2)
