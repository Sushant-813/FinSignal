"""Unit tests for LoginRateLimiter (SEC-06)."""

from unittest.mock import patch

from finsignal.auth.limiter import LoginRateLimiter


def test_rate_limiter_allows_under_threshold() -> None:
    """Verify that failed attempts under threshold remain allowed."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    r1 = limiter.record_failure(key)
    assert r1.allowed is True
    assert r1.remaining_attempts == 2

    r2 = limiter.record_failure(key)
    assert r2.allowed is True
    assert r2.remaining_attempts == 1

    check = limiter.check(key)
    assert check.allowed is True
    assert check.remaining_attempts == 1


def test_rate_limiter_blocks_at_threshold() -> None:
    """Verify that reaching threshold blocks subsequent attempts."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    limiter.record_failure(key)
    limiter.record_failure(key)
    r3 = limiter.record_failure(key)

    assert r3.allowed is False
    assert r3.remaining_attempts == 0
    assert r3.retry_after > 0

    check = limiter.check(key)
    assert check.allowed is False
    assert check.retry_after > 0


def test_rate_limiter_sliding_window_expiration() -> None:
    """Verify that attempts expire after window_seconds has passed."""
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=10)
    key = "127.0.0.1:user@example.com"

    with patch("time.monotonic", return_value=100.0):
        limiter.record_failure(key)
        limiter.record_failure(key)
        assert limiter.check(key).allowed is False

    # After 11 seconds (monotonic = 111.0), previous attempts have expired
    with patch("time.monotonic", return_value=111.0):
        check = limiter.check(key)
        assert check.allowed is True
        assert check.remaining_attempts == 2


def test_rate_limiter_success_clears_failures() -> None:
    """Verify that successful authentication resets failed attempt counter."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    limiter.record_failure(key)
    limiter.record_failure(key)
    assert limiter.check(key).remaining_attempts == 1

    limiter.record_success(key)
    assert limiter.check(key).remaining_attempts == 3


def test_rate_limiter_capacity_eviction() -> None:
    """Verify that exceeding max_tracked_keys evicts oldest key to prevent unbounded growth."""
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=60, max_tracked_keys=3)

    limiter.record_failure("key1")
    limiter.record_failure("key2")
    limiter.record_failure("key3")
    assert len(limiter._records) == 3

    # Adding a 4th key triggers eviction of the oldest key
    limiter.record_failure("key4")
    assert len(limiter._records) <= 3
    assert "key1" not in limiter._records
    assert "key4" in limiter._records


def test_concurrent_admission_blocks_excess_requests() -> None:
    """Verify SEC-06: acquire() bounds in-flight attempts, blocking excess concurrent requests."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    # Acquire 3 attempts concurrently
    r1 = limiter.acquire(key)
    assert r1.allowed is True
    assert r1.remaining_attempts == 2

    r2 = limiter.acquire(key)
    assert r2.allowed is True
    assert r2.remaining_attempts == 1

    r3 = limiter.acquire(key)
    assert r3.allowed is True
    assert r3.remaining_attempts == 0

    # 4th concurrent request must be rejected immediately (retry_after=1 while in-flight)
    r4 = limiter.acquire(key)
    assert r4.allowed is False
    assert r4.remaining_attempts == 0
    assert r4.retry_after == 1


def test_reservation_cleanup_on_unexpected_error() -> None:
    """Verify SEC-06: release_reservation() frees in-flight slots on unexpected exceptions without penalty."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    # Acquire slot
    res = limiter.acquire(key)
    assert res.allowed is True
    assert res.remaining_attempts == 2

    # Unexpected exception occurs -> release reservation
    limiter.release_reservation(key)

    # All 3 attempts should be available again
    check = limiter.check(key)
    assert check.allowed is True
    assert check.remaining_attempts == 3


def test_failed_authentication_transitions_reservation_to_failure() -> None:
    """Verify SEC-06: record_failure() converts an in-flight reservation into a recorded failure."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    # 1. In-flight acquisition
    limiter.acquire(key)
    rec = limiter._records[key]
    assert rec.in_flight == 1
    assert len(rec.timestamps) == 0

    # 2. Authentication fails -> record failure
    limiter.record_failure(key)
    assert rec.in_flight == 0
    assert len(rec.timestamps) == 1

    # Key now has 1 recorded failure and 2 remaining attempts
    check = limiter.check(key)
    assert check.allowed is True
    assert check.remaining_attempts == 2


def test_successful_authentication_clears_reservation_and_failures() -> None:
    """Verify SEC-06: record_success() releases reservation and wipes previous failures."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    # 2 previous failures
    limiter.record_failure(key)
    limiter.record_failure(key)
    assert limiter.check(key).remaining_attempts == 1

    # 3rd attempt acquires and succeeds
    limiter.acquire(key)
    limiter.record_success(key)

    # State is completely cleared
    assert key not in limiter._records
    check = limiter.check(key)
    assert check.allowed is True
    assert check.remaining_attempts == 3


def test_concurrent_threading_race_condition() -> None:
    """Verify SEC-06: Thread-safe admission ensures exactly max_attempts succeed under race conditions."""
    import concurrent.futures

    limiter = LoginRateLimiter(max_attempts=5, window_seconds=60)
    key = "192.168.1.100:victim@example.com"

    def try_admit() -> bool:
        return limiter.acquire(key).allowed

    # Launch 20 concurrent threads attempting to acquire simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(try_admit) for _ in range(20)]
        results = [f.result() for f in futures]

    admitted_count = sum(1 for r in results if r is True)
    blocked_count = sum(1 for r in results if r is False)

    assert admitted_count == 5, (
        f"Expected exactly 5 admitted attempts, got {admitted_count}"
    )
    assert blocked_count == 15, (
        f"Expected exactly 15 blocked attempts, got {blocked_count}"
    )


def test_capacity_reached_with_all_records_active_rejects_new_key() -> None:
    """Verify SEC-06: New keys are rejected when capacity is full and all tracked records are active."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, max_tracked_keys=2)

    # 1. Fill capacity with active in-flight keys
    r1 = limiter.acquire("active_key_1")
    assert r1.allowed is True
    assert limiter._records["active_key_1"].in_flight == 1

    r2 = limiter.acquire("active_key_2")
    assert r2.allowed is True
    assert limiter._records["active_key_2"].in_flight == 1

    # 2. Attempt admission for a 3rd key when all records are active
    r3 = limiter.acquire("active_key_3")
    assert r3.allowed is False
    assert r3.retry_after == 1
    assert "active_key_3" not in limiter._records

    # 3. Confirm active keys were NEVER evicted
    assert "active_key_1" in limiter._records
    assert limiter._records["active_key_1"].in_flight == 1
    assert "active_key_2" in limiter._records
    assert limiter._records["active_key_2"].in_flight == 1


def test_capacity_pressure_admits_existing_active_key() -> None:
    """Verify SEC-06: Capacity pressure cannot reset an existing key's attempt history or block its valid attempts."""
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=60, max_tracked_keys=2)

    # Fill capacity
    limiter.acquire("active_key_1")  # in_flight = 1
    limiter.acquire("active_key_2")  # in_flight = 1
    assert len(limiter._records) == 2

    # Existing active key 1 acquires a second attempt
    r1_second = limiter.acquire("active_key_1")
    assert r1_second.allowed is True
    assert r1_second.remaining_attempts == 3
    assert limiter._records["active_key_1"].in_flight == 2

    # History and active records remain intact
    assert len(limiter._records) == 2
    assert "active_key_1" in limiter._records
    assert "active_key_2" in limiter._records


def test_capacity_eviction_strictly_targets_idle_keys() -> None:
    """Verify SEC-06: Capacity eviction targets only idle records (in_flight == 0) and preserves active keys."""
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=60, max_tracked_keys=2)

    # active_key_1 has in_flight == 1
    limiter.acquire("active_key_1")
    # idle_key_2 has in_flight == 0 (recorded failure)
    limiter.record_failure("idle_key_2")
    assert limiter._records["idle_key_2"].in_flight == 0

    # Key 3 arrives -> idle_key_2 must be evicted; active_key_1 must be preserved
    r3 = limiter.acquire("key_3")
    assert r3.allowed is True
    assert "active_key_1" in limiter._records
    assert limiter._records["active_key_1"].in_flight == 1
    assert "idle_key_2" not in limiter._records
    assert "key_3" in limiter._records


def test_no_negative_in_flight_count_under_double_release() -> None:
    """Verify SEC-06: In-flight reservation counts never become negative even under duplicate release calls."""
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60)
    key = "127.0.0.1:user@example.com"

    limiter.acquire(key)
    rec = limiter._records[key]
    assert rec.in_flight == 1

    # First release
    limiter.release_reservation(key)
    # Key purged because both in_flight == 0 and timestamps is empty
    assert key not in limiter._records

    # Duplicate release on non-existent or zeroed key must not raise or corrupt state
    limiter.release_reservation(key)
    limiter.record_success(key)

    # Next acquire works cleanly
    r_next = limiter.acquire(key)
    assert r_next.allowed is True
    assert limiter._records[key].in_flight == 1
