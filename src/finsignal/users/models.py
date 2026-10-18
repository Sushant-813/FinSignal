"""User domain persistence models."""

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from finsignal.common.models import UpdatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class User(Base, UUIDPrimaryKeyMixin, UpdatedAtMixin):
    """Authenticated application user."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN', 'ANALYST', 'INVESTIGATOR')",
            name="chk_users_role",
        ),
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
