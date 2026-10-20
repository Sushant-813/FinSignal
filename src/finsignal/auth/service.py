"""Authentication domain service for user registration and credential verification."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from finsignal.auth.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from finsignal.common.exceptions import AuthenticationError, ConflictError
from finsignal.core.config import Settings, get_settings
from finsignal.users.repository import UserRepository, normalize_email

logger = logging.getLogger("finsignal.auth")


def _is_email_unique_violation(exc: IntegrityError) -> bool:
    """Determine whether an IntegrityError specifically represents an email uniqueness conflict.

    Inspects PostgreSQL driver diagnostics (sqlstate and constraint_name) across both
    asyncpg and psycopg. Returns True strictly when structured diagnostics positively identify
    an expected email unique constraint ('uq_users_email' or 'ix_users_email') and the SQLSTATE
    (where available) matches PostgreSQL unique_violation ('23505').
    """
    orig = getattr(exc, "orig", None)

    # 1. Inspect SQLSTATE: must match 23505 when present
    sqlstate = (
        getattr(orig, "sqlstate", None)
        or getattr(orig, "pgcode", None)
        or getattr(exc, "sqlstate", None)
    )
    if sqlstate is not None and str(sqlstate) != "23505":
        return False

    # 2. Extract constraint_name strictly from structured driver diagnostics
    # - asyncpg exposes constraint_name on __cause__ (asyncpg.PostgresError) or the DBAPI adapter
    # - psycopg exposes constraint_name on orig.diag (Diagnostic object)
    diag = getattr(orig, "diag", None)
    cause = getattr(orig, "__cause__", None)
    constraint_name = (
        getattr(diag, "constraint_name", None)
        or getattr(cause, "constraint_name", None)
        or getattr(orig, "constraint_name", None)
    )

    if not constraint_name or not isinstance(constraint_name, str):
        return False

    return constraint_name in ("uq_users_email", "ix_users_email")


async def _safe_rollback(
    session: AsyncSession, primary_exc: BaseException
) -> Exception | None:
    """Attempt session rollback, logging and recording any failure without masking primary_exc.

    Preserves primary_exc as the primary exception while ensuring rollback failures
    remain diagnosable in server logs without exposing credentials.
    Returns the rollback exception if one occurred, otherwise None.
    """
    try:
        await session.rollback()
        return None
    except Exception as rollback_err:
        logger.error(
            "Session rollback failed following %s: %s",
            primary_exc.__class__.__name__,
            rollback_err.__class__.__name__,
        )
        if hasattr(primary_exc, "add_note"):
            primary_exc.add_note(
                f"Session rollback failed: {rollback_err.__class__.__name__}: {rollback_err}"
            )
        return rollback_err


class AuthService:
    """Service orchestrating user registration, credential verification, and token issuance."""

    def __init__(
        self,
        user_repo: UserRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.user_repo = user_repo or UserRepository()
        self.settings = settings or get_settings()

    async def register(
        self,
        session: AsyncSession,
        request: RegisterRequest,
    ) -> UserResponse:
        """Register a new user account with role='ANALYST'.

        Hashes password using Argon2id, normalizes email, and handles duplicate-email
        database constraint violations by translating them to client-safe ConflictError.
        Commits on success; rolls back on failure to leave session in a recoverable state.
        """
        normalized_email = normalize_email(str(request.email))

        # Check existing email early to avoid unnecessary hashing work
        existing_user = await self.user_repo.get_by_email(session, normalized_email)
        if existing_user is not None:
            raise ConflictError(
                message="A user with this email address already exists.",
                code="STATE_CONFLICT",
            )

        password_hash = hash_password(request.password)

        try:
            user = await self.user_repo.create(
                session=session,
                email=normalized_email,
                password_hash=password_hash,
                role="ANALYST",
                is_active=True,
            )
            await session.commit()
        except IntegrityError as exc:
            rollback_err = await _safe_rollback(session, exc)
            if rollback_err is None and _is_email_unique_violation(exc):
                raise ConflictError(
                    message="A user with this email address already exists.",
                    code="STATE_CONFLICT",
                ) from None
            # Re-raise primary exception if rollback failed or constraint is unrelated
            raise exc
        except Exception as exc:
            await _safe_rollback(session, exc)
            raise

        return UserResponse.model_validate(user)

    async def login(
        self,
        session: AsyncSession,
        request: LoginRequest,
    ) -> TokenResponse:
        """Authenticate user credentials and return a signed JWT TokenResponse.

        Performs dummy verification for unknown users to mitigate timing attacks.
        Rejects inactive users even if the password matches.
        Returns a TokenResponse with expires_in matching configured expiration window.
        """
        normalized_email = normalize_email(str(request.email))
        user = await self.user_repo.get_by_email(session, normalized_email)

        if user is None:
            verify_dummy_password()
            raise AuthenticationError(
                message="Invalid email or password.",
                code="UNAUTHORIZED",
            )

        if not verify_password(request.password, user.password_hash):
            raise AuthenticationError(
                message="Invalid email or password.",
                code="UNAUTHORIZED",
            )

        if not user.is_active:
            raise AuthenticationError(
                message="User account is inactive.",
                code="UNAUTHORIZED",
            )

        token = create_access_token(
            user_id=user.id,
            settings=self.settings,
        )
        expires_in_seconds = self.settings.access_token_expire_minutes * 60

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in_seconds,
        )
