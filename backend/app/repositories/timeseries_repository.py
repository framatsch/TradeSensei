"""Async repository for time-series aggregation queries.

All methods return plain Python tuples — no ORM model instances — so the
service layer can consume them without SQLAlchemy session lifetime concerns.
Every query filters on ``Trade.user_id`` directly to enforce per-user data
isolation without requiring a JOIN on ``accounts``.
Only trades where both ``pnl IS NOT NULL`` and ``closed_at IS NOT NULL``
are included.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, Numeric, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.portfolio import Portfolio
from app.models.trade import Trade


class TimeSeriesRepository:
    """Data-access object for time-series and aggregation queries.

    All queries are scoped to a ``user_id`` directly on ``Trade.user_id``
    to guarantee strict per-user data isolation without requiring a JOIN
    on ``accounts``.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    def _base_filter(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> list[ColumnElement[bool]]:
        """Build the shared WHERE clause predicates for all queries.

        Args:
            user_id: UUID of the requesting user (enforces ownership).
            account_id: Optional account UUID to further narrow results.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A list of SQLAlchemy column expression predicates.
        """
        predicates: list[ColumnElement[bool]] = [
            Trade.user_id == user_id,
            Trade.pnl.is_not(None),
            Trade.closed_at.is_not(None),
            Account.portfolio_id == portfolio_id,
            Portfolio.user_id == user_id,
        ]
        if account_id is not None:
            predicates.append(Trade.account_id == account_id)
        if from_dt is not None:
            predicates.append(Trade.closed_at >= from_dt)
        if to_dt is not None:
            predicates.append(Trade.closed_at <= to_dt)
        return predicates

    async def get_daily_pnl(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> list[tuple[date, Decimal, int]]:
        """Return per-day PnL aggregates for all qualifying closed trades.

        The result is ordered by trading date ascending so the service layer
        can compute a running cumulative sum in a single linear pass.

        Args:
            user_id: UUID of the requesting user — enforces ownership.
            account_id: Optional account UUID to narrow the query.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A list of ``(trade_date, total_pnl, trade_count)`` tuples,
            ordered by ``trade_date`` ascending.
        """
        # Use timezone-stripped date for grouping and ordering.
        date_col = func.date(Trade.closed_at)
        total_pnl_col = func.sum(cast(Trade.pnl, Numeric)).label("total_pnl")
        count_col = func.count(Trade.id).label("trade_count")

        stmt = (
            select(date_col.label("trade_date"), total_pnl_col, count_col)
            .join(Account, Trade.account_id == Account.id)
            .join(Portfolio, Account.portfolio_id == Portfolio.id)
            .where(
                *self._base_filter(
                    user_id,
                    portfolio_id,
                    account_id,
                    from_dt,
                    to_dt,
                )
            )
            .group_by(date_col)
            .order_by(date_col.asc())
        )

        result = await self._session.execute(stmt)
        rows = result.all()
        return [(row[0], Decimal(str(row[1])), int(row[2])) for row in rows]

    async def get_closed_pnl_series(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> list[tuple[datetime, Decimal, str]]:
        """Return the raw PnL series for all qualifying closed trades.

        Used internally by the service for monthly aggregation where we need
        individual trade PnL values along with their close timestamp and symbol.

        Args:
            user_id: UUID of the requesting user — enforces ownership.
            account_id: Optional account UUID to narrow the query.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A list of ``(closed_at, pnl, symbol)`` tuples sorted by
            ``closed_at`` ascending.
        """
        stmt = (
            select(Trade.closed_at, Trade.pnl, Trade.symbol)
            .join(Account, Trade.account_id == Account.id)
            .join(Portfolio, Account.portfolio_id == Portfolio.id)
            .where(
                *self._base_filter(
                    user_id,
                    portfolio_id,
                    account_id,
                    from_dt,
                    to_dt,
                )
            )
            .order_by(Trade.closed_at.asc())
        )

        result = await self._session.execute(stmt)
        rows = result.all()
        return [(row[0], Decimal(str(row[1])), str(row[2])) for row in rows]

    async def get_pnl_by_symbol(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> list[tuple[str, Decimal, int, int]]:
        """Return per-symbol PnL aggregates for all qualifying closed trades.

        Args:
            user_id: UUID of the requesting user — enforces ownership.
            account_id: Optional account UUID to narrow the query.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A list of ``(symbol, total_pnl, total_count, win_count)`` tuples
            where ``win_count`` is the number of trades with ``pnl > 0``.
        """
        total_pnl_col = func.sum(cast(Trade.pnl, Numeric)).label("total_pnl")
        total_count_col = func.count(Trade.id).label("total_count")
        win_count_col = func.count(Trade.id).filter(cast(Trade.pnl, Numeric) > 0).label("win_count")

        stmt = (
            select(Trade.symbol, total_pnl_col, total_count_col, win_count_col)
            .join(Account, Trade.account_id == Account.id)
            .join(Portfolio, Account.portfolio_id == Portfolio.id)
            .where(
                *self._base_filter(
                    user_id,
                    portfolio_id,
                    account_id,
                    from_dt,
                    to_dt,
                )
            )
            .group_by(Trade.symbol)
            .order_by(total_pnl_col.desc())
        )

        result = await self._session.execute(stmt)
        rows = result.all()
        return [(str(row[0]), Decimal(str(row[1])), int(row[2]), int(row[3])) for row in rows]

    async def get_pnl_by_asset_class(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
    ) -> list[tuple[str, Decimal, int, int]]:
        """Return per-asset-class PnL aggregates for all qualifying closed trades.

        Args:
            user_id: UUID of the requesting user — enforces ownership.
            account_id: Optional account UUID to narrow the query.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A list of ``(asset_class, total_pnl, total_count, win_count)`` tuples
            where ``win_count`` is the number of trades with ``pnl > 0``.
        """
        total_pnl_col = func.sum(cast(Trade.pnl, Numeric)).label("total_pnl")
        total_count_col = func.count(Trade.id).label("total_count")
        win_count_col = func.count(Trade.id).filter(cast(Trade.pnl, Numeric) > 0).label("win_count")

        stmt = (
            select(
                Trade.asset_class,
                total_pnl_col,
                total_count_col,
                win_count_col,
            )
            .join(Account, Trade.account_id == Account.id)
            .join(Portfolio, Account.portfolio_id == Portfolio.id)
            .where(
                *self._base_filter(
                    user_id,
                    portfolio_id,
                    account_id,
                    from_dt,
                    to_dt,
                )
            )
            .group_by(Trade.asset_class)
        )

        result = await self._session.execute(stmt)
        rows = result.all()
        return [(str(row[0]), Decimal(str(row[1])), int(row[2]), int(row[3])) for row in rows]
