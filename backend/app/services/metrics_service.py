"""Business-logic service for performance metrics aggregation.

This layer orchestrates the repository and the pure utility functions.
No HTTP concepts (``Request``, ``Response``, status codes) appear here.
No SQLAlchemy queries are issued here — all data access is delegated to
:class:`~app.repositories.metrics_repository.MetricsRepository`.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EQUITY_CURVE_MAX_POINTS
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.metrics import (
    DrawdownPoint,
    EquityCurvePoint,
    MetricsSummary,
    TradeMetrics,
)
from app.schemas.trade import TradeRead
from app.utils.metrics import (
    compute_drawdown_curve,
    compute_equity_curve,
    compute_trade_metrics,
)

_ZERO = Decimal("0")


class MetricsService:
    """Service layer for computing trading performance metrics.

    Fetches closed trades via the repository, delegates all arithmetic
    to the pure utility functions, and assembles the final DTO.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all data-access calls within
                this request.
        """
        self._repo = MetricsRepository(session)

    async def get_summary(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        starting_capital: Decimal = _ZERO,
    ) -> MetricsSummary:
        """Fetch closed trades and compute the full metrics summary.

        Args:
            user_id: UUID of the authenticated user — used to scope DB
                queries and enforce data isolation.
            account_id: Optional account UUID to restrict the computation
                to a single account.
            from_dt: Optional start of the date range filter (inclusive).
            to_dt: Optional end of the date range filter (inclusive).
            starting_capital: Initial equity value before the first trade.
                Defaults to ``Decimal("0")``.

        Returns:
            A fully populated :class:`~app.schemas.metrics.MetricsSummary`
            DTO.
        """
        orm_trades = await self._repo.get_closed_trades_for_user(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        trade_dtos: list[TradeRead] = [TradeRead.model_validate(t) for t in orm_trades]

        metrics: TradeMetrics = compute_trade_metrics(trade_dtos)

        equity_curve: list[EquityCurvePoint] = compute_equity_curve(
            trade_dtos, starting_capital=starting_capital
        )

        # Cap the equity curve at the configured maximum number of points.
        if len(equity_curve) > EQUITY_CURVE_MAX_POINTS:
            equity_curve = equity_curve[:EQUITY_CURVE_MAX_POINTS]

        drawdown_curve: list[DrawdownPoint]
        max_drawdown: Decimal
        max_drawdown_abs: Decimal
        drawdown_curve, max_drawdown, max_drawdown_abs = compute_drawdown_curve(
            equity_curve, starting_capital=starting_capital
        )

        return MetricsSummary(
            metrics=metrics,
            max_drawdown=max_drawdown,
            max_drawdown_abs=max_drawdown_abs,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
        )

    async def get_equity_curve(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        starting_capital: Decimal = _ZERO,
    ) -> list[EquityCurvePoint]:
        """Fetch closed trades and compute the equity curve only.

        Args:
            user_id: UUID of the authenticated user.
            account_id: Optional account UUID filter.
            from_dt: Optional start date filter (inclusive).
            to_dt: Optional end date filter (inclusive).
            starting_capital: Initial equity value before the first trade.

        Returns:
            An ordered list of :class:`~app.schemas.metrics.EquityCurvePoint`
            DTOs, capped at ``EQUITY_CURVE_MAX_POINTS`` entries.
        """
        orm_trades = await self._repo.get_closed_trades_for_user(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        trade_dtos: list[TradeRead] = [TradeRead.model_validate(t) for t in orm_trades]
        curve = compute_equity_curve(trade_dtos, starting_capital=starting_capital)
        if len(curve) > EQUITY_CURVE_MAX_POINTS:
            curve = curve[:EQUITY_CURVE_MAX_POINTS]
        return curve

    async def get_drawdown_curve(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        starting_capital: Decimal = _ZERO,
    ) -> list[DrawdownPoint]:
        """Fetch closed trades and compute the drawdown curve only.

        Args:
            user_id: UUID of the authenticated user.
            account_id: Optional account UUID filter.
            from_dt: Optional start date filter (inclusive).
            to_dt: Optional end date filter (inclusive).
            starting_capital: Initial equity value before the first trade.

        Returns:
            An ordered list of :class:`~app.schemas.metrics.DrawdownPoint`
            DTOs.
        """
        orm_trades = await self._repo.get_closed_trades_for_user(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        trade_dtos: list[TradeRead] = [TradeRead.model_validate(t) for t in orm_trades]
        curve = compute_equity_curve(trade_dtos, starting_capital=starting_capital)
        if len(curve) > EQUITY_CURVE_MAX_POINTS:
            curve = curve[:EQUITY_CURVE_MAX_POINTS]
        drawdown_curve, _, _ = compute_drawdown_curve(
            curve, starting_capital=starting_capital
        )
        return drawdown_curve
