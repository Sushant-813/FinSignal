"""Device domain persistence models."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from finsignal.common.models import UpdatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class Device(Base, UUIDPrimaryKeyMixin, UpdatedAtMixin):
    """Device entity reference."""

    __tablename__ = "devices"

    external_device_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    device_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    operating_system: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
