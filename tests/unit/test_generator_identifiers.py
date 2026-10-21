"""Unit tests for deterministic business identifier formatting and validation (ADR-065)."""

import pytest

from finsignal.dataset.generator.identifiers import (
    MAX_ACCOUNT_CAPACITY,
    MAX_DEVICE_CAPACITY,
    MAX_LOCATION_CAPACITY,
    MAX_MERCHANT_CAPACITY,
    format_account_id,
    format_device_id,
    format_location_id,
    format_merchant_id,
    is_valid_account_id,
    is_valid_device_id,
    is_valid_location_id,
    is_valid_merchant_id,
)


def test_format_account_id() -> None:
    """Verify account ID format ACC_[0-9]{6} and boundary behavior."""
    assert format_account_id(1) == "ACC_000001"
    assert format_account_id(999) == "ACC_000999"
    assert format_account_id(MAX_ACCOUNT_CAPACITY) == "ACC_999999"

    with pytest.raises(ValueError, match="out of capacity"):
        format_account_id(0)

    with pytest.raises(ValueError, match="out of capacity"):
        format_account_id(-1)

    with pytest.raises(ValueError, match="out of capacity"):
        format_account_id(MAX_ACCOUNT_CAPACITY + 1)


def test_format_merchant_id() -> None:
    """Verify merchant ID format MERCH_[0-9]{5} and boundary behavior."""
    assert format_merchant_id(1) == "MERCH_00001"
    assert format_merchant_id(500) == "MERCH_00500"
    assert format_merchant_id(MAX_MERCHANT_CAPACITY) == "MERCH_99999"

    with pytest.raises(ValueError, match="out of capacity"):
        format_merchant_id(0)

    with pytest.raises(ValueError, match="out of capacity"):
        format_merchant_id(MAX_MERCHANT_CAPACITY + 1)


def test_format_device_id() -> None:
    """Verify device ID format DEV_[0-9]{6} and boundary behavior."""
    assert format_device_id(1) == "DEV_000001"
    assert format_device_id(8000) == "DEV_008000"
    assert format_device_id(MAX_DEVICE_CAPACITY) == "DEV_999999"

    with pytest.raises(ValueError, match="out of capacity"):
        format_device_id(0)

    with pytest.raises(ValueError, match="out of capacity"):
        format_device_id(MAX_DEVICE_CAPACITY + 1)


def test_format_location_id() -> None:
    """Verify location ID format LOC_[0-9]{3} and boundary behavior."""
    assert format_location_id(1) == "LOC_001"
    assert format_location_id(100) == "LOC_100"
    assert format_location_id(MAX_LOCATION_CAPACITY) == "LOC_999"

    with pytest.raises(ValueError, match="out of capacity"):
        format_location_id(0)

    with pytest.raises(ValueError, match="out of capacity"):
        format_location_id(MAX_LOCATION_CAPACITY + 1)


def test_identifier_validators() -> None:
    """Verify regex validation helper functions."""
    assert is_valid_account_id("ACC_000001")
    assert not is_valid_account_id("acc_000001")
    assert not is_valid_account_id("ACC_0001")

    assert is_valid_merchant_id("MERCH_00001")
    assert not is_valid_merchant_id("MERCH_000001")

    assert is_valid_device_id("DEV_000001")
    assert not is_valid_device_id("DEV_1")

    assert is_valid_location_id("LOC_001")
    assert not is_valid_location_id("LOC_0001")
