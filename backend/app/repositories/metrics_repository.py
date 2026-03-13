"""Async repository for performance-metrics queries.

All methods return SQLAlchemy ORM instances.  No business logic lives
here — filtering, validation, and computation belong in the service
layer.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade


class MetricsRepository:
    """Data-access object that fetches closed trades for metrics computation.

    Every query is scoped to a ``user_id`` to enforce data isolation
    between users.  Queries filter directly on ``Trade.user_id`` without
    requiring a JOIN on ``accounts``, so trades created without an account
    are included correctly.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    async def get_closed_trades_for_account(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[Trade]:
        """Return all closed trades (pnl is not null) for a specific account.

        The query is scoped to ``user_id`` directly on ``Trade.user_id`` to
        prevent cross-user data leakage.

        Args:
            account_id: UUID of the account whose trades to fetch.
            user_id: UUID of the requesting user — enforces ownership.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            An ordered list of :class:`~app.models.trade.Trade` ORM
            instances with ``pnl`` set, sorted by ``closed_at`` ascending.
        """
        stmt = select(Trade).where(
            Trade.account_id == account_id,
            Trade.user_id == user_id,
            Trade.pnl.is_not(None),
            Trade.closed_at.is_not(None),
        )

        if from_dt is not None:
            stmt = stmt.where(Trade.closed_at >= from_dt)
        if to_dt is not None:
            stmt = stmt.where(Trade.closed_at <= to_dt)

        stmt = stmt.order_by(Trade.closed_at.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_closed_trades_for_user(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[Trade]:
        """Return all closed trades for a user across all accounts.

        Filters directly on ``Trade.user_id`` so trades without an
        ``account_id`` are included.  When ``account_id`` is supplied the
        results are further narrowed to that specific account.

        Args:
            user_id: UUID of the requesting user.
            account_id: Optional account UUID to narrow the query.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            An ordered list of :class:`~app.models.trade.Trade` ORM
            instances with ``pnl`` set, sorted by ``closed_at`` ascending.
        """
        stmt = select(Trade).where(
            Trade.user_id == user_id,
            Trade.pnl.is_not(None),
            Trade.closed_at.is_not(None),
        )

        if account_id is not None:
            stmt = stmt.where(Trade.account_id == account_id)
        if from_dt is not None:
            stmt = stmt.where(Trade.closed_at >= from_dt)
        if to_dt is not None:
            stmt = stmt.where(Trade.closed_at <= to_dt)

        stmt = stmt.order_by(Trade.closed_at.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
