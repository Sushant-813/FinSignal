"""Location domain persistence models."""

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from finsignal.common.models import CreatedAtMixin, UUIDPrimaryKeyMixin
from finsignal.core.database import Base


class Location(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Normalized geographic reference data."""

    __tablename__ = "locations"

    city: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    state: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    country: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )
