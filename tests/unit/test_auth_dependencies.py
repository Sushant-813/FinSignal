"""Unit tests for FastAPI authentication dependencies and RBAC role checkers."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from finsignal.auth.dependencies import (
    RoleChecker,
    get_current_user,
    require_roles,
)
from finsignal.auth.security import create_access_token
from finsignal.common.exceptions import AuthenticationError, AuthorizationError
from finsignal.core.config import Settings
from finsignal.users.models import User
from finsignal.users.repository import UserRepository


@pytest.fixture
def test_settings() -> Settings:
    """Isolated test settings with dedicated JWT key."""
    return Settings(
        app_name="FinSignalDepTest",
        environment="testing",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        _env_file=None,
    )


@pytest.mark.asyncio
async def test_get_current_user_valid(test_settings: Settings) -> None:
    """Verify get_current_user extracts user_id from valid token and loads user from repository."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, settings=test_settings)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    mock_user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash="argon2id_hash",
        role="ANALYST",
        is_active=True,
    )
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = mock_user

    current_user = await get_current_user(
        credentials=credentials,
        session=mock_session,
        settings=test_settings,
        user_repo=mock_repo,
    )

    assert current_user is mock_user
    assert current_user.id == user_id
    assert current_user.role == "ANALYST"
    assert current_user.is_active is True
    mock_repo.get_by_id.assert_awaited_once_with(mock_session, user_id)


@pytest.mark.asyncio
async def test_get_current_user_missing_credentials(test_settings: Settings) -> None:
    """Verify get_current_user raises AuthenticationError when no credentials are provided."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=None,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "credentials were not provided" in exc_info.value.message


@pytest.mark.asyncio
async def test_get_current_user_non_bearer_scheme(test_settings: Settings) -> None:
    """Verify get_current_user raises AuthenticationError for non-Bearer schemes."""
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="some_token")
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_current_user_expired_token(test_settings: Settings) -> None:
    """Verify get_current_user raises AuthenticationError for expired JWT."""
    user_id = uuid.uuid4()
    # Create expired token (-5 minutes)
    expired_token = create_access_token(
        user_id=user_id,
        settings=test_settings,
        expires_delta=timedelta(minutes=-5),
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=expired_token
    )
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "expired" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(test_settings: Settings) -> None:
    """Verify get_current_user raises AuthenticationError for malformed or tampered token."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="invalid.token.structure"
    )
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_current_user_token_with_malformed_uuid_sub(
    test_settings: Settings,
) -> None:
    """Verify tokens containing a malformed UUID sub string are rejected with HTTP 401."""
    now = datetime.now(UTC)
    payload = {
        "sub": "not-a-valid-uuid-string",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    raw_token = jwt.encode(
        payload,
        test_settings.jwt_secret_key.get_secret_value(),
        algorithm=test_settings.jwt_algorithm,
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_token)
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "uuid" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_user_token_with_non_string_sub(
    test_settings: Settings,
) -> None:
    """Verify tokens containing a non-string sub claim are rejected with HTTP 401."""
    now = datetime.now(UTC)
    payload = {
        "sub": 123456,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    raw_token = jwt.encode(
        payload,
        test_settings.jwt_secret_key.get_secret_value(),
        algorithm=test_settings.jwt_algorithm,
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_token)
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "invalid" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_user_token_missing_sub(
    test_settings: Settings,
) -> None:
    """Verify tokens missing the sub claim entirely are rejected with HTTP 401."""
    now = datetime.now(UTC)
    payload = {
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    raw_token = jwt.encode(
        payload,
        test_settings.jwt_secret_key.get_secret_value(),
        algorithm=test_settings.jwt_algorithm,
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_token)
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("bad_payload", "expected_snippet"),
    [
        ({"sub": "invalid-uuid-syntax"}, "uuid"),
        ({"sub": 98765}, "uuid"),
        ({"sub": None}, "uuid"),
        ({"sub": ""}, "uuid"),
        ({}, "uuid"),
    ],
)
async def test_get_current_user_dependency_handles_bad_decoded_payload_safely(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
    bad_payload: dict[str, Any],
    expected_snippet: str,
) -> None:
    """Verify dependency defense-in-depth: if decode returns malformed/non-string/missing sub, fail with 401."""
    monkeypatch.setattr(
        "finsignal.auth.dependencies.decode_access_token",
        lambda token, settings: bad_payload,
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="any.valid.signature"
    )
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert expected_snippet in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(test_settings: Settings) -> None:
    """Verify get_current_user raises AuthenticationError when user does not exist in DB."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, settings=test_settings)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = None  # User deleted or missing

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "not found" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(test_settings: Settings) -> None:
    """Verify get_current_user raises AuthenticationError when user account is inactive."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, settings=test_settings)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    mock_user = User(
        id=user_id,
        email="inactive@example.com",
        password_hash="hash",
        role="ANALYST",
        is_active=False,  # Inactive
    )
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_id.return_value = mock_user

    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_user(
            credentials=credentials,
            session=mock_session,
            settings=test_settings,
            user_repo=mock_repo,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "inactive" in exc_info.value.message.lower()


def test_role_checker_validation_on_init() -> None:
    """Verify RoleChecker validates allowed roles at initialization time."""
    # Empty roles rejected
    with pytest.raises(ValueError, match="At least one allowed role"):
        RoleChecker()

    # Invalid role typo rejected
    with pytest.raises(ValueError, match="Invalid role"):
        RoleChecker("ADMIN", "INVALID_ROLE")


def test_role_checker_accepted_role() -> None:
    """Verify RoleChecker returns User when user possesses one of the allowed roles."""
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash="hash",
        role="ADMIN",
        is_active=True,
    )
    checker = require_roles("ADMIN", "INVESTIGATOR")
    result = checker(current_user=user)
    assert result is user


def test_role_checker_disallowed_role() -> None:
    """Verify RoleChecker raises AuthorizationError when user lacks allowed roles."""
    user = User(
        id=uuid.uuid4(),
        email="analyst@example.com",
        password_hash="hash",
        role="ANALYST",
        is_active=True,
    )
    checker = require_roles("ADMIN", "INVESTIGATOR")

    with pytest.raises(AuthorizationError) as exc_info:
        checker(current_user=user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"
    assert "permission" in exc_info.value.message.lower()


def test_role_checker_all_canonical_roles() -> None:
    """Verify each canonical role (ADMIN, ANALYST, INVESTIGATOR) can be enforced."""
    for role in ["ADMIN", "ANALYST", "INVESTIGATOR"]:
        user = User(
            id=uuid.uuid4(),
            email=f"{role.lower()}@example.com",
            password_hash="hash",
            role=role,
            is_active=True,
        )
        # Checking with exact role
        checker = require_roles(role)
        assert checker(current_user=user) is user

        # Checking with other roles fails
        other_roles = [r for r in ["ADMIN", "ANALYST", "INVESTIGATOR"] if r != role]
        other_checker = require_roles(*other_roles)
        with pytest.raises(AuthorizationError) as exc_info:
            other_checker(current_user=user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "FORBIDDEN"
