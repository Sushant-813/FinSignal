"""Pydantic v2 schemas for Transaction list and detail endpoints (Phase F0.2)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from finsignal.common.types import MoneyStr


class TransactionSummaryItem(BaseModel):
    """Summary representation of a canonical transaction fact in list responses."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    source_namespace: str
    external_transaction_id: str
    account_id: uuid.UUID
    counterparty_account_id: uuid.UUID | None = None
    merchant_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    occurred_at: datetime
    amount: MoneyStr
    currency: str
    transaction_type: str
    direction: str
    category: str | None = None
    payment_method: str | None = None
    channel: str | None = None
    first_seen_import_id: uuid.UUID | None = None
    created_at: datetime


class TransactionListResponse(BaseModel):
    """Paginated collection response for transaction exploration."""

    model_config = ConfigDict(extra="forbid")

    items: list[TransactionSummaryItem]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class TransactionAccountDTO(BaseModel):
    """Reference account summary embedded in transaction detail."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    external_account_id: str | None = None
    account_type: str
    status: str


class TransactionMerchantDTO(BaseModel):
    """Reference merchant summary embedded in transaction detail."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    external_merchant_id: str | None = None
    merchant_name: str
    merchant_category: str


class TransactionDeviceDTO(BaseModel):
    """Reference device summary embedded in transaction detail."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    external_device_id: str | None = None
    device_type: str | None = None


class TransactionLocationDTO(BaseModel):
    """Reference location summary embedded in transaction detail."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    city: str
    state: str | None = None
    country: str


class TransactionLatestRiskDTO(BaseModel):
    """Lightweight latest risk analysis snapshot for transaction detail."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: uuid.UUID
    score: float
    risk_level: str
    model_version: str
    evaluated_at: datetime


class TransactionDetailResponse(BaseModel):
    """Complete authoritative transaction fact context with relational entities."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    source_namespace: str
    external_transaction_id: str
    first_seen_import_id: uuid.UUID | None = None
    account_id: uuid.UUID
    counterparty_account_id: uuid.UUID | None = None
    merchant_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    occurred_at: datetime
    amount: MoneyStr
    currency: str
    transaction_type: str
    direction: str
    category: str | None = None
    payment_method: str | None = None
    channel: str | None = None
    created_at: datetime
    account: TransactionAccountDTO
    counterparty_account: TransactionAccountDTO | None = None
    merchant: TransactionMerchantDTO | None = None
    device: TransactionDeviceDTO | None = None
    location: TransactionLocationDTO | None = None
    latest_risk: TransactionLatestRiskDTO | None = None
