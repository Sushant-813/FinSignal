"""Canonical transaction hashing and serialization utilities for FinSignal."""

import hashlib
import json
import re
import unicodedata
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

CANONICAL_FIELD_KEYS: tuple[str, ...] = (
    "account_id",
    "amount",
    "category",
    "channel",
    "counterparty_account_id",
    "currency",
    "device_id",
    "direction",
    "external_transaction_id",
    "location_id",
    "merchant_id",
    "occurred_at",
    "payment_method",
    "source_namespace",
    "transaction_type",
)

CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")
NAMESPACE_REGEX = re.compile(r"^[A-Z0-9_]{1,64}$")
TRANSACTION_TYPE_REGEX = re.compile(r"^[A-Z0-9_]{1,32}$")
FIXED_POINT_REGEX = re.compile(r"^-?\d+\.\d{2}$")


def normalize_uuid(value: Any, field_name: str) -> str:
    """Validate and normalize a UUID to a lowercase 36-character hyphenated string."""
    if isinstance(value, uuid.UUID):
        return str(value).lower()
    if isinstance(value, str):
        normalized_str = unicodedata.normalize("NFC", value).strip().lower()
        try:
            parsed = uuid.UUID(normalized_str)
            return str(parsed).lower()
        except ValueError as err:
            raise ValueError(
                f"Field '{field_name}' must be a valid UUID string: {value!r}"
            ) from err
    raise TypeError(
        f"Field '{field_name}' must be a uuid.UUID instance or UUID string, got {type(value).__name__}"
    )


def normalize_timestamp(value: Any, field_name: str) -> str:
    """Validate and normalize a timestamp to UTC ISO 8601 with 6 fractional digits and Z."""
    dt: datetime
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        normalized_str = unicodedata.normalize("NFC", value).strip()
        try:
            if normalized_str.endswith("Z"):
                dt = datetime.fromisoformat(normalized_str[:-1] + "+00:00")
            else:
                dt = datetime.fromisoformat(normalized_str)
        except ValueError as err:
            raise ValueError(
                f"Field '{field_name}' must be a valid ISO 8601 timestamp string: {value!r}"
            ) from err
    else:
        raise TypeError(
            f"Field '{field_name}' must be a datetime or ISO 8601 string, got {type(value).__name__}"
        )

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(
            f"Field '{field_name}' must be timezone-aware; naive datetimes are forbidden"
        )

    utc_dt = dt.astimezone(UTC)
    return str(utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))


def normalize_monetary_amount(value: Any, field_name: str) -> str:
    """Validate and normalize monetary amount following strict representation-scale rules."""
    if isinstance(value, float):
        raise TypeError(
            f"Field '{field_name}' cannot be a float; use Decimal or fixed-point string to prevent precision loss"
        )

    if isinstance(value, str):
        normalized_str = unicodedata.normalize("NFC", value).strip()
        if not FIXED_POINT_REGEX.match(normalized_str):
            raise ValueError(
                f"Field '{field_name}' string must match exact two-decimal fixed-point format (e.g. '125.50'): {value!r}"
            )
        try:
            dec = Decimal(normalized_str)
        except Exception as err:
            raise ValueError(
                f"Field '{field_name}' is not a valid decimal: {value!r}"
            ) from err
    elif isinstance(value, Decimal):
        dec = value
        # Enforce that exponent is exactly -2 (no more or fewer than 2 decimal places represented)
        if dec.as_tuple().exponent != -2:
            raise ValueError(
                f"Field '{field_name}' Decimal must have exact scale of 2 (exponent -2); got exponent {dec.as_tuple().exponent} for {value!r}"
            )
    else:
        raise TypeError(
            f"Field '{field_name}' must be a Decimal or fixed-point str, got {type(value).__name__}"
        )

    if dec <= Decimal("0"):
        raise ValueError(
            f"Field '{field_name}' must be positive (amount > 0), got {dec}"
        )

    return f"{dec:.2f}"


def build_canonical_row_payload(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Validate raw row inputs and construct the canonical 15-key dictionary.

    Enforces:
    1. Exact 15 canonical keys (no missing, no extra keys).
    2. Input type validation and field-specific normalization.
    3. Unicode NFC normalization on all text.
    4. Strict decimal, timestamp, and UUID validation.
    """
    input_keys = set(raw_row.keys())
    expected_keys = set(CANONICAL_FIELD_KEYS)

    missing = expected_keys - input_keys
    if missing:
        raise ValueError(f"Missing required canonical keys: {sorted(missing)}")

    extra = input_keys - expected_keys
    if extra:
        raise ValueError(f"Unexpected extra keys in row_hash payload: {sorted(extra)}")

    canonical: dict[str, Any] = {}

    # 1. account_id (UUID, NOT NULL)
    canonical["account_id"] = normalize_uuid(raw_row["account_id"], "account_id")

    # 2. amount (Decimal/str with scale 2, > 0, NOT NULL)
    canonical["amount"] = normalize_monetary_amount(raw_row["amount"], "amount")

    # 3. category (str | None)
    cat = raw_row["category"]
    if cat is None:
        canonical["category"] = None
    elif isinstance(cat, str):
        canonical["category"] = unicodedata.normalize("NFC", cat)
    else:
        raise TypeError(
            f"Field 'category' must be a str or None, got {type(cat).__name__}"
        )

    # 4. channel (str | None)
    chan = raw_row["channel"]
    if chan is None:
        canonical["channel"] = None
    elif isinstance(chan, str):
        canonical["channel"] = unicodedata.normalize("NFC", chan)
    else:
        raise TypeError(
            f"Field 'channel' must be a str or None, got {type(chan).__name__}"
        )

    # 5. counterparty_account_id (UUID | None)
    c_acc = raw_row["counterparty_account_id"]
    if c_acc is None:
        canonical["counterparty_account_id"] = None
    else:
        canonical["counterparty_account_id"] = normalize_uuid(
            c_acc, "counterparty_account_id"
        )

    # 6. currency (3-letter uppercase, NOT NULL)
    curr = raw_row["currency"]
    if not isinstance(curr, str):
        raise TypeError(f"Field 'currency' must be str, got {type(curr).__name__}")
    norm_curr = unicodedata.normalize("NFC", curr)
    if not CURRENCY_REGEX.match(norm_curr):
        raise ValueError(
            f"Field 'currency' must be an uppercase 3-letter ISO code: {curr!r}"
        )
    canonical["currency"] = norm_curr

    # 7. device_id (UUID | None)
    dev = raw_row["device_id"]
    if dev is None:
        canonical["device_id"] = None
    else:
        canonical["device_id"] = normalize_uuid(dev, "device_id")

    # 8. direction ('DEBIT' or 'CREDIT', NOT NULL)
    dir_val = raw_row["direction"]
    if not isinstance(dir_val, str):
        raise TypeError(f"Field 'direction' must be str, got {type(dir_val).__name__}")
    norm_dir = unicodedata.normalize("NFC", dir_val)
    if norm_dir not in ("DEBIT", "CREDIT"):
        raise ValueError(
            f"Field 'direction' must be 'DEBIT' or 'CREDIT', got {dir_val!r}"
        )
    canonical["direction"] = norm_dir

    # 9. external_transaction_id (str, NOT NULL, whitespace and case preserved)
    ext_id = raw_row["external_transaction_id"]
    if not isinstance(ext_id, str):
        raise TypeError(
            f"Field 'external_transaction_id' must be str, got {type(ext_id).__name__}"
        )
    norm_ext = unicodedata.normalize("NFC", ext_id)
    if not norm_ext:
        raise ValueError("Field 'external_transaction_id' cannot be empty")
    canonical["external_transaction_id"] = norm_ext

    # 10. location_id (UUID | None)
    loc = raw_row["location_id"]
    if loc is None:
        canonical["location_id"] = None
    else:
        canonical["location_id"] = normalize_uuid(loc, "location_id")

    # 11. merchant_id (UUID | None)
    merch = raw_row["merchant_id"]
    if merch is None:
        canonical["merchant_id"] = None
    else:
        canonical["merchant_id"] = normalize_uuid(merch, "merchant_id")

    # 12. occurred_at (aware datetime, NOT NULL)
    canonical["occurred_at"] = normalize_timestamp(
        raw_row["occurred_at"], "occurred_at"
    )

    # 13. payment_method (str | None)
    pm = raw_row["payment_method"]
    if pm is None:
        canonical["payment_method"] = None
    elif isinstance(pm, str):
        canonical["payment_method"] = unicodedata.normalize("NFC", pm)
    else:
        raise TypeError(
            f"Field 'payment_method' must be a str or None, got {type(pm).__name__}"
        )

    # 14. source_namespace (uppercase alphanumeric + underscore, NOT NULL)
    ns = raw_row["source_namespace"]
    if not isinstance(ns, str):
        raise TypeError(
            f"Field 'source_namespace' must be str, got {type(ns).__name__}"
        )
    norm_ns = unicodedata.normalize("NFC", ns)
    if not NAMESPACE_REGEX.match(norm_ns):
        raise ValueError(
            f"Field 'source_namespace' must match '^[A-Z0-9_]{{1,64}}$', got {ns!r}"
        )
    canonical["source_namespace"] = norm_ns

    # 15. transaction_type (uppercase alphanumeric + underscore, NOT NULL)
    tt = raw_row["transaction_type"]
    if not isinstance(tt, str):
        raise TypeError(
            f"Field 'transaction_type' must be str, got {type(tt).__name__}"
        )
    norm_tt = unicodedata.normalize("NFC", tt)
    if not TRANSACTION_TYPE_REGEX.match(norm_tt):
        raise ValueError(
            f"Field 'transaction_type' must match '^[A-Z0-9_]{{1,32}}$', got {tt!r}"
        )
    canonical["transaction_type"] = norm_tt

    return canonical


def serialize_canonical_row_json(canonical_payload: dict[str, Any]) -> str:
    """Serialize the canonical dictionary to single-line JSON with sorted keys."""
    # Ensure all canonical keys are sorted alphabetically
    sorted_dict = {key: canonical_payload[key] for key in CANONICAL_FIELD_KEYS}
    return json.dumps(sorted_dict, separators=(",", ":"), ensure_ascii=False)


def compute_canonical_row_hash(raw_row: dict[str, Any]) -> str:
    """Compute the SHA-256 hex digest of a canonical transaction row."""
    canonical_payload = build_canonical_row_payload(raw_row)
    serialized_json = serialize_canonical_row_json(canonical_payload)
    return hashlib.sha256(serialized_json.encode("utf-8")).hexdigest()
