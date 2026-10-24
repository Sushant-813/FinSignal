"""Unit tests for AnalyticsService validation and domain logic (Phase 5)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from finsignal.analytics.service import AnalyticsService
from finsignal.common.exceptions import NotFoundError, ValidationError
from finsignal.users.models import User


@pytest.fixture
def dummy_user() -> User:
    """Create a mock user for testing service authorization."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = "ANALYST"
    return user


@pytest.mark.asyncio
async def test_validate_namespace_format(dummy_user: User) -> None:
    """Verify namespace format validation rules."""
    service = AnalyticsService()
    # Invalid syntax
    with pytest.raises(ValidationError) as exc:
        service._validate_namespace_format("ab")  # too short
    assert exc.value.code == "INVALID_NAMESPACE_FORMAT"

    with pytest.raises(ValidationError) as exc:
        service._validate_namespace_format("synthetic-lower")  # lowercase and dashes
    assert exc.value.code == "INVALID_NAMESPACE_FORMAT"

    # Valid syntax does not raise
    service._validate_namespace_format("SYNTHETIC")
    service._validate_namespace_format("NAMESPACE_123")


@pytest.mark.asyncio
async def test_validate_currency_format(dummy_user: User) -> None:
    """Verify currency code validation."""
    service = AnalyticsService()
    with pytest.raises(ValidationError) as exc:
        service._validate_currency_format("us")
    assert exc.value.code == "INVALID_CURRENCY_FORMAT"

    with pytest.raises(ValidationError) as exc:
        service._validate_currency_format("usd")  # lowercase
    assert exc.value.code == "INVALID_CURRENCY_FORMAT"

    # Valid syntax does not raise
    service._validate_currency_format("INR")
    service._validate_currency_format("USD")


@pytest.mark.asyncio
async def test_validate_time_window(dummy_user: User) -> None:
    """Verify half-open time window validation: from_time must be strictly earlier than to_time."""
    service = AnalyticsService()
    t0 = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC)

    # Valid: from_time < to_time
    service._validate_time_window(t0, t1)

    # Valid: either is None
    service._validate_time_window(t0, None)
    service._validate_time_window(None, t1)
    service._validate_time_window(None, None)

    # Invalid: from_time == to_time
    with pytest.raises(ValidationError) as exc:
        service._validate_time_window(t0, t0)
    assert exc.value.code == "INVALID_DATE_RANGE"

    # Invalid: from_time > to_time
    with pytest.raises(ValidationError) as exc:
        service._validate_time_window(t1, t0)
    assert exc.value.code == "INVALID_DATE_RANGE"


@pytest.mark.asyncio
async def test_validate_timezone(dummy_user: User) -> None:
    """Verify timezone validation against IANA database."""
    service = AnalyticsService()
    assert service._validate_timezone("UTC") == "UTC"
    assert service._validate_timezone("America/New_York") == "America/New_York"
    assert service._validate_timezone("Asia/Kolkata") == "Asia/Kolkata"

    with pytest.raises(ValidationError) as exc:
        service._validate_timezone("Invalid/NonExistent_Zone")
    assert exc.value.code == "INVALID_TIMEZONE"


@pytest.mark.asyncio
async def test_trends_bucket_limit_exceeded(dummy_user: User) -> None:
    """Verify requesting more than 366 daily buckets raises TREND_BUCKET_COUNT_EXCEEDS_LIMIT."""
    service = AnalyticsService()
    # Mock namespace verification so it passes
    service.repo.verify_namespace_exists = AsyncMock(return_value=True)  # type: ignore

    session = AsyncMock()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2027, 2, 1, 0, 0, 0, tzinfo=UTC)  # ~396 days

    with pytest.raises(ValidationError) as exc:
        await service.get_trends(
            session=session,
            user=dummy_user,
            from_time=t0,
            to_time=t1,
            interval="day",
        )
    assert exc.value.code == "TREND_BUCKET_COUNT_EXCEEDS_LIMIT"


@pytest.mark.asyncio
async def test_trends_invalid_interval(dummy_user: User) -> None:
    """Verify requesting unsupported interval raises INVALID_INTERVAL."""
    service = AnalyticsService()
    service.repo.verify_namespace_exists = AsyncMock(return_value=True)  # type: ignore

    session = AsyncMock()
    t0 = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 9, 2, 0, 0, 0, tzinfo=UTC)

    with pytest.raises(ValidationError) as exc:
        await service.get_trends(
            session=session,
            user=dummy_user,
            from_time=t0,
            to_time=t1,
            interval="hourly",
        )
    assert exc.value.code == "INVALID_INTERVAL"


@pytest.mark.asyncio
async def test_unusual_spending_invalid_multiplier(dummy_user: User) -> None:
    """Verify multiplier must be between 1.5 and 10.0."""
    service = AnalyticsService()
    mock_account = MagicMock()
    mock_account.id = uuid.uuid4()
    mock_account.source_namespace = "SYNTHETIC"
    service.repo.get_account_by_id = AsyncMock(return_value=mock_account)  # type: ignore

    session = AsyncMock()
    with pytest.raises(ValidationError) as exc:
        await service.get_unusual_spending(
            session=session,
            user=dummy_user,
            account_id=mock_account.id,
            multiplier=Decimal("1.2"),  # below 1.5
        )
    assert exc.value.code == "INVALID_MULTIPLIER"

    with pytest.raises(ValidationError) as exc:
        await service.get_unusual_spending(
            session=session,
            user=dummy_user,
            account_id=mock_account.id,
            multiplier=Decimal("12.0"),  # above 10.0
        )
    assert exc.value.code == "INVALID_MULTIPLIER"


@pytest.mark.asyncio
async def test_namespace_not_found(dummy_user: User) -> None:
    """Verify querying nonexistent namespace raises NotFoundError."""
    service = AnalyticsService()
    service.repo.verify_namespace_exists = AsyncMock(return_value=False)  # type: ignore

    session = AsyncMock()
    with pytest.raises(NotFoundError) as exc:
        await service.get_overview(
            session=session,
            user=dummy_user,
            namespace="UNKNOWN_NS",
        )
    assert exc.value.code == "NAMESPACE_NOT_FOUND"


@pytest.mark.asyncio
async def test_account_not_found(dummy_user: User) -> None:
    """Verify querying nonexistent account raises NotFoundError."""
    service = AnalyticsService()
    service.repo.get_account_by_id = AsyncMock(return_value=None)  # type: ignore

    session = AsyncMock()
    random_id = uuid.uuid4()
    with pytest.raises(NotFoundError) as exc:
        await service.get_account_activity(
            session=session,
            user=dummy_user,
            account_id=random_id,
        )
    assert exc.value.code == "RESOURCE_NOT_FOUND"
