"""Async repository for the ``fx_rates`` table.

Provides cache-aware read and upsert operations for daily exchange rates.
No business logic lives here — only data access.
"""

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FX_RATE_SOURCE_ECB
from app.models.fx_rate import FxRate


class FxRateRepository:
    """Data-access layer for ``fx_rates`` table.

    All methods require a caller-supplied :class:`AsyncSession`.
    The session is never committed here — that is the responsibility of
    the service layer.
    """

    async def get_by_date(
        self,
        session: AsyncSession,
        date: dt.date,
        base: str,
        quote: str,
    ) -> Decimal | None:
        """Look up a cached exchange rate for a given date and currency pair.

        Args:
            session: Active async SQLAlchemy session.
            date: Calendar date of the rate.
            base: Base currency ISO-4217 code (e.g. ``"USD"``).
            quote: Quote currency ISO-4217 code (e.g. ``"EUR"``).

        Returns:
            The cached rate as a :class:`~decimal.Decimal`, or ``None`` if
            no entry exists for the given parameters.
        """
        stmt = select(FxRate.rate).where(
            FxRate.date == date,
            FxRate.base == base,
            FxRate.quote == quote,
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return Decimal(str(row)) if row is not None else None

    async def upsert(
        self,
        session: AsyncSession,
        date: dt.date,
        base: str,
        quote: str,
        rate: Decimal,
        source: str = FX_RATE_SOURCE_ECB,
    ) -> None:
        """Insert or update an exchange rate entry (upsert by unique key).

        Uses PostgreSQL ``ON CONFLICT DO UPDATE`` to remain idempotent on
        repeated imports for the same date.

        Args:
            session: Active async SQLAlchemy session.
            date: Calendar date of the rate.
            base: Base currency ISO-4217 code.
            quote: Quote currency ISO-4217 code.
            rate: Exchange rate value.
            source: Origin identifier (defaults to ``"ecb"``).
        """
        stmt = pg_insert(FxRate).values(
            date=date,
            base=base,
            quote=quote,
            rate=rate,
            source=source,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fx_rates_date_base_quote",
            set_={
                "rate": stmt.excluded.rate,
                "source": stmt.excluded.source,
            },
        )
        await session.execute(stmt)
