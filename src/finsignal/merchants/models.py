"""Merchant domain persistence models."""

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finsignal.common.models import UpdatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class Merchant(Base, UUIDPrimaryKeyMixin, UpdatedAtMixin):
    """Merchant entity reference."""

    __tablename__ = "merchants"

    external_merchant_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    merchant_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    merchant_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    location = relationship("Location")
