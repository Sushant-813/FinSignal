"""Deterministic business identifier formatting and validation (ADR-065 Decision B)."""

import re

ACCOUNT_ID_PATTERN = re.compile(r"^ACC_\d{6}$")
MERCHANT_ID_PATTERN = re.compile(r"^MERCH_\d{5}$")
DEVICE_ID_PATTERN = re.compile(r"^DEV_\d{6}$")
LOCATION_ID_PATTERN = re.compile(r"^LOC_\d{3}$")
TRANSACTION_ID_PATTERN = re.compile(r"^TXN_\d{8}$")

MAX_ACCOUNT_CAPACITY = 999_999
MAX_MERCHANT_CAPACITY = 99_999
MAX_DEVICE_CAPACITY = 999_999
MAX_LOCATION_CAPACITY = 999
MAX_TRANSACTION_CAPACITY = 99_999_999


def format_account_id(index: int) -> str:
    """Format a 1-based sequential integer into an account identifier (ACC_[0-9]{6}).

    Raises:
        ValueError: If index is <= 0 or exceeds the 6-digit capacity (999,999).
    """
    if index <= 0 or index > MAX_ACCOUNT_CAPACITY:
        raise ValueError(
            f"Account index {index} out of capacity [1, {MAX_ACCOUNT_CAPACITY}]."
        )
    return f"ACC_{index:06d}"


def format_merchant_id(index: int) -> str:
    """Format a 1-based sequential integer into a merchant identifier (MERCH_[0-9]{5}).

    Raises:
        ValueError: If index is <= 0 or exceeds the 5-digit capacity (99,999).
    """
    if index <= 0 or index > MAX_MERCHANT_CAPACITY:
        raise ValueError(
            f"Merchant index {index} out of capacity [1, {MAX_MERCHANT_CAPACITY}]."
        )
    return f"MERCH_{index:05d}"


def format_device_id(index: int) -> str:
    """Format a 1-based sequential integer into a device identifier (DEV_[0-9]{6}).

    Raises:
        ValueError: If index is <= 0 or exceeds the 6-digit capacity (999,999).
    """
    if index <= 0 or index > MAX_DEVICE_CAPACITY:
        raise ValueError(
            f"Device index {index} out of capacity [1, {MAX_DEVICE_CAPACITY}]."
        )
    return f"DEV_{index:06d}"


def format_location_id(index: int) -> str:
    """Format a 1-based sequential integer into a location identifier (LOC_[0-9]{3}).

    Raises:
        ValueError: If index is <= 0 or exceeds the 3-digit capacity (999).
    """
    if index <= 0 or index > MAX_LOCATION_CAPACITY:
        raise ValueError(
            f"Location index {index} out of capacity [1, {MAX_LOCATION_CAPACITY}]."
        )
    return f"LOC_{index:03d}"


def format_transaction_id(index: int) -> str:
    """Format a 1-based sequential integer into a transaction identifier (TXN_[0-9]{8}).

    Raises:
        ValueError: If index is <= 0 or exceeds the 8-digit capacity (99,999,999).
    """
    if index <= 0 or index > MAX_TRANSACTION_CAPACITY:
        raise ValueError(
            f"Transaction index {index} out of capacity [1, {MAX_TRANSACTION_CAPACITY}]."
        )
    return f"TXN_{index:08d}"


def is_valid_account_id(identifier: str) -> bool:
    """Check if string matches the canonical account ID format."""
    return bool(ACCOUNT_ID_PATTERN.match(identifier))


def is_valid_merchant_id(identifier: str) -> bool:
    """Check if string matches the canonical merchant ID format."""
    return bool(MERCHANT_ID_PATTERN.match(identifier))


def is_valid_device_id(identifier: str) -> bool:
    """Check if string matches the canonical device ID format."""
    return bool(DEVICE_ID_PATTERN.match(identifier))


def is_valid_location_id(identifier: str) -> bool:
    """Check if string matches the canonical location ID format."""
    return bool(LOCATION_ID_PATTERN.match(identifier))


def is_valid_transaction_id(identifier: str) -> bool:
    """Check if string matches the canonical transaction ID format."""
    return bool(TRANSACTION_ID_PATTERN.match(identifier))
