"""Transaction domain validation functions and invariants."""

from finsignal.common.exceptions import NamespaceMismatchError


def validate_transaction_account_namespace(
    account_namespace: str,
    transaction_namespace: str,
) -> None:
    """Validate that the transaction namespace matches the account namespace.

    Layered Enforcement (ADR-065 Decision D Section 7):
    Application-level validation provides early developer-friendly diagnostics
    with error code 'NAMESPACE_MISMATCH' prior to database persistence.
    """
    if account_namespace != transaction_namespace:
        raise NamespaceMismatchError(
            message=(
                f"Transaction source namespace '{transaction_namespace}' does not match "
                f"account source namespace '{account_namespace}'."
            ),
            details={
                "account_namespace": account_namespace,
                "transaction_namespace": transaction_namespace,
            },
        )
