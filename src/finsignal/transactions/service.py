"""Transaction domain service handling validation, namespace isolation, and DTO mapping."""

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.common.exceptions import NotFoundError, ValidationError
from finsignal.transactions.repository import TransactionRepository
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

NAMESPACE_REGEX = re.compile(r"^[A-Z0-9_]{3,64}$")
ALLOWED_SORT_FIELDS: frozenset[str] = frozenset({"occurred_at", "amount", "created_at"})
ALLOWED_SORT_ORDERS: frozenset[str] = frozenset({"asc", "desc"})
MIN_TRANSACTION_AMOUNT = Decimal("0.01")


class TransactionService:
    """Orchestrates read-only transaction listing and detail retrieval."""

    def __init__(self, repo: TransactionRepository | None = None) -> None:
        self.repo = repo or TransactionRepository()

    def _validate_namespace(self, namespace: str) -> str:
        """Validate namespace against canonical uppercase alphanumeric/underscore format."""
        if not NAMESPACE_REGEX.match(namespace):
            raise ValidationError(
                message=(
                    f"Invalid namespace format: '{namespace}'. "
                    "Must match ^[A-Z0-9_]{3,64}$."
                ),
                code="INVALID_NAMESPACE_FORMAT",
                details={"source_namespace": namespace},
            )
        return namespace

    def _normalize_utc_datetime(
        self, value: datetime | None, field_name: str
    ) -> datetime | None:
        """Reject naive datetimes and normalize timezone-aware datetimes to UTC."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(
                message=f"Parameter '{field_name}' must include timezone information (UTC ISO 8601).",
                code="INVALID_TIMEZONE",
                details={"field": field_name},
            )
        return value.astimezone(UTC)

    def _validate_time_window(
        self, from_time: datetime | None, to_time: datetime | None
    ) -> tuple[datetime | None, datetime | None]:
        """Validate half-open UTC interval [from_time, to_time)."""
        norm_from = self._normalize_utc_datetime(from_time, "from_time")
        norm_to = self._normalize_utc_datetime(to_time, "to_time")
        if norm_from is not None and norm_to is not None and norm_from >= norm_to:
            raise ValidationError(
                message="from_time must be strictly earlier than to_time.",
                code="INVALID_DATE_RANGE",
                details={
                    "from_time": norm_from.isoformat(),
                    "to_time": norm_to.isoformat(),
                },
            )
        return norm_from, norm_to

    def _validate_amount_range(
        self, min_amount: Decimal | None, max_amount: Decimal | None
    ) -> None:
        """Validate finite positive decimal bounds and min_amount <= max_amount."""
        for field_name, val in (("min_amount", min_amount), ("max_amount", max_amount)):
            if val is None:
                continue
            if not val.is_finite():
                raise ValidationError(
                    message=f"Parameter '{field_name}' must be a finite decimal value.",
                    code="INVALID_AMOUNT_RANGE",
                    details={"field": field_name},
                )
            if val < MIN_TRANSACTION_AMOUNT:
                raise ValidationError(
                    message=f"Parameter '{field_name}' must be at least {MIN_TRANSACTION_AMOUNT}.",
                    code="INVALID_AMOUNT_RANGE",
                    details={"field": field_name},
                )

        if (
            min_amount is not None
            and max_amount is not None
            and min_amount > max_amount
        ):
            raise ValidationError(
                message="min_amount must be less than or equal to max_amount.",
                code="INVALID_AMOUNT_RANGE",
                details={
                    "min_amount": str(min_amount),
                    "max_amount": str(max_amount),
                },
            )

    def _validate_sort(self, sort_by: str, sort_order: str) -> tuple[str, str]:
        """Validate whitelisted sort column and case-insensitive sort direction."""
        if sort_by not in ALLOWED_SORT_FIELDS:
            raise ValidationError(
                message=(
                    f"Unsupported sort_by field '{sort_by}'. "
                    f"Allowed fields: {', '.join(sorted(ALLOWED_SORT_FIELDS))}."
                ),
                code="UNSUPPORTED_SORT_FIELD",
                details={"sort_by": sort_by},
            )
        norm_order = sort_order.strip().lower()
        if norm_order not in ALLOWED_SORT_ORDERS:
            raise ValidationError(
                message=f"Invalid sort_order '{sort_order}'. Must be 'asc' or 'desc'.",
                code="INVALID_SORT_ORDER",
                details={"sort_order": sort_order},
            )
        return sort_by, norm_order

    async def list_transactions(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 50,
        source_namespace: str = "SYNTHETIC",
        account_id: uuid.UUID | None = None,
        merchant_id: uuid.UUID | None = None,
        device_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        transaction_type: str | None = None,
        direction: str | None = None,
        category: str | None = None,
        currency: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        risk_level: str | None = None,
        sort_by: str = "occurred_at",
        sort_order: str = "desc",
    ) -> TransactionListResponse:
        """Validate filters, verify namespace existence, and return paginated transactions."""
        norm_ns = self._validate_namespace(source_namespace)
        norm_from, norm_to = self._validate_time_window(from_time, to_time)
        self._validate_amount_range(min_amount, max_amount)
        valid_sort_by, valid_sort_order = self._validate_sort(sort_by, sort_order)

        exists = await self.repo.verify_namespace_exists(session, norm_ns)
        if not exists:
            raise NotFoundError(
                message=f"Target namespace '{norm_ns}' does not exist.",
                code="NAMESPACE_NOT_FOUND",
                details={"source_namespace": norm_ns},
            )

        rows, total, total_pages = await self.repo.list_transactions(
            session,
            source_namespace=norm_ns,
            page=page,
            page_size=page_size,
            account_id=account_id,
            merchant_id=merchant_id,
            device_id=device_id,
            location_id=location_id,
            transaction_type=transaction_type,
            direction=direction,
            category=category,
            currency=currency,
            from_time=norm_from,
            to_time=norm_to,
            min_amount=min_amount,
            max_amount=max_amount,
            risk_level=risk_level,
            sort_by=valid_sort_by,
            sort_order=valid_sort_order,
        )

        items = [TransactionSummaryItem.model_validate(tx) for tx in rows]
        return TransactionListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def get_transaction_detail(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
        *,
        source_namespace: str | None = None,
    ) -> TransactionDetailResponse:
        """Retrieve complete transaction fact context with optional namespace fencing."""
        norm_ns = (
            self._validate_namespace(source_namespace)
            if source_namespace is not None
            else None
        )

        result = await self.repo.get_transaction_detail(
            session,
            transaction_id,
            source_namespace=norm_ns,
        )
        if result is None:
            raise NotFoundError(
                message=f"Transaction '{transaction_id}' not found.",
                code="TRANSACTION_NOT_FOUND",
                details={"transaction_id": str(transaction_id)},
            )

        tx, latest_ra = result

        latest_risk_dto: TransactionLatestRiskDTO | None = None
        if latest_ra is not None:
            model_ver = (
                latest_ra.model_version.version
                if latest_ra.model_version is not None
                else "unknown"
            )
            latest_risk_dto = TransactionLatestRiskDTO(
                analysis_id=latest_ra.id,
                score=float(latest_ra.score),
                risk_level=latest_ra.risk_level,
                model_version=model_ver,
                evaluated_at=latest_ra.created_at,
            )

        return TransactionDetailResponse(
            id=tx.id,
            source_namespace=tx.source_namespace,
            external_transaction_id=tx.external_transaction_id,
            first_seen_import_id=tx.first_seen_import_id,
            account_id=tx.account_id,
            counterparty_account_id=tx.counterparty_account_id,
            merchant_id=tx.merchant_id,
            device_id=tx.device_id,
            location_id=tx.location_id,
            occurred_at=tx.occurred_at,
            amount=tx.amount,
            currency=tx.currency,
            transaction_type=tx.transaction_type,
            direction=tx.direction,
            category=tx.category,
            payment_method=tx.payment_method,
            channel=tx.channel,
            created_at=tx.created_at,
            account=TransactionAccountDTO.model_validate(tx.account),
            counterparty_account=(
                TransactionAccountDTO.model_validate(tx.counterparty_account)
                if tx.counterparty_account is not None
                else None
            ),
            merchant=(
                TransactionMerchantDTO.model_validate(tx.merchant)
                if tx.merchant is not None
                else None
            ),
            device=(
                TransactionDeviceDTO.model_validate(tx.device)
                if tx.device is not None
                else None
            ),
            location=(
                TransactionLocationDTO.model_validate(tx.location)
                if tx.location is not None
                else None
            ),
            latest_risk=latest_risk_dto,
        )
