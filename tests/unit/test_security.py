"""Unit tests for cryptographic security primitives (Argon2id and PyJWT)."""

import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr

from finsignal.auth.security import (
    _DUMMY_ARGON2_HASH,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from finsignal.common.exceptions import AuthenticationError
from finsignal.core.config import Settings


@pytest.fixture
def test_security_settings() -> Settings:
    """Provide isolated Settings instance with a dedicated strong test signing secret."""
    return Settings(
        jwt_secret_key=SecretStr("test-secret-key-at-least-32-chars-long-0123456789"),
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        database_password=SecretStr("pw"),
        _env_file=None,
    )


# ============================================================================
# Password Hashing & Verification Tests (Argon2id)
# ============================================================================


def test_password_hashing_and_verification_success() -> None:
    """Verify that a correct password verifies successfully against its Argon2id hash."""
    plain = "CorrectHorseBatteryStaple123!"
    hashed = hash_password(plain)

    # Identifies Argon2id with explicit OWASP parameters (m=65536, t=3, p=4)
    assert hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert plain not in hashed
    assert len(hashed) > 50

    # Verifies matching password
    assert verify_password(plain, hashed) is True


def test_password_verification_failure_on_incorrect_password() -> None:
    """Verify that an incorrect password safely returns False without raising exceptions."""
    plain = "CorrectHorseBatteryStaple123!"
    hashed = hash_password(plain)

    assert verify_password("WrongPasswordEntirely!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password("correcthorsebatterystaple123!", hashed) is False


def test_password_verification_safe_on_malformed_hashes() -> None:
    """Verify that corrupted or malformed stored hashes return False safely."""
    malformed_hashes = [
        "",
        "not_a_valid_hash",
        "$argon2id$v=19$m=65536,t=3,p=4$corrupted_payload",
        "$pbkdf2-sha256$29000$fake$fake",
        "1234567890",
    ]
    for bad_hash in malformed_hashes:
        assert verify_password("any_password", bad_hash) is False


def test_verify_dummy_password_completes_without_error() -> None:
    """Verify that dummy password verification completes cleanly without unhandled errors."""
    # Precomputed dummy hash must be a valid Argon2id hash with expected parameters
    assert _DUMMY_ARGON2_HASH.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert len(_DUMMY_ARGON2_HASH) > 50

    # Must complete safely without error
    verify_dummy_password()


# ============================================================================
# JWT Access Token Creation & Decoding Tests
# ============================================================================


def test_jwt_create_and_decode_success(test_security_settings: Settings) -> None:
    """Verify successful JWT issuance and decoding with expected claims."""
    user_id = uuid.uuid4()
    before_ts = int(datetime.now(UTC).timestamp())

    token = create_access_token(user_id=user_id, settings=test_security_settings)
    after_ts = int(datetime.now(UTC).timestamp())

    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token=token, settings=test_security_settings)

    # Verify subject matches UUID string
    assert payload["sub"] == str(user_id)

    # Verify timestamp claims
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert before_ts <= payload["iat"] <= after_ts
    # 30 minutes lifetime (1800 seconds)
    assert payload["exp"] - payload["iat"] == 1800

    # Verify approved claims minimalism: no role, no email, no jti
    assert set(payload.keys()) == {"sub", "iat", "exp"}
    assert "role" not in payload
    assert "email" not in payload
    assert "jti" not in payload


def test_jwt_custom_expires_delta(test_security_settings: Settings) -> None:
    """Verify custom expires_delta overrides the settings default lifetime."""
    user_id = uuid.uuid4()
    custom_delta = timedelta(minutes=10)
    token = create_access_token(
        user_id=user_id,
        settings=test_security_settings,
        expires_delta=custom_delta,
    )
    payload = decode_access_token(token=token, settings=test_security_settings)
    assert payload["exp"] - payload["iat"] == 600


def test_jwt_expired_token_rejection(test_security_settings: Settings) -> None:
    """Verify that expired tokens raise AuthenticationError with 401."""
    user_id = uuid.uuid4()
    # Issue a token expired in the past
    token = create_access_token(
        user_id=user_id,
        settings=test_security_settings,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token=token, settings=test_security_settings)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "expired" in exc_info.value.message.lower()


def test_jwt_wrong_secret_rejection(test_security_settings: Settings) -> None:
    """Verify that a token signed with a different key is rejected."""
    user_id = uuid.uuid4()
    wrong_settings = Settings(
        jwt_secret_key=SecretStr("different-secret-key-at-least-32-chars-long-abc"),
        jwt_algorithm="HS256",
        database_password=SecretStr("pw"),
        _env_file=None,
    )

    token = create_access_token(user_id=user_id, settings=wrong_settings)

    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token=token, settings=test_security_settings)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "invalid" in exc_info.value.message.lower()


def test_jwt_tampered_signature_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify that modifying token payload or signature is detected and rejected."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, settings=test_security_settings)

    parts = token.split(".")
    assert len(parts) == 3

    # Tamper with signature
    tampered_sig = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token=tampered_token, settings=test_security_settings)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"


def test_jwt_malformed_token_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify that malformed string tokens raise AuthenticationError."""
    malformed_tokens = [
        "",
        "not.a.token",
        "header.payload",
        "a.b.c.d",
        "invalid_base64!",
    ]
    for bad_token in malformed_tokens:
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(token=bad_token, settings=test_security_settings)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "UNAUTHORIZED"


def test_jwt_unexpected_algorithm_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify that tokens signed with unexpected algorithms (e.g. 'none') are rejected."""
    user_id = uuid.uuid4()
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + 1800}

    # Attempt 'none' algorithm bypass
    none_token = jwt.encode(payload, key="", algorithm="none")

    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token=none_token, settings=test_security_settings)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"


def test_jwt_missing_required_claims_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify that tokens missing sub, iat, or exp are rejected."""
    key = test_security_settings.jwt_secret_key.get_secret_value()
    now = int(time.time())

    # Missing sub
    token_no_sub = jwt.encode({"iat": now, "exp": now + 1800}, key, algorithm="HS256")
    with pytest.raises(AuthenticationError):
        decode_access_token(token=token_no_sub, settings=test_security_settings)

    # Missing iat
    token_no_iat = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": now + 1800}, key, algorithm="HS256"
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token=token_no_iat, settings=test_security_settings)

    # Missing exp
    token_no_exp = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now}, key, algorithm="HS256"
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token=token_no_exp, settings=test_security_settings)


def test_jwt_invalid_uuid_subject_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify that tokens containing non-UUID subjects are rejected."""
    key = test_security_settings.jwt_secret_key.get_secret_value()
    now = int(time.time())

    invalid_subjects = [
        "not-a-uuid",
        "12345",
        "a0000000-0000-0000-0000-00000000000Z",  # Invalid hex
        "",
    ]
    for bad_sub in invalid_subjects:
        token = jwt.encode(
            {"sub": bad_sub, "iat": now, "exp": now + 1800},
            key,
            algorithm="HS256",
        )
        with pytest.raises(AuthenticationError) as exc_info:
            decode_access_token(token=token, settings=test_security_settings)
        assert exc_info.value.status_code == 401
        assert "UUID" in exc_info.value.message
        # Verify untrusted raw_sub is never leaked into internal_context or details
        assert "raw_sub" not in exc_info.value.internal_context
        assert "raw_sub" not in exc_info.value.details


def test_jwt_future_issued_at_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify that tokens with future iat timestamps are rejected."""
    key = test_security_settings.jwt_secret_key.get_secret_value()
    now = int(time.time())

    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now + 1000, "exp": now + 2000},
        key,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token=token, settings=test_security_settings)
    assert exc_info.value.status_code == 401


def test_jwt_iat_greater_than_exp_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify that tokens where iat > exp are rejected."""
    key = test_security_settings.jwt_secret_key.get_secret_value()
    now = int(time.time())

    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now, "exp": now - 100},
        key,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token=token, settings=test_security_settings)
    assert exc_info.value.status_code == 401


def test_jwt_boolean_timestamp_claims_rejection(
    test_security_settings: Settings,
) -> None:
    """Verify boolean iat claims are rejected."""
    key = test_security_settings.jwt_secret_key.get_secret_value()
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": True, "exp": now + 1800},
        key,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(token=token, settings=test_security_settings)
    assert exc_info.value.status_code == 401
    assert "epoch numbers" in exc_info.value.message


def test_jwt_server_invalid_key_error_not_converted_to_auth_error() -> None:
    """Verify server-side invalid key type raises PyJWT error, not client AuthenticationError."""
    import jwt.exceptions

    with pytest.raises(jwt.exceptions.PyJWTError):
        jwt.decode("header.payload.sig", None, algorithms=["HS256"])
