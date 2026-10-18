"""Reusable SQLAlchemy 2.0 declarative mixins for FinSignal."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """Provides a UUID v4 primary key column named 'id'.

    Applied to all standalone primary entities. Excluded from tables with composite
    natural primary keys (such as account_devices).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class CreatedAtMixin:
    """Provides an immutable created_at timestamp in UTC.

    Applied to all tables that define record creation timestamps.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class UpdatedAtMixin(CreatedAtMixin):
    """Provides created_at and mutable updated_at timestamps in UTC.

    Applied strictly to mutable domain entities (users, accounts, merchants, devices).
    Immutable facts and audit ledgers must not inherit from this mixin.
    """

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
