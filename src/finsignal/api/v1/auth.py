"""Authentication API v1 router and endpoint handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.dependencies import get_auth_service, get_current_user
from finsignal.auth.limiter import (
    LoginRateLimiter,
    default_login_rate_limiter,
    get_login_rate_limiter,
)
from finsignal.auth.schemas import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from finsignal.auth.service import AuthService
from finsignal.common.exceptions import AuthenticationError, RateLimitError
from finsignal.core.database import get_db_session
from finsignal.users.models import User
from finsignal.users.repository import normalize_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    request: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Register a new user account with role 'ANALYST'.

    Validates password complexity (strictly 12-128 characters), normalizes email
    address, hashes password with Argon2id, and persists the user record.
    Client-supplied roles are strictly rejected by the schema contract.
    """
    return await auth_service.register(session=session, request=request)


_DUMMY_REQUEST = Request({"type": "http", "client": ("127.0.0.1", 12345)})


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue access token",
)
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    raw_request: Request = _DUMMY_REQUEST,
    rate_limiter: Annotated[
        LoginRateLimiter, Depends(get_login_rate_limiter)
    ] = default_login_rate_limiter,
) -> TokenResponse:
    """Authenticate email and password credentials, returning a signed JWT access token.

    Uses Argon2id password verification and dummy hash verification for non-existent
    users to defend against timing attacks. Inactive accounts are rejected.
    Enforces in-memory sliding-window rate limiting (SEC-06) to defend against brute force attacks.
    """
    limiter = rate_limiter or default_login_rate_limiter
    client_ip = (
        raw_request.client.host if raw_request and raw_request.client else "unknown"
    )
    normalized_email = normalize_email(request.email)
    rate_key = f"{client_ip}:{normalized_email}"

    # 1. Acquire admission reservation (prevents check-then-record race across concurrent requests)
    status_check = limiter.acquire(rate_key)
    if not status_check.allowed:
        raise RateLimitError(
            retry_after=status_check.retry_after,
            details={"retry_after_seconds": status_check.retry_after},
        )

    # 2. Attempt credential verification with guaranteed reservation lifecycle handling
    auth_success = False
    auth_failed = False
    try:
        token_resp = await auth_service.login(session=session, request=request)
        auth_success = True
        return token_resp
    except AuthenticationError:
        auth_failed = True
        limiter.record_failure(rate_key)
        raise
    finally:
        if auth_success:
            limiter.record_success(rate_key)
        elif not auth_failed:
            # Unexpected exception (e.g. database error, cancellation)
            limiter.release_reservation(rate_key)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Retrieve identity and permissions for the currently authenticated user.

    The user is authoritatively resolved from PostgreSQL using the database session.
    Returns only client-safe public user fields.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Stateless user logout",
)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
) -> LogoutResponse:
    """Acknowledge client logout under the stateless JWT architecture.

    Requires an authenticated active user. Under FinSignal's stateless JWT design,
    the server does not maintain server-side session state or token revocation lists.
    The client is responsible for discarding its stored access token.
    """
    return LogoutResponse(message="Successfully logged out.")
