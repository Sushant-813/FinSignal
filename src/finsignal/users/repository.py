"""User domain repository for database access."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.users.models import User


def normalize_email(email: str) -> str:
    """Normalize an email address by stripping surrounding whitespace and lowercasing.

    Preserves all valid characters in the local part while guaranteeing
    consistent case-insensitive representation across database storage and queries.
    """
    return email.strip().lower()


class UserRepository:
    """Repository handling asynchronous persistence and lookup for User entities."""

    async def get_by_id(self, session: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Retrieve a user by their UUID primary key."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Retrieve a user by their normalized email address.

        Uses exact equality against the normalized email to leverage the
        unique index `ix_users_email` without requiring functional indexes.
        """
        normalized = normalize_email(email)
        stmt = select(User).where(User.email == normalized)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        session: AsyncSession,
        email: str,
        password_hash: str,
        role: str,
        is_active: bool = True,
    ) -> User:
        """Instantiate and persist a new User record.

        Flushes to the database to populate database defaults (e.g., id, created_at)
        and surface integrity constraint violations immediately, without committing
        the transaction. Transaction commit/rollback is managed by the service boundary.
        """
        normalized_email = normalize_email(email)
        user = User(
            email=normalized_email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        session.add(user)
        await session.flush()
        return user
