"""Unit tests for canonical transaction row hashing and normalization."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from finsignal.transactions.hashing import (
    build_canonical_row_payload,
    compute_canonical_row_hash,
    serialize_canonical_row_json,
)


@pytest.fixture
def valid_test_vector_payload() -> dict[str, object]:
    """Canonical test vector payload with valid hex UUIDs and direction='DEBIT'."""
    return {
        "account_id": "a0000000-0000-0000-0000-000000000001",
        "amount": "125.50",
        "category": "GROCERY",
        "channel": "POS",
        "counterparty_account_id": None,
        "currency": "USD",
        "device_id": "d0000000-0000-0000-0000-000000000001",
        "direction": "DEBIT",
        "external_transaction_id": "TXN_00000001",
        "location_id": "c0000000-0000-0000-0000-000000000001",
        "merchant_id": "e0000000-0000-0000-0000-000000000001",
        "occurred_at": "2026-10-18T13:30:00.000000Z",
        "payment_method": "CHIP",
        "source_namespace": "SYNTHETIC",
        "transaction_type": "PURCHASE",
    }


def test_canonical_test_vector_serialization_and_digest(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify that the exact test vector reproduces the expected canonical JSON and SHA-256."""
    expected_json = (
        '{"account_id":"a0000000-0000-0000-0000-000000000001","amount":"125.50",'
        '"category":"GROCERY","channel":"POS","counterparty_account_id":null,'
        '"currency":"USD","device_id":"d0000000-0000-0000-0000-000000000001",'
        '"direction":"DEBIT","external_transaction_id":"TXN_00000001",'
        '"location_id":"c0000000-0000-0000-0000-000000000001",'
        '"merchant_id":"e0000000-0000-0000-0000-000000000001",'
        '"occurred_at":"2026-10-18T13:30:00.000000Z","payment_method":"CHIP",'
        '"source_namespace":"SYNTHETIC","transaction_type":"PURCHASE"}'
    )
    expected_digest = "1a5a4a225797715e7a1c98c6901285120cb4857df19d4ca7eb3f53f5646f686b"

    canonical = build_canonical_row_payload(valid_test_vector_payload)
    serialized = serialize_canonical_row_json(canonical)
    digest = compute_canonical_row_hash(valid_test_vector_payload)

    assert serialized == expected_json
    assert digest == expected_digest


def test_typed_inputs_produce_same_canonical_digest(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify that typed objects (UUID, Decimal, aware datetime) produce identical digest."""
    typed_payload = dict(valid_test_vector_payload)
    typed_payload["account_id"] = uuid.UUID("a0000000-0000-0000-0000-000000000001")
    typed_payload["location_id"] = uuid.UUID("c0000000-0000-0000-0000-000000000001")
    typed_payload["device_id"] = uuid.UUID("d0000000-0000-0000-0000-000000000001")
    typed_payload["merchant_id"] = uuid.UUID("e0000000-0000-0000-0000-000000000001")
    typed_payload["amount"] = Decimal("125.50")
    typed_payload["occurred_at"] = datetime(2026, 10, 18, 13, 30, 0, tzinfo=UTC)

    digest = compute_canonical_row_hash(typed_payload)
    assert digest == "1a5a4a225797715e7a1c98c6901285120cb4857df19d4ca7eb3f53f5646f686b"


def test_missing_and_extra_keys_rejection(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify that missing any canonical key or providing extra keys raises ValueError."""
    # Missing key
    missing_payload = dict(valid_test_vector_payload)
    del missing_payload["currency"]
    with pytest.raises(ValueError, match="Missing required canonical keys.*currency"):
        build_canonical_row_payload(missing_payload)

    # Extra key
    extra_payload = dict(valid_test_vector_payload)
    extra_payload["unexpected_field"] = "foo"
    with pytest.raises(ValueError, match="Unexpected extra keys.*unexpected_field"):
        build_canonical_row_payload(extra_payload)


def test_invalid_uuid_rejection(valid_test_vector_payload: dict[str, object]) -> None:
    """Verify invalid UUID strings are rejected."""
    bad_payload = dict(valid_test_vector_payload)
    bad_payload["account_id"] = "not-a-valid-uuid"
    with pytest.raises(
        ValueError, match="Field 'account_id' must be a valid UUID string"
    ):
        build_canonical_row_payload(bad_payload)


def test_naive_timestamp_rejection(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify naive datetimes without timezone are rejected."""
    bad_payload = dict(valid_test_vector_payload)
    bad_payload["occurred_at"] = datetime(2026, 10, 18, 13, 30, 0)
    with pytest.raises(ValueError, match="naive datetimes are forbidden"):
        build_canonical_row_payload(bad_payload)


def test_utc_normalization_timezone_offsets(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify that timestamps with different timezone offsets matching same instant yield identical hash."""
    payload_utc = dict(valid_test_vector_payload)
    payload_utc["occurred_at"] = "2026-10-18T13:30:00.000000Z"

    # +02:00 offset (15:30:00 in +02:00 is 13:30:00 UTC)
    payload_offset = dict(valid_test_vector_payload)
    payload_offset["occurred_at"] = "2026-10-18T15:30:00.000000+02:00"

    hash_utc = compute_canonical_row_hash(payload_utc)
    hash_offset = compute_canonical_row_hash(payload_offset)
    assert hash_utc == hash_offset


def test_float_rejection(valid_test_vector_payload: dict[str, object]) -> None:
    """Verify float types are rejected for monetary amounts."""
    bad_payload = dict(valid_test_vector_payload)
    bad_payload["amount"] = 125.50
    with pytest.raises(TypeError, match="cannot be a float"):
        build_canonical_row_payload(bad_payload)


def test_monetary_strict_representation_scale(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify strict representation-scale rejection of non-2 decimal places."""
    bad_cases = [
        "125.5",
        "125.500",
        "125.505",
        Decimal("125.5"),
        Decimal("125.500"),
        Decimal("125.505"),
    ]
    for bad_amt in bad_cases:
        bad_payload = dict(valid_test_vector_payload)
        bad_payload["amount"] = bad_amt
        with pytest.raises(ValueError):
            build_canonical_row_payload(bad_payload)


def test_zero_and_negative_amount_rejection(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify zero and negative amounts are rejected."""
    for bad_amt in ["0.00", "-10.00", Decimal("0.00"), Decimal("-1.50")]:
        bad_payload = dict(valid_test_vector_payload)
        bad_payload["amount"] = bad_amt
        with pytest.raises(ValueError, match="must be positive"):
            build_canonical_row_payload(bad_payload)


def test_invalid_currency_and_direction(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify malformed currency or direction are rejected."""
    # Currency
    for bad_curr in ["US", "us", "USDD", "123"]:
        bad_payload = dict(valid_test_vector_payload)
        bad_payload["currency"] = bad_curr
        with pytest.raises(ValueError, match="uppercase 3-letter ISO code"):
            build_canonical_row_payload(bad_payload)

    # Direction
    for bad_dir in ["OUTBOUND", "INBOUND", "debit", "CRED"]:
        bad_payload = dict(valid_test_vector_payload)
        bad_payload["direction"] = bad_dir
        with pytest.raises(ValueError, match="must be 'DEBIT' or 'CREDIT'"):
            build_canonical_row_payload(bad_payload)


def test_unicode_nfc_equivalence(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify that canonically equivalent Unicode strings (decomposed vs precomposed) yield identical hash."""
    # Decomposed: 'e' + combining acute accent (\u0301)
    payload_decomposed = dict(valid_test_vector_payload)
    payload_decomposed["category"] = "Cafe\u0301"

    # Precomposed: '\u00e9'
    payload_precomposed = dict(valid_test_vector_payload)
    payload_precomposed["category"] = "Caf\u00e9"

    hash_decomposed = compute_canonical_row_hash(payload_decomposed)
    hash_precomposed = compute_canonical_row_hash(payload_precomposed)
    assert hash_decomposed == hash_precomposed


def test_external_transaction_id_whitespace_and_case_preserved(
    valid_test_vector_payload: dict[str, object],
) -> None:
    """Verify external_transaction_id preserves exact whitespace and casing without silent stripping."""
    payload_a = dict(valid_test_vector_payload)
    payload_a["external_transaction_id"] = " txn_123 "

    payload_b = dict(valid_test_vector_payload)
    payload_b["external_transaction_id"] = "txn_123"

    canon_a = build_canonical_row_payload(payload_a)
    canon_b = build_canonical_row_payload(payload_b)
    assert canon_a["external_transaction_id"] == " txn_123 "
    assert canon_b["external_transaction_id"] == "txn_123"
    assert compute_canonical_row_hash(payload_a) != compute_canonical_row_hash(
        payload_b
    )
