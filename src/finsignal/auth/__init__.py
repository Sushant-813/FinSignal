"""Authentication domain package for FinSignal."""

from finsignal.auth.dependencies import (
    VALID_ROLES,
    RoleChecker,
    get_auth_service,
    get_current_user,
    require_roles,
)
from finsignal.auth.schemas import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from finsignal.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from finsignal.auth.service import AuthService

__all__ = [
    "AuthService",
    "LoginRequest",
    "LogoutResponse",
    "RegisterRequest",
    "RoleChecker",
    "TokenResponse",
    "UserResponse",
    "VALID_ROLES",
    "create_access_token",
    "decode_access_token",
    "get_auth_service",
    "get_current_user",
    "hash_password",
    "require_roles",
    "verify_dummy_password",
    "verify_password",
]
