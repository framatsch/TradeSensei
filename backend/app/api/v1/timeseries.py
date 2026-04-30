"""Route handlers for the ``/api/v1/timeseries`` resource."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    RETURN_DISTRIBUTION_DEFAULT_BUCKETS,
    RETURN_DISTRIBUTION_MAX_BUCKETS,
    RETURN_DISTRIBUTION_MIN_BUCKETS,
    ROLLING_WINRATE_DEFAULT_WINDOW,
    ROLLING_WINRATE_MAX_WINDOW,
    ROLLING_WINRATE_MIN_WINDOW,
)
from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.timeseries import (
    DailyPnl,
    MonthlyPnl,
    MonthlyWinratePoint,
    PnlByAssetClass,
    PnlBySymbol,
    ReturnDistribution,
    RollingWinratePoint,
)
from app.services.timeseries_service import TimeSeriesService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/timeseries",
    tags=["timeseries"],
    dependencies=[Depends(require_portfolio_owner)],
)


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> TimeSeriesService:
    """FastAPI dependency that constructs a :class:`TimeSeriesService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`TimeSeriesService` bound to the current session.
    """
    return TimeSeriesService(session)


@router.get(
    "/daily-pnl",
    response_model=ResponseEnvelope[list[DailyPnl]],
    summary="Get Daily PnL",
    description=(
        "Return per-day PnL aggregates for the authenticated user's closed "
        "trades, ordered by trading date ascending.\n\n"
        "**What each entry contains:**\n"
        "- `date`: the calendar date (UTC).\n"
        "- `pnl`: total PnL for all closed trades on that day.\n"
        "- `trade_count`: number of closed trades on that day.\n"
        "- `cumulative_pnl`: running cumulative PnL from the earliest "
        "available day in the result set.\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow "
        "the result by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=("An ordered list (ascending by date) of daily PnL aggregates, wrapped in a ResponseEnvelope."),
    responses={
        200: {"description": "Daily PnL aggregates successfully returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {"description": ("Query parameter validation error. Check that dates are valid ISO-8601 strings.")},
    },
)
async def get_daily_pnl(
    portfolio_id: uuid.UUID,
    service: Annotated[TimeSeriesService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(
            description=("Optional account UUID to restrict results to a single account. When omitted, trades from all of the user's accounts are included.")
        ),
    ] = None,
    from_dt: Annotated[
        datetime | None,
        Query(
            alias="from_dt",
            description=("Optional ISO-8601 datetime lower bound (inclusive) on ``closed_at``. When omitted, no lower bound is applied."),
            examples=["2024-01-01T00:00:00Z"],
        ),
    ] = None,
    to_dt: Annotated[
        datetime | None,
        Query(
            alias="to_dt",
            description=("Optional ISO-8601 datetime upper bound (inclusive) on ``closed_at``. When omitted, no upper bound is applied."),
            examples=["2024-12-31T23:59:59Z"],
        ),
    ] = None,
) -> ResponseEnvelope[list[DailyPnl]]:
    """Return daily PnL aggregates with a running cumulative total.

    Args:
        service: Injected time-series service.
        current_user: The currently authenticated user.
        account_id: Optional account UUID filter.
        from_dt: Optional inclusive lower bound on ``closed_at``.
        to_dt: Optional inclusive upper bound on ``closed_at``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains an ordered list of :class:`~app.schemas.timeseries.DailyPnl` DTOs.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or invalid.
    """
    try:
        data = await service.get_daily_pnl(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[DailyPnl]](data=data)


@router.get(
    "/monthly-pnl",
    response_model=ResponseEnvelope[list[MonthlyPnl]],
    summary="Get Monthly PnL",
    description=(
        "Return per-month PnL aggregates for the authenticated user's closed "
        "trades, ordered by year and month ascending.\n\n"
        "**What each entry contains:**\n"
        "- `year` and `month`: the calendar period.\n"
        "- `pnl`: total PnL for all closed trades in that month.\n"
        "- `trade_count`: total number of closed trades that month.\n"
        "- `win_rate`: fraction of winning trades (PnL > 0) that month "
        "(0.0–1.0).\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow "
        "the result by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=("An ordered list (ascending by year/month) of monthly PnL aggregates, wrapped in a ResponseEnvelope."),
    responses={
        200: {"description": "Monthly PnL aggregates successfully returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {"description": ("Query parameter validation error. Check that dates are valid ISO-8601 strings.")},
    },
)
async def get_monthly_pnl(
    portfolio_id: uuid.UUID,
    service: Annotated[TimeSeriesService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description=("Optional account UUID to restrict results to a single account. When omitted, all of the user's accounts are included.")),
    ] = None,
    from_dt: Annotated[
        datetime | None,
        Query(
            alias="from_dt",
            description=("Optional ISO-8601 datetime lower bound (inclusive) on ``closed_at``. When omitted, no lower bound is applied."),
            examples=["2024-01-01T00:00:00Z"],
        ),
    ] = None,
    to_dt: Annotated[
        datetime | None,
        Query(
            alias="to_dt",
            description=("Optional ISO-8601 datetime upper bound (inclusive) on ``closed_at``. When omitted, no upper bound is applied."),
            examples=["2024-12-31T23:59:59Z"],
        ),
    ] = None,
) -> ResponseEnvelope[list[MonthlyPnl]]:
    """Return monthly PnL aggregates with per-month win rates.

    Args:
        service: Injected time-series service.
        current_user: The currently authenticated user.
        account_id: Optional account UUID filter.
        from_dt: Optional inclusive lower bound on ``closed_at``.
        to_dt: Optional inclusive upper bound on ``closed_at``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains an ordered list of :class:`~app.schemas.timeseries.MonthlyPnl` DTOs.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or invalid.
    """
    try:
        data = await service.get_monthly_pnl(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[MonthlyPnl]](data=data)


@router.get(
    "/pnl-by-symbol",
    response_model=ResponseEnvelope[list[PnlBySymbol]],
    summary="Get PnL by Symbol",
    description=(
        "Return PnL aggregates grouped by ticker symbol for the authenticated "
        "user's closed trades, sorted by ``total_pnl`` descending (most "
        "profitable symbol first).\n\n"
        "**What each entry contains:**\n"
        "- `symbol`: ticker symbol.\n"
        "- `total_pnl`: sum of PnL across all trades for this symbol.\n"
        "- `trade_count`: number of closed trades for this symbol.\n"
        "- `win_rate`: fraction of winning trades (PnL > 0) for this symbol.\n"
        "- `avg_pnl`: average PnL per trade for this symbol.\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow "
        "the result by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=("A list of per-symbol PnL aggregates sorted by ``total_pnl`` descending, wrapped in a ResponseEnvelope."),
    responses={
        200: {"description": "Per-symbol PnL aggregates successfully returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {"description": ("Query parameter validation error. Check that dates are valid ISO-8601 strings.")},
    },
)
async def get_pnl_by_symbol(
    portfolio_id: uuid.UUID,
    service: Annotated[TimeSeriesService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description=("Optional account UUID to restrict results to a single account. When omitted, all of the user's accounts are included.")),
    ] = None,
    from_dt: Annotated[
        datetime | None,
        Query(
            alias="from_dt",
            description=("Optional ISO-8601 datetime lower bound (inclusive) on ``closed_at``. When omitted, no lower bound is applied."),
            examples=["2024-01-01T00:00:00Z"],
        ),
    ] = None,
    to_dt: Annotated[
        datetime | None,
        Query(
            alias="to_dt",
            description=("Optional ISO-8601 datetime upper bound (inclusive) on ``closed_at``. When omitted, no upper bound is applied."),
            examples=["2024-12-31T23:59:59Z"],
        ),
    ] = None,
) -> ResponseEnvelope[list[PnlBySymbol]]:
    """Return per-symbol PnL aggregates for the current user.

    Args:
        service: Injected time-series service.
        current_user: The currently authenticated user.
        account_id: Optional account UUID filter.
        from_dt: Optional inclusive lower bound on ``closed_at``.
        to_dt: Optional inclusive upper bound on ``closed_at``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains a list of :class:`~app.schemas.timeseries.PnlBySymbol` DTOs.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or invalid.
    """
    try:
        data = await service.get_pnl_by_symbol(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[PnlBySymbol]](data=data)


@router.get(
    "/pnl-by-asset-class",
    response_model=ResponseEnvelope[list[PnlByAssetClass]],
    summary="Get PnL by Asset Class",
    description=(
        "Return PnL aggregates grouped by asset class for the authenticated "
        "user's closed trades.\n\n"
        "**What each entry contains:**\n"
        "- `asset_class`: one of EQUITY, OPTION, FUTURE, FOREX, CRYPTO.\n"
        "- `total_pnl`: sum of PnL across all trades for this asset class.\n"
        "- `trade_count`: number of closed trades for this asset class.\n"
        "- `win_rate`: fraction of winning trades (PnL > 0) for this asset "
        "class.\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow "
        "the result by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=("A list of per-asset-class PnL aggregates, wrapped in a ResponseEnvelope."),
    responses={
        200: {"description": "Per-asset-class PnL aggregates successfully returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {"description": ("Query parameter validation error. Check that dates are valid ISO-8601 strings.")},
    },
)
async def get_pnl_by_asset_class(
    portfolio_id: uuid.UUID,
    service: Annotated[TimeSeriesService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description=("Optional account UUID to restrict results to a single account. When omitted, all of the user's accounts are included.")),
    ] = None,
    from_dt: Annotated[
        datetime | None,
        Query(
            alias="from_dt",
            description=("Optional ISO-8601 datetime lower bound (inclusive) on ``closed_at``. When omitted, no lower bound is applied."),
            examples=["2024-01-01T00:00:00Z"],
        ),
    ] = None,
    to_dt: Annotated[
        datetime | None,
        Query(
            alias="to_dt",
            description=("Optional ISO-8601 datetime upper bound (inclusive) on ``closed_at``. When omitted, no upper bound is applied."),
            examples=["2024-12-31T23:59:59Z"],
        ),
    ] = None,
) -> ResponseEnvelope[list[PnlByAssetClass]]:
    """Return per-asset-class PnL aggregates for the current user.

    Args:
        service: Injected time-series service.
        current_user: The currently authenticated user.
        account_id: Optional account UUID filter.
        from_dt: Optional inclusive lower bound on ``closed_at``.
        to_dt: Optional inclusive upper bound on ``closed_at``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains a list of :class:`~app.schemas.timeseries.PnlByAssetClass` DTOs.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or invalid.
    """
    try:
        data = await service.get_pnl_by_asset_class(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[PnlByAssetClass]](data=data)


@router.get(
    "/return-distribution",
    response_model=ResponseEnvelope[list[ReturnDistribution]],
    summary="Get Return Distribution",
    description=(
        "Return a histogram of PnL return distribution for the authenticated "
        "user's closed trades.\n\n"
        "**What each bucket contains:**\n"
        "- `bucket_min` / `bucket_max`: the PnL range for this bin.\n"
        "- `count`: number of trades whose PnL falls in this bin.\n"
        "- `frequency`: fraction of total trades in this bin (0.0–1.0).\n\n"
        "**Bins:** the range ``[min_pnl, max_pnl]`` is divided into "
        "``buckets`` equal-width bins. When all trades have the same PnL "
        "a single bucket is returned.\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow "
        "the result by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=(
        "A list of histogram buckets for the PnL return distribution, wrapped in a ResponseEnvelope. Empty list when no closed trades exist."
    ),
    responses={
        200: {"description": "Return distribution histogram successfully returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {
            "description": (
                "Query parameter validation error. Check that dates are valid "
                "ISO-8601 strings and ``buckets`` is between "
                f"{RETURN_DISTRIBUTION_MIN_BUCKETS} and "
                f"{RETURN_DISTRIBUTION_MAX_BUCKETS}."
            )
        },
    },
)
async def get_return_distribution(
    portfolio_id: uuid.UUID,
    service: Annotated[TimeSeriesService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description=("Optional account UUID to restrict results to a single account. When omitted, all of the user's accounts are included.")),
    ] = None,
    from_dt: Annotated[
        datetime | None,
        Query(
            alias="from_dt",
            description=("Optional ISO-8601 datetime lower bound (inclusive) on ``closed_at``. When omitted, no lower bound is applied."),
            examples=["2024-01-01T00:00:00Z"],
        ),
    ] = None,
    to_dt: Annotated[
        datetime | None,
        Query(
            alias="to_dt",
            description=("Optional ISO-8601 datetime upper bound (inclusive) on ``closed_at``. When omitted, no upper bound is applied."),
            examples=["2024-12-31T23:59:59Z"],
        ),
    ] = None,
    buckets: Annotated[
        int,
        Query(
            ge=RETURN_DISTRIBUTION_MIN_BUCKETS,
            le=RETURN_DISTRIBUTION_MAX_BUCKETS,
            description=(
                f"Number of equal-width histogram bins. "
                f"Must be between {RETURN_DISTRIBUTION_MIN_BUCKETS} and "
                f"{RETURN_DISTRIBUTION_MAX_BUCKETS}. "
                f"Defaults to {RETURN_DISTRIBUTION_DEFAULT_BUCKETS}."
            ),
            examples=[20, 50],
        ),
    ] = RETURN_DISTRIBUTION_DEFAULT_BUCKETS,
) -> ResponseEnvelope[list[ReturnDistribution]]:
    """Return a PnL histogram for the current user's closed trades.

    Args:
        service: Injected time-series service.
        current_user: The currently authenticated user.
        account_id: Optional account UUID filter.
        from_dt: Optional inclusive lower bound on ``closed_at``.
        to_dt: Optional inclusive upper bound on ``closed_at``.
        buckets: Number of equal-width histogram bins (5–100, default 20).

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains a list of :class:`~app.schemas.timeseries.ReturnDistribution`
        DTOs.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or invalid.
    """
    try:
        data = await service.get_return_distribution(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
            buckets=buckets,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[ReturnDistribution]](data=data)


@router.get(
    "/rolling-winrate",
    response_model=ResponseEnvelope[list[RollingWinratePoint]],
    summary="Get Rolling Win Rate",
    description=(
        "Return a rolling win-rate series for the authenticated user's closed "
        "trades, ordered chronologically by ``closed_at``.\n\n"
        "**What each point contains:**\n"
        "- `trade_index`: zero-based ordinal position in the series.\n"
        "- `closed_at`: UTC timestamp of the trade at this index.\n"
        "- `rolling_winrate`: fraction of wins in the sliding window ending "
        "at this trade (0.0–1.0).\n"
        "- `window`: actual window size at this point (grows up to "
        "``window_trades`` for the first trades).\n\n"
        "**Window:** the ``window_trades`` parameter controls the sliding "
        f"window size ({ROLLING_WINRATE_MIN_WINDOW}–{ROLLING_WINRATE_MAX_WINDOW} "
        f"trades, default {ROLLING_WINRATE_DEFAULT_WINDOW}).\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow "
        "the result by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=(
        "A chronologically ordered list of rolling win-rate data points, wrapped in a ResponseEnvelope. Empty list when no closed trades exist."
    ),
    responses={
        200: {"description": "Rolling win-rate series successfully returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {
            "description": (
                "Query parameter validation error. Check that dates are valid "
                "ISO-8601 strings and ``window_trades`` is between "
                f"{ROLLING_WINRATE_MIN_WINDOW} and {ROLLING_WINRATE_MAX_WINDOW}."
            )
        },
    },
)
async def get_rolling_winrate(
    portfolio_id: uuid.UUID,
    service: Annotated[TimeSeriesService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    window_trades: Annotated[
        int,
        Query(
            ge=ROLLING_WINRATE_MIN_WINDOW,
            le=ROLLING_WINRATE_MAX_WINDOW,
            description=(
                f"Sliding window size in number of trades. "
                f"Must be between {ROLLING_WINRATE_MIN_WINDOW} and "
                f"{ROLLING_WINRATE_MAX_WINDOW}. "
                f"Defaults to {ROLLING_WINRATE_DEFAULT_WINDOW}."
            ),
            examples=[20, 10, 50],
        ),
    ] = ROLLING_WINRATE_DEFAULT_WINDOW,
    account_id: Annotated[
        uuid.UUID | None,
        Query(description=("Optional account UUID to restrict results to a single account. When omitted, all of the user's accounts are included.")),
    ] = None,
    from_dt: Annotated[
        datetime | None,
        Query(
            alias="from_dt",
            description=("Optional ISO-8601 datetime lower bound (inclusive) on ``closed_at``. When omitted, no lower bound is applied."),
            examples=["2024-01-01T00:00:00Z"],
        ),
    ] = None,
    to_dt: Annotated[
        datetime | None,
        Query(
            alias="to_dt",
            description=("Optional ISO-8601 datetime upper bound (inclusive) on ``closed_at``. When omitted, no upper bound is applied."),
            examples=["2024-12-31T23:59:59Z"],
        ),
    ] = None,
) -> ResponseEnvelope[list[RollingWinratePoint]]:
    """Return a rolling win-rate series for the current user's closed trades.

    Args:
        service: Injected time-series service.
        current_user: The currently authenticated user.
        window_trades: Sliding window size in number of trades (5–100, default 20).
        account_id: Optional account UUID filter.
        from_dt: Optional inclusive lower bound on ``closed_at``.
        to_dt: Optional inclusive upper bound on ``closed_at``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains a chronologically ordered list of
        :class:`~app.schemas.timeseries.RollingWinratePoint` DTOs.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or invalid.
    """
    try:
        data = await service.get_rolling_winrate(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            window_trades=window_trades,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[RollingWinratePoint]](data=data)


@router.get(
    "/monthly-winrate",
    response_model=ResponseEnvelope[list[MonthlyWinratePoint]],
    summary="Get Monthly Win Rate",
    description=(
        "Return per-calendar-month win-rate statistics for the authenticated "
        "user's closed trades.\n\n"
        "**What each point contains:**\n"
        "- `year` / `month`: the calendar month.\n"
        "- `label`: human-readable label (e.g. ``'May 2024'``).\n"
        "- `win_rate`: fraction of winning trades (PnL > 0) for this month (0.0–1.0).\n"
        "- `win_count`: number of trades with PnL > 0.\n"
        "- `loss_count`: number of trades with PnL ≤ 0.\n"
        "- `trade_count`: total closed trades in this month.\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow "
        "the result by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required."
    ),
    response_description=(
        "A chronologically ordered list of monthly win-rate data points, wrapped in a ResponseEnvelope. Empty list when no closed trades exist."
    ),
    responses={
        200: {"description": "Monthly win-rate series successfully returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
    },
)
async def get_monthly_winrate(
    portfolio_id: uuid.UUID,
    service: Annotated[TimeSeriesService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    account_id: Annotated[
        uuid.UUID | None,
        Query(description=("Optional account UUID to restrict results to a single account. When omitted, all of the user's accounts are included.")),
    ] = None,
    from_dt: Annotated[
        datetime | None,
        Query(
            alias="from_dt",
            description=("Optional ISO-8601 datetime lower bound (inclusive) on ``closed_at``. When omitted, no lower bound is applied."),
            examples=["2024-01-01T00:00:00Z"],
        ),
    ] = None,
    to_dt: Annotated[
        datetime | None,
        Query(
            alias="to_dt",
            description=("Optional ISO-8601 datetime upper bound (inclusive) on ``closed_at``. When omitted, no upper bound is applied."),
            examples=["2024-12-31T23:59:59Z"],
        ),
    ] = None,
) -> ResponseEnvelope[list[MonthlyWinratePoint]]:
    """Return per-month win-rate statistics for the current user's closed trades.

    Args:
        service: Injected time-series service.
        current_user: The currently authenticated user.
        account_id: Optional account UUID filter.
        from_dt: Optional inclusive lower bound on ``closed_at``.
        to_dt: Optional inclusive upper bound on ``closed_at``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains a chronologically ordered list of
        :class:`~app.schemas.timeseries.MonthlyWinratePoint` DTOs.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or invalid.
    """
    try:
        data = await service.get_monthly_winrate(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[MonthlyWinratePoint]](data=data)
