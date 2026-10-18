"""Account domain persistence models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import UpdatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class Account(Base, UUIDPrimaryKeyMixin, UpdatedAtMixin):
    """Financial account being analyzed."""

    __tablename__ = "accounts"

    external_account_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    account_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    customer_age: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    home_location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    home_location = relationship("Location")
    devices = relationship("Device", secondary="account_devices")


class AccountDevice(Base):
    """Many-to-many relationship between accounts and devices."""

    __tablename__ = "account_devices"

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
