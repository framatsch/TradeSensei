# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Route handlers for the ``/api/v1/metrics`` resource."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.metrics import DrawdownPoint, EquityCurvePoint, MetricsSummary
from app.services.metrics_service import MetricsService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_portfolio_owner)],
)

_METRICS_SUNSET = "Sat, 01 Nov 2026 00:00:00 GMT"


def _set_deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _METRICS_SUNSET


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> MetricsService:
    """FastAPI dependency that constructs a :class:`MetricsService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`MetricsService` bound to the current session.
    """
    return MetricsService(session)


@router.get(
    "/summary",
    response_model=ResponseEnvelope[MetricsSummary],
    summary="Get Performance Metrics Summary",
    description=(
        "Compute and return the full performance metrics summary for the "
        "authenticated user's closed trades.\n\n"
        "**What is computed:**\n"
        "- Aggregate statistics: win rate, loss rate, profit factor, expectancy, "
        "Sharpe ratio, average win/loss, gross profit/loss, consecutive "
        "win/loss streaks, and average trade duration.\n"
        "- Equity curve: cumulative PnL from `starting_capital`, one point per "
        "closed trade, capped at 1 000 entries.\n"
        "- Drawdown curve: per-trade fractional and absolute drawdown from the "
        "running equity peak.\n"
        "- `max_drawdown` and `max_drawdown_abs`: the worst drawdown observed "
        "over the entire period.\n\n"
        "**Date filtering:** when `from_dt` or `to_dt` are supplied, only trades "
        "whose `closed_at` falls within the range (both bounds inclusive) are "
        "included. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required. Returns HTTP 401 "
        "if the token is missing, expired, or invalid."
    ),
    response_description=(
        "A complete metrics summary including aggregate TradeMetrics, "
        "max_drawdown, max_drawdown_abs, the equity curve, and the drawdown "
        "curve — all wrapped in a ResponseEnvelope."
    ),
    responses={
        200: {"description": "Metrics summary successfully computed and returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {"description": ("Query parameter validation error. Check that dates are valid ISO-8601 strings and starting_capital is a valid decimal.")},
    },
    deprecated=True,
)
async def get_metrics_summary(
    portfolio_id: uuid.UUID,
    service: Annotated[MetricsService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    response: Response,
    account_id: Annotated[
        uuid.UUID | None,
        Query(description=("Optional account UUID to restrict metrics to a single account. When omitted, all accounts belonging to the user are included.")),
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
    starting_capital: Annotated[
        Decimal,
        Query(
            description=(
                "Starting capital used as the equity baseline for the equity and "
                "drawdown curves. Defaults to zero, which means the curves show "
                "cumulative PnL only."
            ),
            examples=["10000.00", "0"],
        ),
    ] = Decimal("0"),
) -> ResponseEnvelope[MetricsSummary]:
    """Compute and return the full performance metrics summary for the current user.

    Fetches all qualifying closed trades (scoped to the authenticated user,
    optionally filtered by account and date range), then delegates computation
    to the service layer, which calls the pure utility functions for trade
    metrics, equity curve, and drawdown curve assembly.

    Args:
        service: Injected metrics service that orchestrates data access and
            computation.
        current_user: The currently authenticated user, resolved from the
            Bearer token by the ``get_current_user`` dependency.
        account_id: Optional UUID of a broker account. When supplied, only
            trades belonging to that account are included.
        from_dt: Optional inclusive lower bound on ``closed_at``. When
            ``None``, no lower bound is applied.
        to_dt: Optional inclusive upper bound on ``closed_at``. When
            ``None``, no upper bound is applied.
        starting_capital: Initial equity value placed before the first trade.
            Used as the baseline for both the equity curve and drawdown peak
            calculations. Defaults to ``Decimal("0")``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains a fully populated :class:`~app.schemas.metrics.MetricsSummary`.

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or
            otherwise invalid.
    """
    _set_deprecation_headers(response)
    try:
        summary = await service.get_summary(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
            starting_capital=starting_capital,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[MetricsSummary](data=summary)


@router.get(
    "/equity-curve",
    response_model=ResponseEnvelope[list[EquityCurvePoint]],
    summary="Get Equity Curve",
    description=(
        "Return the cumulative equity curve for the authenticated user's closed "
        "trades, sorted by `closed_at` ascending.\n\n"
        "**What each point contains:**\n"
        "- `timestamp`: the `closed_at` datetime of the trade.\n"
        "- `equity`: cumulative PnL from `starting_capital` up to and including "
        "this trade.\n"
        "- `pnl`: the individual PnL of this trade.\n\n"
        "**Cap:** the response is limited to 1 000 data points. When more trades "
        "exist in the requested range, the oldest 1 000 are returned.\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow the "
        "set of trades by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required. Returns HTTP 401 "
        "if the token is missing, expired, or invalid."
    ),
    response_description=(
        "An ordered list (ascending by timestamp) of equity curve data points, "
        "wrapped in a ResponseEnvelope. Empty list when the user has no closed "
        "trades in the requested range."
    ),
    responses={
        200: {"description": "Equity curve successfully computed and returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {"description": ("Query parameter validation error. Check that dates are valid ISO-8601 strings and starting_capital is a valid decimal.")},
    },
    deprecated=True,
)
async def get_equity_curve(
    portfolio_id: uuid.UUID,
    service: Annotated[MetricsService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    response: Response,
    account_id: Annotated[
        uuid.UUID | None,
        Query(
            description=("Optional account UUID to restrict the curve to a single account. When omitted, trades from all of the user's accounts are included.")
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
    starting_capital: Annotated[
        Decimal,
        Query(
            description=(
                "Starting capital used as the equity baseline. The first point's "
                "``equity`` value equals ``starting_capital + first_trade_pnl``. "
                "Defaults to zero."
            ),
            examples=["10000.00", "0"],
        ),
    ] = Decimal("0"),
) -> ResponseEnvelope[list[EquityCurvePoint]]:
    """Compute and return the equity curve for the current user.

    Fetches qualifying closed trades, computes cumulative PnL starting from
    ``starting_capital``, and returns up to 1 000 ordered data points.

    Args:
        service: Injected metrics service that orchestrates data access and
            computation.
        current_user: The currently authenticated user, resolved from the
            Bearer token by the ``get_current_user`` dependency.
        account_id: Optional UUID of a broker account. When supplied, only
            trades belonging to that account are included.
        from_dt: Optional inclusive lower bound on ``closed_at``. When
            ``None``, no lower bound is applied.
        to_dt: Optional inclusive upper bound on ``closed_at``. When
            ``None``, no upper bound is applied.
        starting_capital: Initial equity value placed before the first trade.
            Defaults to ``Decimal("0")``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains an ordered list of :class:`~app.schemas.metrics.EquityCurvePoint`
        DTOs (at most 1 000 entries).

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or
            otherwise invalid.
    """
    _set_deprecation_headers(response)
    try:
        curve = await service.get_equity_curve(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
            starting_capital=starting_capital,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[EquityCurvePoint]](data=curve)


@router.get(
    "/drawdown",
    response_model=ResponseEnvelope[list[DrawdownPoint]],
    summary="Get Drawdown Curve",
    description=(
        "Return the drawdown time series for the authenticated user's closed "
        "trades, sorted by `closed_at` ascending.\n\n"
        "**What each point contains:**\n"
        "- `timestamp`: the `closed_at` datetime of the trade.\n"
        "- `drawdown`: fractional drawdown from the running equity peak "
        "(0.0 to -1.0). For example, `-0.15` means the portfolio is 15 % "
        "below its peak at that moment.\n"
        "- `drawdown_abs`: absolute drawdown in account currency (always ≤ 0).\n\n"
        "**Peak initialisation:** the equity peak is seeded with "
        "`starting_capital`. If `starting_capital` is 0 (default), the peak "
        "starts at 0 and rises with each winning trade.\n\n"
        "**Cap:** the underlying equity curve is capped at 1 000 points before "
        "the drawdown is computed, so the drawdown series also has at most "
        "1 000 entries.\n\n"
        "**Date filtering:** `from_dt` and `to_dt` (both inclusive) narrow the "
        "set of trades by `closed_at`. Omitting both returns all-time data.\n\n"
        "**Authentication:** a valid Bearer token is required. Returns HTTP 401 "
        "if the token is missing, expired, or invalid."
    ),
    response_description=(
        "An ordered list (ascending by timestamp) of drawdown data points, "
        "wrapped in a ResponseEnvelope. Empty list when the user has no closed "
        "trades in the requested range."
    ),
    responses={
        200: {"description": "Drawdown curve successfully computed and returned."},
        401: {"description": ("Not authenticated. The Bearer token is missing, expired, or invalid.")},
        422: {"description": ("Query parameter validation error. Check that dates are valid ISO-8601 strings and starting_capital is a valid decimal.")},
    },
    deprecated=True,
)
async def get_drawdown_curve(
    portfolio_id: uuid.UUID,
    service: Annotated[MetricsService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    response: Response,
    account_id: Annotated[
        uuid.UUID | None,
        Query(
            description=(
                "Optional account UUID to restrict the drawdown curve to a single account. When omitted, all accounts belonging to the user are included."
            )
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
    starting_capital: Annotated[
        Decimal,
        Query(
            description=(
                "Starting capital used to seed the equity peak baseline. "
                "A higher value reduces the measured drawdown depth when early "
                "losses are small relative to capital. Defaults to zero."
            ),
            examples=["10000.00", "0"],
        ),
    ] = Decimal("0"),
) -> ResponseEnvelope[list[DrawdownPoint]]:
    """Compute and return the drawdown curve for the current user.

    Fetches qualifying closed trades, builds the equity curve capped at
    1 000 points, then derives the per-point fractional and absolute drawdown
    from the running equity peak seeded by ``starting_capital``.

    Args:
        service: Injected metrics service that orchestrates data access and
            computation.
        current_user: The currently authenticated user, resolved from the
            Bearer token by the ``get_current_user`` dependency.
        account_id: Optional UUID of a broker account. When supplied, only
            trades belonging to that account are included.
        from_dt: Optional inclusive lower bound on ``closed_at``. When
            ``None``, no lower bound is applied.
        to_dt: Optional inclusive upper bound on ``closed_at``. When
            ``None``, no upper bound is applied.
        starting_capital: Initial equity value used to seed the running peak.
            Defaults to ``Decimal("0")``.

    Returns:
        A :class:`~app.schemas.common.ResponseEnvelope` whose ``data`` field
        contains an ordered list of :class:`~app.schemas.metrics.DrawdownPoint`
        DTOs (at most 1 000 entries).

    Raises:
        HTTPException: 401 if the Bearer token is missing, expired, or
            otherwise invalid.
    """
    _set_deprecation_headers(response)
    try:
        curve = await service.get_drawdown_curve(
            user_id=current_user.id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            from_dt=from_dt,
            to_dt=to_dt,
            starting_capital=starting_capital,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[DrawdownPoint]](data=curve)
