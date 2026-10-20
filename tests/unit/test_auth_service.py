"""Unit tests for AuthService registration and login business logic."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from finsignal.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from finsignal.auth.security import decode_access_token, hash_password
from finsignal.auth.service import AuthService
from finsignal.common.exceptions import AuthenticationError, ConflictError
from finsignal.core.config import Settings
from finsignal.users.models import User
from finsignal.users.repository import UserRepository


@pytest.fixture
def test_auth_settings() -> Settings:
    """Isolated test settings for authentication service tests."""
    return Settings(
        app_name="FinSignalAuthTest",
        environment="testing",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        _env_file=None,
    )


@pytest.mark.asyncio
async def test_register_success(test_auth_settings: Settings) -> None:
    """Verify successful registration hashes password, assigns ANALYST role, and commits."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_email.return_value = None

    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    async def fake_create(session, email, password_hash, role, is_active=True):
        return User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
            created_at=now,
        )

    mock_repo.create.side_effect = fake_create

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = RegisterRequest(
        email="  NEW.ANALYST@Example.COM  ",
        password="SecurePassword123!",
    )

    response = await service.register(mock_session, req)

    # Email normalized
    mock_repo.get_by_email.assert_awaited_once_with(
        mock_session, "new.analyst@example.com"
    )
    # Entity created with explicit role="ANALYST" and active status
    mock_repo.create.assert_awaited_once()
    create_kwargs = mock_repo.create.call_args.kwargs
    assert create_kwargs["email"] == "new.analyst@example.com"
    assert create_kwargs["role"] == "ANALYST"
    assert create_kwargs["is_active"] is True
    # Password hashed with Argon2id, never plaintext
    assert create_kwargs["password_hash"].startswith("$argon2id$")
    assert "SecurePassword123!" not in create_kwargs["password_hash"]

    # Transaction committed
    mock_session.commit.assert_awaited_once()

    # Response is sanitized UserResponse
    assert isinstance(response, UserResponse)
    assert response.id == user_id
    assert response.email == "new.analyst@example.com"
    assert response.role == "ANALYST"
    assert response.is_active is True
    assert response.created_at == now


@pytest.mark.asyncio
async def test_register_duplicate_email_fast_path(test_auth_settings: Settings) -> None:
    """Verify prior lookup catches existing user and raises ConflictError without calling create."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_email.return_value = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        password_hash="somehash",
        role="ANALYST",
    )

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = RegisterRequest(
        email="existing@example.com",
        password="SecurePassword123!",
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.register(mock_session, req)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "STATE_CONFLICT"
    assert "already exists" in exc_info.value.message
    mock_repo.create.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_duplicate_email_race_condition(
    test_auth_settings: Settings,
) -> None:
    """Verify database IntegrityError with structured email unique diagnostic triggers ConflictError."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    # Fast path missed the concurrent insert
    mock_repo.get_by_email.return_value = None

    # Structured driver diagnostic identifying uq_users_email and SQLSTATE 23505
    mock_orig = MagicMock()
    mock_orig.diag.constraint_name = "uq_users_email"
    mock_orig.sqlstate = "23505"

    mock_repo.create.side_effect = IntegrityError(
        statement="INSERT INTO users...",
        params={},
        orig=mock_orig,
    )

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = RegisterRequest(
        email="race.user@example.com",
        password="SecurePassword123!",
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.register(mock_session, req)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "STATE_CONFLICT"
    assert "already exists" in exc_info.value.message
    # No SQL or constraint names leaked to client
    assert "INSERT" not in exc_info.value.message
    assert "uq_users_email" not in exc_info.value.message

    # Session rolled back to leave it in a recoverable state
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_unrelated_integrity_error_reraised(
    test_auth_settings: Settings,
) -> None:
    """Verify non-email integrity errors (e.g. check constraint) are rolled back and re-raised."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_email.return_value = None

    # Simulate unrelated check constraint failure (chk_users_role) with SQLSTATE 23514
    mock_orig = MagicMock()
    mock_orig.diag.constraint_name = "chk_users_role"
    mock_orig.sqlstate = "23514"
    unrelated_integrity_err = IntegrityError(
        statement="INSERT INTO users...",
        params={},
        orig=mock_orig,
    )
    mock_repo.create.side_effect = unrelated_integrity_err

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = RegisterRequest(
        email="check.violation@example.com",
        password="SecurePassword123!",
    )

    # Must NOT raise ConflictError
    with pytest.raises(IntegrityError) as exc_info:
        await service.register(mock_session, req)

    assert exc_info.value is unrelated_integrity_err
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_missing_or_unknown_constraint_diagnostics_reraised(
    test_auth_settings: Settings,
) -> None:
    """Verify IntegrityError with missing or unknown constraint diagnostics is rolled back and re-raised."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_email.return_value = None

    # Driver exception lacks structured constraint_name (plain Exception or None constraint_name)
    untyped_orig = Exception(
        "some generic database integrity error mentioning uq_users_email"
    )
    untyped_integrity_err = IntegrityError(
        statement="INSERT INTO users...",
        params={},
        orig=untyped_orig,
    )
    mock_repo.create.side_effect = untyped_integrity_err

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = RegisterRequest(
        email="missing.diag@example.com",
        password="SecurePassword123!",
    )

    # Without structured constraint diagnostics, it must NOT guess or translate to ConflictError
    with pytest.raises(IntegrityError) as exc_info:
        await service.register(mock_session, req)

    assert exc_info.value is untyped_integrity_err
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_rollback_failure_preserves_primary_exception(
    test_auth_settings: Settings,
) -> None:
    """Verify failed session rollback preserves primary IntegrityError and records failure."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_email.return_value = None

    mock_orig = MagicMock()
    mock_orig.diag.constraint_name = "uq_users_email"
    mock_orig.sqlstate = "23505"
    integrity_err = IntegrityError(
        statement="INSERT INTO users...",
        params={},
        orig=mock_orig,
    )
    mock_repo.create.side_effect = integrity_err
    mock_session.rollback.side_effect = ConnectionResetError("Database connection lost")

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = RegisterRequest(
        email="race.user@example.com",
        password="SecurePassword123!",
    )

    # The primary IntegrityError must be raised rather than masked by ConflictError
    with pytest.raises(IntegrityError) as exc_info:
        await service.register(mock_session, req)

    assert exc_info.value is integrity_err
    # Verify rollback failure was attached to the exception notes
    notes = getattr(exc_info.value, "__notes__", [])
    assert any("ConnectionResetError" in note for note in notes)


@pytest.mark.asyncio
async def test_register_unexpected_error_rolls_back(
    test_auth_settings: Settings,
) -> None:
    """Verify unexpected database or system exception triggers rollback and is re-raised."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_email.return_value = None
    mock_repo.create.side_effect = RuntimeError("Fatal connection drop")

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = RegisterRequest(
        email="crash.user@example.com",
        password="SecurePassword123!",
    )

    with pytest.raises(RuntimeError, match="Fatal connection drop"):
        await service.register(mock_session, req)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_login_success(test_auth_settings: Settings) -> None:
    """Verify login with correct credentials returns valid TokenResponse."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    user_id = uuid.uuid4()
    plain_pw = "ValidPassword123!"
    pw_hash = hash_password(plain_pw)

    mock_user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash=pw_hash,
        role="ANALYST",
        is_active=True,
    )
    mock_repo.get_by_email.return_value = mock_user

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = LoginRequest(
        email="  ANALYST@Example.COM  ",
        password=plain_pw,
    )

    response = await service.login(mock_session, req)

    assert isinstance(response, TokenResponse)
    assert response.token_type == "bearer"
    assert response.expires_in == 30 * 60  # 1800 seconds

    # Decode and verify the access token claims
    payload = decode_access_token(response.access_token, test_auth_settings)
    assert payload["sub"] == str(user_id)
    assert "iat" in payload
    assert "exp" in payload


@pytest.mark.asyncio
async def test_login_unknown_user_runs_dummy_hash_and_raises(
    test_auth_settings: Settings,
) -> None:
    """Verify unknown user runs dummy Argon2id verification and raises AuthenticationError."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_by_email.return_value = None

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = LoginRequest(
        email="unknown@example.com",
        password="SomePassword123!",
    )

    with patch("finsignal.auth.service.verify_dummy_password") as mock_dummy:
        with pytest.raises(AuthenticationError) as exc_info:
            await service.login(mock_session, req)

        mock_dummy.assert_called_once()

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert exc_info.value.message == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_incorrect_password_raises(test_auth_settings: Settings) -> None:
    """Verify incorrect password raises AuthenticationError."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    user_id = uuid.uuid4()
    pw_hash = hash_password("CorrectPassword123!")

    mock_user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash=pw_hash,
        role="ANALYST",
        is_active=True,
    )
    mock_repo.get_by_email.return_value = mock_user

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = LoginRequest(
        email="analyst@example.com",
        password="WrongPassword123!",
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await service.login(mock_session, req)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert exc_info.value.message == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_unknown_user_and_bad_password_equivalent_errors(
    test_auth_settings: Settings,
) -> None:
    """Verify unknown user and wrong password raise identical public errors preventing enumeration."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)

    # 1. Unknown user error
    mock_repo.get_by_email.return_value = None
    with pytest.raises(AuthenticationError) as unknown_exc:
        await service.login(mock_session, LoginRequest(email="a@x.com", password="pw1"))

    # 2. Bad password error
    mock_repo.get_by_email.return_value = User(
        id=uuid.uuid4(),
        email="b@x.com",
        password_hash=hash_password("RealPassword123!"),
        role="ANALYST",
        is_active=True,
    )
    with pytest.raises(AuthenticationError) as bad_pw_exc:
        await service.login(mock_session, LoginRequest(email="b@x.com", password="pw1"))

    # Assert completely indistinguishable public error structure
    assert unknown_exc.value.status_code == bad_pw_exc.value.status_code == 401
    assert unknown_exc.value.code == bad_pw_exc.value.code == "UNAUTHORIZED"
    assert (
        unknown_exc.value.message
        == bad_pw_exc.value.message
        == "Invalid email or password."
    )
    assert unknown_exc.value.details == bad_pw_exc.value.details == {}


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(test_auth_settings: Settings) -> None:
    """Verify inactive account is rejected even when password is correct."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    user_id = uuid.uuid4()
    plain_pw = "ValidPassword123!"
    pw_hash = hash_password(plain_pw)

    mock_user = User(
        id=user_id,
        email="inactive@example.com",
        password_hash=pw_hash,
        role="ANALYST",
        is_active=False,  # Inactive
    )
    mock_repo.get_by_email.return_value = mock_user

    service = AuthService(user_repo=mock_repo, settings=test_auth_settings)
    req = LoginRequest(
        email="inactive@example.com",
        password=plain_pw,
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await service.login(mock_session, req)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"
    assert "inactive" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_login_configured_expiration_reflected() -> None:
    """Verify token expiration reflects configured setting value."""
    mock_session = AsyncMock()
    mock_repo = AsyncMock(spec=UserRepository)

    custom_settings = Settings(
        app_name="FinSignalCustomExpiry",
        environment="testing",
        access_token_expire_minutes=45,
        _env_file=None,
    )

    user_id = uuid.uuid4()
    pw_hash = hash_password("ValidPassword123!")

    mock_user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash=pw_hash,
        role="ANALYST",
        is_active=True,
    )
    mock_repo.get_by_email.return_value = mock_user

    service = AuthService(user_repo=mock_repo, settings=custom_settings)
    req = LoginRequest(
        email="analyst@example.com",
        password="ValidPassword123!",
    )

    response = await service.login(mock_session, req)

    # 45 minutes = 2700 seconds
    assert response.expires_in == 45 * 60 == 2700
