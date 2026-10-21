"""Deterministic random stream derivation and PRNG isolation (ADR-029, ADR-065)."""

import hashlib
import random


def derive_seed(master_seed: int, *domain_keys: str | int) -> int:
    """Derive an independent, deterministic 64-bit unsigned integer seed from a master seed and keys.

    Uses SHA-256 over an unambiguous UTF-8 representation to guarantee:
    1. Independent random streams for distinct entity domains or partitions.
    2. Zero interference across entity generators (e.g. changing merchant count does not alter accounts).
    3. Architecture- and platform-independent reproducibility.
    """
    key_payload = ":".join(str(k) for k in domain_keys)
    digest = hashlib.sha256(f"{master_seed}:{key_payload}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def get_entity_rng(
    master_seed: int,
    entity_type: str,
    index: int,
    generator_version: str,
) -> random.Random:
    """Construct an isolated PRNG instance for a specific entity index.

    Per-entity isolation guarantees progressive scale stability: generating entity N
    produces the exact same attributes regardless of total collection scale.
    """
    stream_seed = derive_seed(master_seed, generator_version, entity_type, index)
    return random.Random(stream_seed)


def get_domain_rng(
    master_seed: int,
    domain: str,
    generator_version: str,
) -> random.Random:
    """Construct an isolated PRNG instance for a domain-level sequence."""
    stream_seed = derive_seed(master_seed, generator_version, domain)
    return random.Random(stream_seed)
