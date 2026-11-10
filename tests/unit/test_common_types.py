"""Unit tests for shared monetary serialization types in finsignal.common.types."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, ConfigDict

from finsignal.analytics import schemas as analytics_schemas
from finsignal.common import types as common_types
from finsignal.common.types import (
    MoneyStr,
    OptionalMoneyStr,
    to_money_str,
    to_optional_money_str,
)


class _SampleMoneyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_amount: MoneyStr
    optional_amount: OptionalMoneyStr = None


def test_to_money_str_formatting() -> None:
    """Verify to_money_str formats supported types verbatim to two-decimal strings."""
    assert to_money_str(Decimal("123.456")) == "123.46"
    assert to_money_str(Decimal("123.4")) == "123.40"
    assert to_money_str(Decimal("75000.00")) == "75000.00"
    assert to_money_str(100) == "100.00"
    assert to_money_str(99.9) == "99.90"
    assert to_money_str("45000.5") == "45000.50"
    assert to_money_str(None) == "0.00"

    with pytest.raises(ValueError, match="Cannot format"):
        to_money_str(object())


def test_to_optional_money_str_formatting() -> None:
    """Verify to_optional_money_str preserves None and formats numeric/string values."""
    assert to_optional_money_str(None) is None
    assert to_optional_money_str(Decimal("0")) == "0.00"
    assert to_optional_money_str(42) == "42.00"
    assert to_optional_money_str(12.5) == "12.50"
    assert to_optional_money_str("12.34") == "12.34"

    with pytest.raises(ValueError, match="Cannot format"):
        to_optional_money_str(object())


def test_pydantic_money_annotations() -> None:
    """Verify MoneyStr and OptionalMoneyStr serialize values inside Pydantic models."""
    populated = _SampleMoneyModel(
        required_amount=Decimal("75000.00"),
        optional_amount=Decimal("10.5"),
    )
    assert populated.model_dump() == {
        "required_amount": "75000.00",
        "optional_amount": "10.50",
    }

    with_none = _SampleMoneyModel(required_amount="0")
    assert with_none.model_dump() == {
        "required_amount": "0.00",
        "optional_amount": None,
    }


def test_backward_compatible_analytics_reexports() -> None:
    """Verify analytics.schemas re-exports the exact objects from common.types."""
    assert analytics_schemas.MoneyStr is common_types.MoneyStr
    assert analytics_schemas.OptionalMoneyStr is common_types.OptionalMoneyStr
    assert analytics_schemas.to_money_str is common_types.to_money_str
    assert analytics_schemas.to_optional_money_str is common_types.to_optional_money_str
