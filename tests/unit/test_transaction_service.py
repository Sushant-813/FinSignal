"""Unit tests for TransactionService and DatasetImportService.list_imports (Phase F0.2)."""

import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from finsignal.common.exceptions import NotFoundError, ValidationError
from finsignal.dataset.repository import DatasetImportRepository
from finsignal.dataset.service import DatasetImportService
from finsignal.transactions.repository import TransactionRepository
from finsignal.transactions.service import TransactionService


@pytest.mark.asyncio
async def test_transaction_service_namespace_validation() -> None:
    """Verify namespace regex and existence validation."""
    repo = AsyncMock(spec=TransactionRepository)
    service = TransactionService(repo=repo)
    session = AsyncMock()

    with pytest.raises(ValidationError) as exc:
        await service.list_transactions(session, source_namespace="bad-ns")
    assert exc.value.code == "INVALID_NAMESPACE_FORMAT"
    assert exc.value.status_code == 422

    repo.verify_namespace_exists.return_value = False
    with pytest.raises(NotFoundError) as nf_exc:
        await service.list_transactions(session, source_namespace="MISSING_NS")
    assert nf_exc.value.code == "NAMESPACE_NOT_FOUND"
    assert nf_exc.value.status_code == 404


@pytest.mark.asyncio
async def test_transaction_service_timestamp_validation_and_utc_normalization() -> None:
    """Verify naive datetimes are rejected and aware datetimes normalize to UTC."""
    repo = AsyncMock(spec=TransactionRepository)
    repo.verify_namespace_exists.return_value = True
    repo.list_transactions.return_value = ([], 0, 0)
    service = TransactionService(repo=repo)
    session = AsyncMock()

    # Naive from_time -> 422 INVALID_TIMEZONE
    with pytest.raises(ValidationError) as exc_naive:
        await service.list_transactions(
            session,
            from_time=datetime(2026, 9, 1, 0, 0, 0),
        )
    assert exc_naive.value.code == "INVALID_TIMEZONE"

    # Naive to_time -> 422 INVALID_TIMEZONE
    with pytest.raises(ValidationError) as exc_naive_to:
        await service.list_transactions(
            session,
            to_time=datetime(2026, 9, 2, 0, 0, 0),
        )
    assert exc_naive_to.value.code == "INVALID_TIMEZONE"

    # Inverted range -> 422 INVALID_DATE_RANGE
    t0 = datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError) as exc_inv:
        await service.list_transactions(session, from_time=t0, to_time=t1)
    assert exc_inv.value.code == "INVALID_DATE_RANGE"

    # Equal boundaries -> 422 INVALID_DATE_RANGE
    with pytest.raises(ValidationError) as exc_eq:
        await service.list_transactions(session, from_time=t0, to_time=t0)
    assert exc_eq.value.code == "INVALID_DATE_RANGE"

    # Non-UTC timezone-aware normalized to UTC before repository call
    ist = timezone(timedelta(hours=5, minutes=30))
    from_ist = datetime(2026, 9, 1, 5, 30, 0, tzinfo=ist)  # 2026-09-01T00:00:00Z
    to_ist = datetime(2026, 9, 2, 5, 30, 0, tzinfo=ist)  # 2026-09-02T00:00:00Z
    await service.list_transactions(session, from_time=from_ist, to_time=to_ist)

    kwargs = repo.list_transactions.call_args.kwargs
    assert kwargs["from_time"] == datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    assert kwargs["to_time"] == datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_transaction_service_amount_and_sort_validation() -> None:
    """Verify semantic amount bounds and sort whitelist validation."""
    repo = AsyncMock(spec=TransactionRepository)
    repo.verify_namespace_exists.return_value = True
    repo.list_transactions.return_value = ([], 0, 0)
    service = TransactionService(repo=repo)
    session = AsyncMock()

    # Non-finite Decimal
    with pytest.raises(ValidationError) as exc_nan:
        await service.list_transactions(session, min_amount=Decimal("NaN"))
    assert exc_nan.value.code == "INVALID_AMOUNT_RANGE"

    # Below 0.01
    with pytest.raises(ValidationError) as exc_zero:
        await service.list_transactions(session, min_amount=Decimal("0.00"))
    assert exc_zero.value.code == "INVALID_AMOUNT_RANGE"

    # min > max
    with pytest.raises(ValidationError) as exc_gt:
        await service.list_transactions(
            session,
            min_amount=Decimal("500.00"),
            max_amount=Decimal("100.00"),
        )
    assert exc_gt.value.code == "INVALID_AMOUNT_RANGE"

    # Unsupported sort_by
    with pytest.raises(ValidationError) as exc_sort:
        await service.list_transactions(session, sort_by="currency")
    assert exc_sort.value.code == "UNSUPPORTED_SORT_FIELD"

    # Invalid sort_order
    with pytest.raises(ValidationError) as exc_ord:
        await service.list_transactions(session, sort_order="sideways")
    assert exc_ord.value.code == "INVALID_SORT_ORDER"

    # Case-insensitive sort_order normalized
    await service.list_transactions(session, sort_by="amount", sort_order="ASC")
    assert repo.list_transactions.call_args.kwargs["sort_order"] == "asc"


@pytest.mark.asyncio
async def test_transaction_service_detail_validation_and_not_found() -> None:
    """Verify detail endpoint validates optional namespace and emits TRANSACTION_NOT_FOUND."""
    repo = AsyncMock(spec=TransactionRepository)
    service = TransactionService(repo=repo)
    session = AsyncMock()
    tx_id = uuid.uuid4()

    with pytest.raises(ValidationError) as exc_ns:
        await service.get_transaction_detail(
            session, tx_id, source_namespace="invalid-ns"
        )
    assert exc_ns.value.code == "INVALID_NAMESPACE_FORMAT"

    repo.get_transaction_detail.return_value = None
    with pytest.raises(NotFoundError) as exc_nf:
        await service.get_transaction_detail(
            session, tx_id, source_namespace="SYNTHETIC"
        )
    assert exc_nf.value.code == "TRANSACTION_NOT_FOUND"
    assert exc_nf.value.status_code == 404


@pytest.mark.asyncio
async def test_dataset_import_service_list_validation() -> None:
    """Verify DatasetImportService.list_imports enforces namespace, timezone, date range, and status."""
    import_repo = AsyncMock(spec=DatasetImportRepository)
    import_repo.verify_namespace_exists.return_value = True
    import_repo.list_imports.return_value = ([], 0, 0)
    service = DatasetImportService(import_repo=import_repo)
    session = AsyncMock()

    with pytest.raises(ValidationError) as exc_ns:
        await service.list_imports(session, source_namespace="bad")
    assert exc_ns.value.code == "INVALID_NAMESPACE_FORMAT"

    with pytest.raises(ValidationError) as exc_tz:
        await service.list_imports(session, from_time=datetime(2026, 10, 1, 0, 0, 0))
    assert exc_tz.value.code == "INVALID_TIMEZONE"

    with pytest.raises(ValidationError) as exc_rng:
        t0 = datetime(2026, 10, 2, 0, 0, 0, tzinfo=UTC)
        t1 = datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC)
        await service.list_imports(session, from_time=t0, to_time=t1)
    assert exc_rng.value.code == "INVALID_DATE_RANGE"

    with pytest.raises(ValidationError) as exc_st:
        await service.list_imports(session, status="UNKNOWN")
    assert exc_st.value.code == "INVALID_IMPORT_STATUS"

    import_repo.verify_namespace_exists.return_value = False
    with pytest.raises(NotFoundError) as exc_nf:
        await service.list_imports(session, source_namespace="GHOST_NS")
    assert exc_nf.value.code == "NAMESPACE_NOT_FOUND"
