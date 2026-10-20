"""Unit tests for UserRepository operations and transaction isolation."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from finsignal.users.models import User
from finsignal.users.repository import UserRepository, normalize_email


def test_normalize_email() -> None:
    """Verify email normalization handles whitespace and case folding."""
    assert normalize_email("   USER@DOMAIN.COM   ") == "user@domain.com"
    assert (
        normalize_email("user.name+tag@sub.example.com")
        == "user.name+tag@sub.example.com"
    )
    assert normalize_email("  MixedCase@Example.Org ") == "mixedcase@example.org"


@pytest.mark.asyncio
async def test_get_by_id_found() -> None:
    """Verify get_by_id executes select query and returns matched user without committing."""
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="analyst@example.com",
        password_hash="hashed_pw",
        role="ANALYST",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    repo = UserRepository()
    result = await repo.get_by_id(mock_session, user_id)

    assert result is mock_user
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_id_not_found() -> None:
    """Verify get_by_id returns None when user does not exist."""
    user_id = uuid.uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    repo = UserRepository()
    result = await repo.get_by_id(mock_session, user_id)

    assert result is None
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_email_normalizes_and_queries() -> None:
    """Verify get_by_email normalizes email before querying and never commits."""
    mock_user = User(
        id=uuid.uuid4(),
        email="analyst@example.com",
        password_hash="hashed_pw",
        role="ANALYST",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    repo = UserRepository()
    result = await repo.get_by_email(mock_session, "  ANALYST@Example.COM  ")

    assert result is mock_user
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_email_not_found() -> None:
    """Verify get_by_email returns None when email is not registered."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    repo = UserRepository()
    result = await repo.get_by_email(mock_session, "missing@example.com")

    assert result is None
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_adds_user_and_flushes_without_committing() -> None:
    """Verify create adds entity, flushes to surface constraints, and leaves commit to caller."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    repo = UserRepository()
    user = await repo.create(
        session=mock_session,
        email="  NEW_USER@Domain.COM  ",
        password_hash="argon2id_hash_val",
        role="INVESTIGATOR",
        is_active=True,
    )

    assert isinstance(user, User)
    assert user.email == "new_user@domain.com"
    assert user.password_hash == "argon2id_hash_val"
    assert user.role == "INVESTIGATOR"
    assert user.is_active is True

    mock_session.add.assert_called_once_with(user)
    mock_session.flush.assert_awaited_once()
    # Transaction ownership MUST remain outside the repository
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_default_is_active_true() -> None:
    """Verify create defaults is_active to True when not specified."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    repo = UserRepository()
    user = await repo.create(
        session=mock_session,
        email="analyst@domain.com",
        password_hash="argon2id_hash_val",
        role="ANALYST",
    )

    assert user.is_active is True
    mock_session.add.assert_called_once_with(user)
    mock_session.flush.assert_awaited_once()
    mock_session.commit.assert_not_called()
