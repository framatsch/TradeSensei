"""Async repository for tax-related aggregate queries.

Provides the raw SQL aggregation needed by :class:`~app.services.tax_service.TaxService`
to build the annual tax summary.  No business logic or categorisation lives here.
"""

import uuid
from decimal import Decimal

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import (  # noqa: F401 (AssetClass used in case expr)
    AssetClass,
    Trade,
)


class TaxRepository:
    """Data-access layer for annual tax summary queries.

    All methods are scoped to a single user and perform only read operations.
    """

    async def get_annual_summary_rows(
        self,
        session: AsyncSession,
        year: int,
        user_id: uuid.UUID,
    ) -> list[tuple[bool, Decimal, Decimal, int, int]]:
        """Aggregate closed trades with pnl_eur for a given year and user.

        Groups by ``is_equity`` (True for :attr:`~app.models.trade.AssetClass.EQUITY`,
        False for all others) and returns aggregated gains, losses, trade count,
        and count of trades with a NULL ``pnl_eur``.

        Only trades where ``pnl IS NOT NULL`` (closed trades) are included.
        The ``pnl_eur IS NOT NULL`` filter is applied separately when computing
        financial totals; ``trades_missing_eur`` counts those that slipped through.

        Args:
            session: Active async SQLAlchemy session.
            year: Calendar year to filter on (based on ``closed_at``).
            user_id: UUID of the authenticated user.

        Returns:
            A list of 5-tuples ``(is_equity, gains_eur, losses_eur, trade_count,
            missing_count)`` with one row per category that has at least one trade.

            Each tuple contains:
            - ``is_equity`` (bool): ``True`` for equity, ``False`` for derivatives.
            - ``gains_eur`` (Decimal): Sum of positive ``pnl_eur`` values.
            - ``losses_eur`` (Decimal): Sum of negative ``pnl_eur`` values
              (always <= 0).
            - ``trade_count`` (int): Trades with non-NULL ``pnl_eur``.
            - ``missing_count`` (int): Trades with NULL ``pnl_eur``.
        """
        is_equity_expr = case(
            (Trade.asset_class == AssetClass.EQUITY, True),
            else_=False,
        )

        gains_expr = func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Trade.pnl_eur.is_not(None),
                            Trade.pnl_eur > 0,
                        ),
                        Trade.pnl_eur,
                    ),
                    else_=None,
                )
            ),
            Decimal("0"),
        )

        losses_expr = func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Trade.pnl_eur.is_not(None),
                            Trade.pnl_eur < 0,
                        ),
                        Trade.pnl_eur,
                    ),
                    else_=None,
                )
            ),
            Decimal("0"),
        )

        trade_count_expr = func.count(Trade.pnl_eur)  # COUNT ignores NULLs.

        missing_count_expr = func.count(
            case(
                (Trade.pnl_eur.is_(None), 1),
                else_=None,
            )
        )

        stmt = (
            select(
                is_equity_expr.label("is_equity"),
                gains_expr.label("gains_eur"),
                losses_expr.label("losses_eur"),
                trade_count_expr.label("trade_count"),
                missing_count_expr.label("missing_count"),
            )
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.pnl.is_not(None),  # Only closed trades.
                    extract("year", Trade.closed_at) == year,
                )
            )
            .group_by(is_equity_expr)
        )

        result = await session.execute(stmt)
        rows = result.all()
        output: list[tuple[bool, Decimal, Decimal, int, int]] = [
            (
                bool(row.is_equity),
                Decimal(str(row.gains_eur)),
                Decimal(str(row.losses_eur)),
                int(row.trade_count),
                int(row.missing_count),
            )
            for row in rows
        ]
        return output

    async def get_annual_trades(
        self,
        session: AsyncSession,
        year: int,
        user_id: uuid.UUID,
    ) -> list[Trade]:
        """Fetch individual closed trades for a given year and user.

        Used by the CSV export endpoint.  Returns all closed trades (those
        where ``pnl IS NOT NULL``) ordered by ``closed_at`` ascending,
        regardless of whether ``pnl_eur`` is set.

        Args:
            session: Active async SQLAlchemy session.
            year: Calendar year to filter on (based on ``closed_at``).
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`~app.models.trade.Trade` ORM instances ordered
            by ``closed_at`` ascending.
        """
        stmt = (
            select(Trade)
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.pnl.is_not(None),  # Only closed trades.
                    extract("year", Trade.closed_at) == year,
                )
            )
            .order_by(Trade.closed_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
