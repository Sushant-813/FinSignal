"""In-memory sliding-window rate limiter for authentication endpoints (SEC-06)."""

import threading
import time
from collections import deque
from typing import NamedTuple


class RateLimitResult(NamedTuple):
    """Result of rate limit inspection or recording."""

    allowed: bool
    retry_after: int
    remaining_attempts: int


class _KeyRecord:
    """Internal state tracked for a specific rate limit key."""

    __slots__ = ("timestamps", "in_flight")

    def __init__(self) -> None:
        self.timestamps: deque[float] = deque()
        self.in_flight: int = 0


class LoginRateLimiter:
    """Thread-safe, bounded in-memory sliding-window rate limiter with concurrent admission control.

    Defends against both serial brute-force attacks and concurrent request bursts.
    In-flight verification attempts are reserved upon admission and released or converted to
    failures once Argon2id authentication completes, preventing check-then-record race conditions.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 60,
        max_tracked_keys: int = 10000,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.max_tracked_keys = max_tracked_keys
        self._lock = threading.Lock()
        self._records: dict[str, _KeyRecord] = {}

    def _purge_expired(self, key: str, now: float) -> _KeyRecord | None:
        """Remove timestamps older than window_seconds for the given key."""
        cutoff = now - self.window_seconds
        record = self._records.get(key)
        if record is None:
            return None
        while record.timestamps and record.timestamps[0] <= cutoff:
            record.timestamps.popleft()
        if not record.timestamps and record.in_flight == 0:
            del self._records[key]
            return None
        return record

    def check(self, key: str) -> RateLimitResult:
        """Check whether the key is currently rate-limited without reserving an attempt."""
        now = time.monotonic()
        with self._lock:
            record = self._purge_expired(key, now)
            if record is None:
                return RateLimitResult(
                    allowed=True,
                    retry_after=0,
                    remaining_attempts=self.max_attempts,
                )
            total_active = len(record.timestamps) + record.in_flight
            if total_active >= self.max_attempts:
                if record.timestamps:
                    retry_after = max(
                        1, int(self.window_seconds - (now - record.timestamps[0]))
                    )
                else:
                    retry_after = 1
                return RateLimitResult(
                    allowed=False,
                    retry_after=retry_after,
                    remaining_attempts=0,
                )
            remaining = self.max_attempts - total_active
            return RateLimitResult(
                allowed=True,
                retry_after=0,
                remaining_attempts=remaining,
            )

    def acquire(self, key: str) -> RateLimitResult:
        """Atomically test and reserve an in-flight authentication attempt for the key."""
        now = time.monotonic()
        with self._lock:
            record = self._purge_expired(key, now)
            if record is None:
                if len(self._records) >= self.max_tracked_keys:
                    # Evict an idle key (in_flight == 0) first
                    evict_key = next(
                        (k for k, r in self._records.items() if r.in_flight == 0),
                        None,
                    )
                    if evict_key is None:
                        # Capacity reached and all records are active: reject new key
                        return RateLimitResult(
                            allowed=False,
                            retry_after=1,
                            remaining_attempts=0,
                        )
                    del self._records[evict_key]
                record = _KeyRecord()
                self._records[key] = record

            total_active = len(record.timestamps) + record.in_flight
            if total_active >= self.max_attempts:
                if record.timestamps:
                    retry_after = max(
                        1, int(self.window_seconds - (now - record.timestamps[0]))
                    )
                else:
                    retry_after = 1
                return RateLimitResult(
                    allowed=False,
                    retry_after=retry_after,
                    remaining_attempts=0,
                )

            record.in_flight += 1
            remaining = self.max_attempts - (len(record.timestamps) + record.in_flight)
            return RateLimitResult(
                allowed=True,
                retry_after=0,
                remaining_attempts=remaining,
            )

    def record_failure(self, key: str) -> RateLimitResult:
        """Record a failed login attempt, transitioning 1 in-flight reservation to a failed timestamp."""
        now = time.monotonic()
        with self._lock:
            record = self._purge_expired(key, now)
            if record is None:
                if len(self._records) >= self.max_tracked_keys:
                    evict_key = next(
                        (k for k, r in self._records.items() if r.in_flight == 0),
                        None,
                    )
                    if evict_key is None:
                        return RateLimitResult(
                            allowed=False,
                            retry_after=1,
                            remaining_attempts=0,
                        )
                    del self._records[evict_key]
                record = _KeyRecord()
                self._records[key] = record

            if record.in_flight > 0:
                record.in_flight -= 1
            record.timestamps.append(now)

            total_active = len(record.timestamps) + record.in_flight
            if total_active >= self.max_attempts:
                oldest = record.timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                return RateLimitResult(
                    allowed=False,
                    retry_after=retry_after,
                    remaining_attempts=0,
                )
            remaining = self.max_attempts - total_active
            return RateLimitResult(
                allowed=True,
                retry_after=0,
                remaining_attempts=remaining,
            )

    def release_reservation(self, key: str) -> None:
        """Release an in-flight reservation without recording a failure (e.g. on unexpected errors)."""
        with self._lock:
            record = self._records.get(key)
            if record is not None:
                if record.in_flight > 0:
                    record.in_flight -= 1
                if not record.timestamps and record.in_flight == 0:
                    del self._records[key]

    def record_success(self, key: str) -> None:
        """Clear failed attempts and release reservation for key on successful login."""
        with self._lock:
            record = self._records.get(key)
            if record is not None:
                if record.in_flight > 0:
                    record.in_flight -= 1
                record.timestamps.clear()
                if record.in_flight == 0:
                    del self._records[key]

    def reset(self) -> None:
        """Clear all rate limiting state (for testing)."""
        with self._lock:
            self._records.clear()


# Default singleton instance for the application process
default_login_rate_limiter = LoginRateLimiter()


def get_login_rate_limiter() -> LoginRateLimiter:
    """FastAPI dependency provider for the login rate limiter singleton."""
    return default_login_rate_limiter
