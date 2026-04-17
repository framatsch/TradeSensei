"""SQLAlchemy ORM model for the ``fx_rates`` table.

Caches daily exchange rates fetched from the Deutsche Bundesbank
Statistical Data Warehouse API.  Each row represents the official
EZB reference rate for one currency pair on one calendar date.
"""

import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    CURRENCY_LENGTH,
    FX_RATE_SOURCE_ECB,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
)
from app.core.database import Base


class FxRate(Base):
    """ORM representation of a cached daily foreign-exchange rate.

    Attributes:
        id: Auto-increment integer primary key.
        date: Calendar date of the exchange rate (EZB reference rate date).
        base: Base currency ISO-4217 code (e.g. ``"USD"``).
        quote: Quote currency ISO-4217 code (e.g. ``"EUR"``).
        rate: Exchange rate: ``1 base = rate quote``.
        source: Origin of the rate (default ``"ecb"``).
        created_at: Row-creation timestamp set by the database.
    """

    __tablename__ = "fx_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[dt.date] = mapped_column(
        Date,
        nullable=False,
        comment="Calendar date of the exchange rate (EZB reference rate).",
    )
    base: Mapped[str] = mapped_column(
        String(CURRENCY_LENGTH),
        nullable=False,
        comment="Base currency ISO-4217 code (e.g. USD).",
    )
    quote: Mapped[str] = mapped_column(
        String(CURRENCY_LENGTH),
        nullable=False,
        comment="Quote currency ISO-4217 code (e.g. EUR).",
    )
    rate: Mapped[Decimal] = mapped_column(
        Numeric(NUMERIC_PRECISION, NUMERIC_SCALE),
        nullable=False,
        comment="Exchange rate: 1 base = rate quote.",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=FX_RATE_SOURCE_ECB,
        comment="Source identifier for the rate (e.g. 'ecb').",
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("date", "base", "quote", name="uq_fx_rates_date_base_quote"),
    )

    def __repr__(self) -> str:
        """Return a human-readable string representation.

        Returns:
            A debug string with date, currency pair, and rate.
        """
        return f"<FxRate date={self.date} {self.base}/{self.quote}={self.rate}>"
