"""Deterministic canonical feature fingerprinting for immutable analysis identity."""

import hashlib
import json
from typing import Any

from finsignal.features.schemas import EvaluatedTransactionDTO, FeatureVector
from finsignal.ml.constants import CANONICAL_FEATURE_NAMES


def compute_feature_fingerprint(
    features: FeatureVector,
    evaluated_tx: EvaluatedTransactionDTO,
) -> str:
    """Compute a deterministic 64-character SHA-256 fingerprint of all result-affecting inputs.

    Inputs included:
    - All 34 canonical numeric features in fixed order.
    - Result-affecting transaction context: amount, currency, direction, merchant_id,
      device_id, location_id, category.

    Guarantees:
    - Deterministic across platforms and execution environments.
    - Excludes non-deterministic or ephemeral values (request IDs, wall-clock timestamps).
    - Produces bitwise identical digests for identical input states.
    """
    payload: dict[str, Any] = {}

    # 1. 34 Canonical Features
    feat_dict = features.model_dump()
    for name in CANONICAL_FEATURE_NAMES:
        val = feat_dict[name]
        if isinstance(val, float):
            payload[f"f_{name}"] = f"{val:.6f}"
        else:
            payload[f"f_{name}"] = str(val)

    # 2. Contextual Transaction Attributes
    payload["ctx_amount"] = str(evaluated_tx.amount)
    payload["ctx_currency"] = evaluated_tx.currency
    payload["ctx_direction"] = evaluated_tx.direction
    payload["ctx_device_id"] = (
        str(evaluated_tx.device_id) if evaluated_tx.device_id else "null"
    )
    payload["ctx_merchant_id"] = (
        str(evaluated_tx.merchant_id) if evaluated_tx.merchant_id else "null"
    )
    payload["ctx_location_id"] = (
        str(evaluated_tx.location_id) if evaluated_tx.location_id else "null"
    )
    payload["ctx_category"] = evaluated_tx.category if evaluated_tx.category else "null"

    # Canonical sorted JSON string
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
