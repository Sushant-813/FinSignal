"""PostgreSQL transaction-scoped advisory locking for dataset imports (P4.5, ADR-065)."""

import hashlib
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.common.exceptions import ConflictError

logger = logging.getLogger("finsignal.dataset.ingestion.locking")


def derive_advisory_lock_key(source_namespace: str, file_hash: str) -> int:
    """Derive a deterministic signed 64-bit integer lock key from namespace and file hash.

    PostgreSQL pg_advisory_xact_lock requires a bigint (signed 64-bit integer)
    in the range [-2^63, 2^63 - 1].
    """
    digest = hashlib.sha256(f"{source_namespace}:{file_hash}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


async def acquire_import_advisory_lock(
    session: AsyncSession,
    source_namespace: str,
    file_hash: str,
    timeout_seconds: float = 5.0,
) -> int:
    """Acquire a transaction-scoped PostgreSQL advisory lock for the namespace and file hash.

    Safety & Concurrency Guarantees:
    - Uses pg_advisory_xact_lock: the lock is automatically released by PostgreSQL
      when the enclosing transaction commits or rolls back.
    - Applies a local statement timeout to prevent indefinite blocking under deadlock.
    - Scoped strictly to (source_namespace, file_hash).
    """
    lock_key = derive_advisory_lock_key(source_namespace, file_hash)
    timeout_ms = int(timeout_seconds * 1000)

    # Set local timeout for lock acquisition
    await session.execute(text(f"SET LOCAL lock_timeout = '{timeout_ms}ms';"))
    try:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key);"),
            {"lock_key": lock_key},
        )
    except Exception as e:
        err_msg = str(e).lower()
        if (
            "lock timeout" in err_msg
            or "canceling statement" in err_msg
            or "locknotavailable" in err_msg
        ):
            raise ConflictError(
                message="Timed out acquiring dataset import advisory lock. Another upload may be active.",
                code="LOCK_TIMEOUT",
                details={"source_namespace": source_namespace, "file_hash": file_hash},
            ) from e
        raise

    logger.debug(
        "Acquired transaction advisory lock: key=%d namespace=%s hash=%s",
        lock_key,
        source_namespace,
        file_hash,
    )
    return lock_key
