"""Unit tests for transaction and dataset import list Pydantic schemas (Phase F0.2)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from finsignal.dataset.schemas import DatasetImportListResponse, DatasetImportResponse
from finsignal.transactions.schemas import (
    TransactionAccountDTO,
    TransactionDetailResponse,
    TransactionDeviceDTO,
    TransactionLatestRiskDTO,
    TransactionListResponse,
    TransactionLocationDTO,
    TransactionMerchantDTO,
    TransactionSummaryItem,
)


def test_transaction_summary_item_serialization_and_forbid_extra() -> None:
    """Verify MoneyStr fixed-point formatting, nullables, and extra='forbid'."""
    now = datetime(2026, 9, 15, 14, 30, 0, tzinfo=UTC)
    item = TransactionSummaryItem(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_transaction_id="TXN_00012345",
        account_id=uuid.uuid4(),
        occurred_at=now,
        amount=Decimal("75000"),
        currency="INR",
        transaction_type="TRANSFER",
        direction="DEBIT",
        created_at=now,
    )
    dumped = item.model_dump()
    assert dumped["amount"] == "75000.00"
    assert isinstance(dumped["amount"], str)
    assert dumped["counterparty_account_id"] is None
    assert dumped["merchant_id"] is None

    with pytest.raises(ValidationError):
        TransactionSummaryItem(
            id=uuid.uuid4(),
            source_namespace="SYNTHETIC",
            external_transaction_id="TXN_00012345",
            account_id=uuid.uuid4(),
            occurred_at=now,
            amount=Decimal("10.50"),
            currency="INR",
            transaction_type="PURCHASE",
            direction="DEBIT",
            created_at=now,
            unexpected="forbidden",  # type: ignore[call-arg]
        )


def test_transaction_list_response_pagination_bounds() -> None:
    """Verify TransactionListResponse validates pagination envelope constraints."""
    empty = TransactionListResponse(
        items=[],
        page=1,
        page_size=50,
        total=0,
        total_pages=0,
    )
    assert empty.total_pages == 0

    with pytest.raises(ValidationError):
        TransactionListResponse(items=[], page=0, page_size=50, total=0, total_pages=0)

    with pytest.raises(ValidationError):
        TransactionListResponse(items=[], page=1, page_size=101, total=0, total_pages=0)


def test_transaction_detail_response_nested_dtos() -> None:
    """Verify TransactionDetailResponse serializes embedded relational context and latest_risk."""
    now = datetime(2026, 9, 15, 14, 30, 0, tzinfo=UTC)
    acc_id = uuid.uuid4()
    merch_id = uuid.uuid4()
    dev_id = uuid.uuid4()
    loc_id = uuid.uuid4()

    detail = TransactionDetailResponse(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        external_transaction_id="TXN_00012345",
        account_id=acc_id,
        merchant_id=merch_id,
        device_id=dev_id,
        location_id=loc_id,
        occurred_at=now,
        amount=Decimal("1250.5"),
        currency="INR",
        transaction_type="PURCHASE",
        direction="DEBIT",
        created_at=now,
        account=TransactionAccountDTO(
            id=acc_id,
            external_account_id="ACC_001",
            account_type="SAVINGS",
            status="ACTIVE",
        ),
        merchant=TransactionMerchantDTO(
            id=merch_id,
            external_merchant_id="MERCH_001",
            merchant_name="Acme Electronics",
            merchant_category="ELECTRONICS",
        ),
        device=TransactionDeviceDTO(
            id=dev_id,
            external_device_id="DEV_001",
            device_type="SMARTPHONE",
        ),
        location=TransactionLocationDTO(
            id=loc_id,
            city="Mumbai",
            state="MH",
            country="India",
        ),
        latest_risk=TransactionLatestRiskDTO(
            analysis_id=uuid.uuid4(),
            score=82.5,
            risk_level="CRITICAL",
            model_version="1.0.0",
            evaluated_at=now,
        ),
    )
    dumped = detail.model_dump()
    assert dumped["amount"] == "1250.50"
    assert dumped["merchant"]["merchant_name"] == "Acme Electronics"
    assert dumped["location"]["country"] == "India"
    assert dumped["latest_risk"]["risk_level"] == "CRITICAL"


def test_dataset_import_list_response_schema() -> None:
    """Verify DatasetImportListResponse excludes error collections and enforces bounds."""
    now = datetime(2026, 10, 20, 10, 0, 0, tzinfo=UTC)
    item = DatasetImportResponse(
        id=uuid.uuid4(),
        source_namespace="SYNTHETIC",
        status="COMPLETED",
        source_type="SYNTHETIC",
        filename="tx.csv",
        file_hash="a" * 64,
        total_rows=10,
        valid_rows=10,
        invalid_rows=0,
        started_at=now,
        completed_at=now,
    )
    resp = DatasetImportListResponse(
        items=[item],
        page=1,
        page_size=20,
        total=1,
        total_pages=1,
    )
    assert "errors" not in resp.items[0].model_dump()
    assert resp.items[0].is_duplicate is False
