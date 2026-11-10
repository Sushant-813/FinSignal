"""Shared Pydantic value types and monetary serialization helpers."""

from decimal import Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator


def to_money_str(v: Any) -> str:
    """Format monetary numbers to strict two-decimal string representation."""
    if v is None:
        return "0.00"
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    if isinstance(v, (int, float)):
        return f"{Decimal(str(v)):.2f}"
    if isinstance(v, str):
        return f"{Decimal(v):.2f}"
    raise ValueError(f"Cannot format {v!r} as monetary string")


def to_optional_money_str(v: Any) -> str | None:
    """Format optional monetary numbers to strict two-decimal string or None."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    if isinstance(v, (int, float)):
        return f"{Decimal(str(v)):.2f}"
    if isinstance(v, str):
        return f"{Decimal(v):.2f}"
    raise ValueError(f"Cannot format {v!r} as monetary string")


MoneyStr = Annotated[str, BeforeValidator(to_money_str)]
OptionalMoneyStr = Annotated[str | None, BeforeValidator(to_optional_money_str)]
