"""Unit tests for namespace validation and NamespaceMismatchError (ADR-065 Decision D)."""

import pytest

from finsignal.common.exceptions import (
    FinSignalError,
    NamespaceMismatchError,
    ValidationError,
)
from finsignal.transactions.validation import validate_transaction_account_namespace


def test_namespace_mismatch_error_properties() -> None:
    """Verify NamespaceMismatchError error code, status_code, and hierarchy."""
    err = NamespaceMismatchError(
        message="Transaction namespace does not match account namespace.",
        details={
            "account_namespace": "SYNTHETIC",
            "transaction_namespace": "CORE_BANKING",
        },
    )
    assert isinstance(err, ValidationError)
    assert isinstance(err, FinSignalError)
    assert err.code == "NAMESPACE_MISMATCH"
    assert err.status_code == 422
    assert err.details["account_namespace"] == "SYNTHETIC"
    assert err.details["transaction_namespace"] == "CORE_BANKING"


def test_validate_transaction_account_namespace_success() -> None:
    """Verify validation succeeds when account and transaction namespaces match."""
    # Matching namespaces must not raise
    validate_transaction_account_namespace("SYNTHETIC", "SYNTHETIC")
    validate_transaction_account_namespace("CORE_BANKING", "CORE_BANKING")
    validate_transaction_account_namespace("PARTNER_A", "PARTNER_A")


def test_validate_transaction_account_namespace_failure() -> None:
    """Verify validation raises NamespaceMismatchError on mismatch."""
    with pytest.raises(NamespaceMismatchError) as exc_info:
        validate_transaction_account_namespace("SYNTHETIC", "CORE_BANKING")

    err = exc_info.value
    assert err.code == "NAMESPACE_MISMATCH"
    assert err.status_code == 422
    assert "CORE_BANKING" in str(err)
    assert "SYNTHETIC" in str(err)
    assert err.details["account_namespace"] == "SYNTHETIC"
    assert err.details["transaction_namespace"] == "CORE_BANKING"
