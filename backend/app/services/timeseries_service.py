"""Business-logic service for time-series and aggregation endpoints.

Orchestrates the :class:`~app.repositories.timeseries_repository.TimeSeriesRepository`
and converts raw DB tuples into typed Pydantic DTOs.  No HTTP concepts
(``Request``, ``Response``, status codes) appear here. No SQLAlchemy
queries are issued here — all data access is delegated to the repository.
"""

import calendar
import uuid
from collections import deque
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    RETURN_DISTRIBUTION_DEFAULT_BUCKETS,
    ROLLING_WINRATE_MAX_POINTS,
)
from app.repositories.timeseries_repository import TimeSeriesRepository
from app.schemas.timeseries import (
    DailyPnl,
    MonthlyPnl,
    MonthlyWinratePoint,
    PnlByAssetClass,
    PnlBySymbol,
    ReturnDistribution,
    RollingWinratePoint,
)

_ZERO = Decimal("0")
_ONE = Decimal("1")


class TimeSeriesService:
    """Service layer for time-series PnL aggregation.

    Fetches raw aggregate tuples from the repository and assembles typed
    Pydantic DTOs with all derived fields (cumulative PnL, win rate, etc.)
    computed in Python.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all data-access calls within
                this request.
        """
        self._repo = TimeSeriesRepository(session)

    async def get_daily_pnl(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[DailyPnl]:
        """Fetch daily grouped PnL and compute a running cumulative total.

        Args:
            user_id: UUID of the authenticated user — scopes DB queries.
            account_id: Optional account UUID to restrict the computation.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A chronologically ordered list of :class:`~app.schemas.timeseries.DailyPnl`
            DTOs, each with ``cumulative_pnl`` reflecting the running total up to
            and including that day.
        """
        rows = await self._repo.get_daily_pnl(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        result: list[DailyPnl] = []
        running: Decimal = _ZERO
        for trade_date, pnl, trade_count in rows:
            running += pnl
            result.append(
                DailyPnl(
                    date=trade_date,
                    pnl=pnl,
                    trade_count=trade_count,
                    cumulative_pnl=running,
                )
            )
        return result

    async def get_monthly_pnl(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[MonthlyPnl]:
        """Aggregate the raw trade PnL series into monthly buckets.

        Fetches the individual closed-trade PnL series from the repository
        and performs month-level aggregation (total PnL, trade count, and
        win rate) in Python so that no additional DB round-trip is needed.

        Args:
            user_id: UUID of the authenticated user — scopes DB queries.
            account_id: Optional account UUID to restrict the computation.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A chronologically ordered list of
            :class:`~app.schemas.timeseries.MonthlyPnl`
            DTOs.
        """
        rows = await self._repo.get_closed_pnl_series(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        # Accumulate per-(year, month) stats using a dict keyed by (year, month)
        # to preserve insertion order (Python 3.7+ dicts are ordered).
        monthly_pnl: dict[tuple[int, int], Decimal] = {}
        monthly_count: dict[tuple[int, int], int] = {}
        monthly_wins: dict[tuple[int, int], int] = {}

        for closed_at, pnl, _symbol in rows:
            key = (closed_at.year, closed_at.month)
            monthly_pnl[key] = monthly_pnl.get(key, _ZERO) + pnl
            monthly_count[key] = monthly_count.get(key, 0) + 1
            if pnl > _ZERO:
                monthly_wins[key] = monthly_wins.get(key, 0) + 1

        result: list[MonthlyPnl] = []
        for (year, month), total_pnl in monthly_pnl.items():
            count = monthly_count[(year, month)]
            wins = monthly_wins.get((year, month), 0)
            win_rate = Decimal(wins) / Decimal(count) if count > 0 else _ZERO
            result.append(
                MonthlyPnl(
                    year=year,
                    month=month,
                    pnl=total_pnl,
                    trade_count=count,
                    win_rate=win_rate,
                )
            )
        return result

    async def get_monthly_winrate(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[MonthlyWinratePoint]:
        """Aggregate closed-trade PnL series into monthly win-rate buckets.

        Reuses the raw per-trade PnL series from the repository and computes
        win/loss counts plus win rate for each calendar month in Python.

        Args:
            user_id: UUID of the authenticated user — scopes DB queries.
            account_id: Optional account UUID to restrict the computation.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A chronologically ordered list of
            :class:`~app.schemas.timeseries.MonthlyWinratePoint` DTOs.
        """
        rows = await self._repo.get_closed_pnl_series(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        monthly_wins: dict[tuple[int, int], int] = {}
        monthly_losses: dict[tuple[int, int], int] = {}

        for closed_at, pnl, _symbol in rows:
            key = (closed_at.year, closed_at.month)
            if pnl > _ZERO:
                monthly_wins[key] = monthly_wins.get(key, 0) + 1
            else:
                monthly_losses[key] = monthly_losses.get(key, 0) + 1

        # Union of all months that appear in either dict, in chronological order.
        all_keys = sorted(set(monthly_wins) | set(monthly_losses))

        result: list[MonthlyWinratePoint] = []
        for year, month in all_keys:
            wins = monthly_wins.get((year, month), 0)
            losses = monthly_losses.get((year, month), 0)
            total = wins + losses
            win_rate = Decimal(wins) / Decimal(total) if total > 0 else _ZERO
            month_abbr = calendar.month_abbr[month]
            label = f"{month_abbr} {year}"
            result.append(
                MonthlyWinratePoint(
                    year=year,
                    month=month,
                    label=label,
                    win_rate=win_rate,
                    win_count=wins,
                    loss_count=losses,
                    trade_count=total,
                )
            )
        return result

    async def get_pnl_by_symbol(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[PnlBySymbol]:
        """Return per-symbol PnL aggregates sorted by total PnL descending.

        Args:
            user_id: UUID of the authenticated user — scopes DB queries.
            account_id: Optional account UUID to restrict the computation.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A list of :class:`~app.schemas.timeseries.PnlBySymbol` DTOs
            sorted by ``total_pnl`` descending (most profitable symbol first).
        """
        rows = await self._repo.get_pnl_by_symbol(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        result: list[PnlBySymbol] = []
        for symbol, total_pnl, total_count, win_count in rows:
            win_rate = (
                Decimal(win_count) / Decimal(total_count) if total_count > 0 else _ZERO
            )
            avg_pnl = total_pnl / Decimal(total_count) if total_count > 0 else _ZERO
            result.append(
                PnlBySymbol(
                    symbol=symbol,
                    total_pnl=total_pnl,
                    trade_count=total_count,
                    win_rate=win_rate,
                    avg_pnl=avg_pnl,
                )
            )
        return result

    async def get_pnl_by_asset_class(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[PnlByAssetClass]:
        """Return per-asset-class PnL aggregates.

        Args:
            user_id: UUID of the authenticated user — scopes DB queries.
            account_id: Optional account UUID to restrict the computation.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A list of :class:`~app.schemas.timeseries.PnlByAssetClass` DTOs.
        """
        rows = await self._repo.get_pnl_by_asset_class(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        result: list[PnlByAssetClass] = []
        for asset_class, total_pnl, total_count, win_count in rows:
            win_rate = (
                Decimal(win_count) / Decimal(total_count) if total_count > 0 else _ZERO
            )
            result.append(
                PnlByAssetClass(
                    asset_class=asset_class,
                    total_pnl=total_pnl,
                    trade_count=total_count,
                    win_rate=win_rate,
                )
            )
        return result

    async def get_return_distribution(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        buckets: int = RETURN_DISTRIBUTION_DEFAULT_BUCKETS,
    ) -> list[ReturnDistribution]:
        """Build a histogram of PnL returns across equal-width bins.

        Fetches the raw per-trade PnL series and distributes each value into
        one of ``buckets`` equal-width bins spanning
        ``[min_pnl, max_pnl]``. When all PnL values are identical the
        single value is placed in a single bucket of zero width.

        Args:
            user_id: UUID of the authenticated user — scopes DB queries.
            account_id: Optional account UUID to restrict the computation.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.
            buckets: Number of equal-width histogram bins. Must be between
                ``RETURN_DISTRIBUTION_MIN_BUCKETS`` and
                ``RETURN_DISTRIBUTION_MAX_BUCKETS`` (validated at the API
                layer). Defaults to
                ``RETURN_DISTRIBUTION_DEFAULT_BUCKETS`` (20).

        Returns:
            A list of :class:`~app.schemas.timeseries.ReturnDistribution` DTOs,
            one per bucket. The list is empty when no closed trades exist.
            Buckets with zero trades are included so the histogram shape is
            always preserved.
        """
        rows = await self._repo.get_closed_pnl_series(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        if not rows:
            return []

        pnl_values = [pnl for _dt, pnl, _sym in rows]
        total = len(pnl_values)

        min_pnl = min(pnl_values)
        max_pnl = max(pnl_values)

        # Edge case: all trades have identical PnL.
        if min_pnl == max_pnl:
            return [
                ReturnDistribution(
                    bucket_min=min_pnl,
                    bucket_max=max_pnl,
                    count=total,
                    frequency=_ONE,
                )
            ]

        bucket_width = (max_pnl - min_pnl) / Decimal(buckets)
        counts = [0] * buckets

        for pnl in pnl_values:
            # Determine the zero-based bin index.
            idx = int((pnl - min_pnl) / bucket_width)
            # Clamp the maximum value into the last bucket (inclusive upper bound).
            if idx >= buckets:
                idx = buckets - 1
            counts[idx] += 1

        result: list[ReturnDistribution] = []
        for i in range(buckets):
            bucket_min = min_pnl + bucket_width * Decimal(i)
            bucket_max = bucket_min + bucket_width
            result.append(
                ReturnDistribution(
                    bucket_min=bucket_min,
                    bucket_max=bucket_max,
                    count=counts[i],
                    frequency=Decimal(counts[i]) / Decimal(total),
                )
            )
        return result

    async def get_rolling_winrate(
        self,
        user_id: uuid.UUID,
        window_trades: int = 20,
        account_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RollingWinratePoint]:
        """Compute a rolling win-rate series over closed trades.

        Fetches the raw per-trade PnL series (ordered chronologically by
        ``closed_at``) and slides a window of ``window_trades`` across it in
        Python using a :class:`collections.deque`.  Each point in the returned
        series represents the win rate over the ``window_trades`` most recent
        trades ending at that position.

        The first ``window_trades - 1`` trades do not yet have a full window;
        for these positions the window size is the number of trades seen so far
        (i.e. the window grows until it reaches ``window_trades``).

        The response is capped at ``ROLLING_WINRATE_MAX_POINTS`` most-recent
        points to avoid unbounded response sizes.

        Args:
            user_id: UUID of the authenticated user — scopes DB queries.
            window_trades: Sliding window size in number of trades (5–100).
            account_id: Optional account UUID to restrict the computation.
            from_dt: Optional inclusive lower bound on ``closed_at``.
            to_dt: Optional inclusive upper bound on ``closed_at``.

        Returns:
            A chronologically ordered list of
            :class:`~app.schemas.timeseries.RollingWinratePoint` DTOs.
            Empty when there are no closed trades with PnL data.
        """
        rows = await self._repo.get_closed_pnl_series(
            user_id=user_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        if not rows:
            return []

        win_deque: deque[bool] = deque(maxlen=window_trades)
        result: list[RollingWinratePoint] = []

        for trade_index, (closed_at, pnl, _symbol) in enumerate(rows):
            win_deque.append(pnl > _ZERO)
            window_size = len(win_deque)
            wins = sum(1 for w in win_deque if w)
            rolling_winrate = Decimal(wins) / Decimal(window_size)
            result.append(
                RollingWinratePoint(
                    trade_index=trade_index,
                    closed_at=closed_at,
                    rolling_winrate=rolling_winrate,
                    window=window_size,
                )
            )

        # Cap at max points (most recent).
        if len(result) > ROLLING_WINRATE_MAX_POINTS:
            result = result[-ROLLING_WINRATE_MAX_POINTS:]

        return result
