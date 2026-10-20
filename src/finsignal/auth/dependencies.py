"""FastAPI dependencies for request authentication and role-based access control (RBAC)."""

import uuid
from typing import Annotated, Literal

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.security import decode_access_token
from finsignal.auth.service import AuthService
from finsignal.common.exceptions import AuthenticationError, AuthorizationError
from finsignal.core.config import Settings, get_settings
from finsignal.core.database import get_db_session
from finsignal.users.models import User
from finsignal.users.repository import UserRepository

UserRole = Literal["ADMIN", "ANALYST", "INVESTIGATOR"]
VALID_ROLES: frozenset[str] = frozenset({"ADMIN", "ANALYST", "INVESTIGATOR"})

# HTTPBearer with auto_error=False to allow custom AuthenticationError (HTTP 401)
# rather than default Starlette HTTPException (HTTP 403).
http_bearer = HTTPBearer(auto_error=False)


def get_user_repository() -> UserRepository:
    """Provide a UserRepository instance for dependency injection."""
    return UserRepository()


def get_auth_settings(request: Request) -> Settings:
    """Obtain application settings bound to the current FastAPI application."""
    return getattr(request.app.state, "settings", None) or get_settings()


def get_auth_service(
    settings: Annotated[Settings, Depends(get_auth_settings)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    """Provide an AuthService instance wired with request-scoped settings and repository."""
    return AuthService(user_repo=user_repo, settings=settings)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_auth_settings)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Authenticate incoming request via Bearer JWT and load authoritative User from database.

    Validation steps:
    1. Verify Authorization header is provided with 'Bearer' scheme.
    2. Decode and validate access token signature, expiration, and claims.
    3. Extract and parse canonical UUID subject.
    4. Query database for current User record.
    5. Verify user exists and account is active.

    Does not trust role or email claims from the token; database record is the
    authoritative source of current account status and role.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError(
            message="Authentication credentials were not provided or are invalid.",
            code="UNAUTHORIZED",
        )

    token = credentials.credentials
    # decode_access_token validates signature, expiration, algorithm, and claims,
    # raising AuthenticationError on any token failure.
    payload = decode_access_token(token, settings)

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise AuthenticationError(
            message="Token subject must be a valid canonical UUID string.",
            code="UNAUTHORIZED",
        )

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError, AttributeError):
        raise AuthenticationError(
            message="Token subject must be a valid canonical UUID string.",
            code="UNAUTHORIZED",
        ) from None

    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise AuthenticationError(
            message="User not found or credentials invalid.",
            code="UNAUTHORIZED",
        )

    if not user.is_active:
        raise AuthenticationError(
            message="User account is inactive.",
            code="UNAUTHORIZED",
        )

    return user


class RoleChecker:
    """Dependency callable enforcing that the authenticated user possesses one of the allowed roles."""

    def __init__(self, *allowed_roles: str) -> None:
        if not allowed_roles:
            raise ValueError("At least one allowed role must be specified.")
        invalid_roles = set(allowed_roles) - VALID_ROLES
        if invalid_roles:
            raise ValueError(
                f"Invalid role(s) specified: {sorted(invalid_roles)}. "
                f"Must be a subset of {sorted(VALID_ROLES)}."
            )
        self.allowed_roles = frozenset(allowed_roles)

    def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Verify the database-backed user role against the allowed roles."""
        if current_user.role not in self.allowed_roles:
            raise AuthorizationError(
                message="You do not have permission to perform this action.",
                code="FORBIDDEN",
            )
        return current_user


def require_roles(*allowed_roles: str) -> RoleChecker:
    """Factory returning a RoleChecker dependency for the specified allowed roles."""
    return RoleChecker(*allowed_roles)
