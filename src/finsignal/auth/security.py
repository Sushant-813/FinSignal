"""Cryptographic security primitives for password hashing and JWT access tokens."""

import contextlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import argon2
import argon2.exceptions
import jwt
import jwt.exceptions

from finsignal.common.exceptions import AuthenticationError
from finsignal.core.config import Settings

logger = logging.getLogger("finsignal.security")

# Reusable module-level Argon2id password hasher with OWASP-recommended parameters
_PASSWORD_HASHER = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=argon2.Type.ID,
)

# Ephemeral secret token used strictly to initialize the static dummy hash on module load.
# The dummy password is an unguessable 64-hex token that cannot be used as an application credential.
_DUMMY_ARGON2_HASH = _PASSWORD_HASHER.hash(secrets.token_hex(32))


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id with OWASP-recommended parameters.

    Returns the formatted Argon2id hash string ($argon2id$v=19$m=65536,t=3,p=4$...).
    Plaintext passwords and intermediate values are never logged or stored.
    """
    return _PASSWORD_HASHER.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an encoded Argon2id hash.

    Returns True if the password matches, False on mismatch or corrupted hash.
    Catches specific verification exceptions without exposing details or raising 500 errors.
    """
    try:
        return _PASSWORD_HASHER.verify(hashed_password, plain_password)
    except argon2.exceptions.VerifyMismatchError:
        return False
    except (
        argon2.exceptions.InvalidHashError,
        argon2.exceptions.VerificationError,
    ):
        logger.warning(
            "Attempted password verification against an invalid or malformed hash representation."
        )
        return False


def verify_dummy_password() -> None:
    """Perform dummy Argon2id verification for unknown users to reduce timing differences.

    Note: Dummy verification mitigates timing side-channels between existing and
    non-existent accounts by executing comparable cryptographic work (~50-100ms),
    but does NOT guarantee mathematically constant-time HTTP responses due to
    underlying system scheduling, database query latency, and network variance.
    """
    with contextlib.suppress(argon2.exceptions.VerificationError):
        # Intentionally mismatch with a non-matching candidate to trigger standard verification failure
        _PASSWORD_HASHER.verify(_DUMMY_ARGON2_HASH, "mismatched-candidate-sentinel")


def create_access_token(
    user_id: uuid.UUID,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a signed JWT access token using the user's UUID and configured HS256 key.

    Claims included:
    - `sub`: Canonical string representation of the user's UUID.
    - `iat`: UTC epoch timestamp of issuance.
    - `exp`: UTC epoch timestamp of expiration (default 30 minutes).

    Per approved architecture, neither role nor email claims are stored in the token;
    authorization evaluates the authoritative, current role from the database.
    Tokens do not include `jti` as no revocation mechanism is enabled in this phase.
    """
    now = datetime.now(UTC)
    delta = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    iat = int(now.timestamp())
    exp = int((now + delta).timestamp())

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": iat,
        "exp": exp,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_access_token(
    token: str,
    settings: Settings,
) -> dict[str, Any]:
    """Decode and validate a JWT access token, returning the validated payload dictionary.

    Validation rules:
    - Explicitly restricted to HS256 algorithm (disallowing 'none' or unexpected algorithms).
    - Requires 'sub', 'iat', and 'exp' claims.
    - Validates expiration and issued-at timestamps.
    - Validates that 'sub' is a valid canonical UUID string.
    - Catches all PyJWT validation failures and translates them into client-safe AuthenticationError.
    - Does not leak raw tokens, secrets, or internal PyJWT exception structures.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={
                "require": ["sub", "iat", "exp"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
            },
        )
    except jwt.exceptions.ExpiredSignatureError as err:
        raise AuthenticationError(
            message="Token has expired.",
            code="UNAUTHORIZED",
        ) from err
    except (
        jwt.exceptions.InvalidSignatureError,
        jwt.exceptions.InvalidAlgorithmError,
        jwt.exceptions.DecodeError,
        jwt.exceptions.MissingRequiredClaimError,
        jwt.exceptions.InvalidIssuedAtError,
        jwt.exceptions.ImmatureSignatureError,
        jwt.exceptions.InvalidTokenError,
    ) as err:
        raise AuthenticationError(
            message="Token is invalid or malformed.",
            code="UNAUTHORIZED",
        ) from err

    # Validate subject format
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise AuthenticationError(
            message="Token subject must be a valid canonical UUID string.",
            code="UNAUTHORIZED",
        )
    try:
        user_uuid = uuid.UUID(sub)
        if str(user_uuid) != sub:
            raise ValueError("Non-canonical UUID representation")
    except (ValueError, TypeError, AttributeError) as err:
        raise AuthenticationError(
            message="Token subject must be a valid canonical UUID string.",
            code="UNAUTHORIZED",
        ) from err

    # Validate claim types and logical consistency
    iat = payload.get("iat")
    exp = payload.get("exp")
    if (
        isinstance(iat, bool)
        or isinstance(exp, bool)
        or not isinstance(iat, (int, float))
        or not isinstance(exp, (int, float))
    ):
        raise AuthenticationError(
            message="Token timestamp claims must be valid epoch numbers.",
            code="UNAUTHORIZED",
        )
    if iat > exp:
        raise AuthenticationError(
            message="Token issuance timestamp cannot be after expiration timestamp.",
            code="UNAUTHORIZED",
        )

    return payload
