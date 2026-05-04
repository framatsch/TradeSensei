"""Route handlers for portfolio-scoped analytics endpoints."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import Spec5NotDeployedError
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.saved_dashboard_view_repository import (
    SavedDashboardViewRepository,
)
from app.schemas.analytics import (
    AnalyticsSummary,
    AnalyticsSummaryRequest,
    AttributionResponse,
    DashboardFilterConfig,
)
from app.schemas.common import ResponseEnvelope
from app.services.analytics_service import AnalyticsService
from app.services.attribution_service import AttributionService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_portfolio_owner)],
)


def _get_analytics_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> AnalyticsService:
    return AnalyticsService(session)


def _get_attribution_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> AttributionService:
    return AttributionService(session)


@router.post(
    "/summary",
    response_model=ResponseEnvelope[AnalyticsSummary],
    summary="Compute analytics summary",
    description=(
        "Compute server-side summary metrics for either inline filter_config "
        "or a saved view ID."
    ),
    response_description="Computed analytics summary payload.",
)
async def get_analytics_summary(
    portfolio_id: uuid.UUID,
    payload: AnalyticsSummaryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnalyticsService, Depends(_get_analytics_service)],
) -> ResponseEnvelope[AnalyticsSummary]:
    data = await service.get_summary(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        request=payload,
    )
    return ResponseEnvelope[AnalyticsSummary](data=data)


@router.get(
    "/correlations/market-phase",
    response_model=ResponseEnvelope[AttributionResponse],
    summary="Get market-phase attribution correlation",
    description=("Group trade metrics by DailyCheckin market phase for one portfolio."),
    response_description="Attribution buckets and exclusion counters.",
)
async def get_market_phase_correlation(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AttributionService, Depends(_get_attribution_service)],
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
    from_date: Annotated[
        date | None,
        Query(description="Optional inclusive start date for trade close date filter."),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(description="Optional inclusive end date for trade close date filter."),
    ] = None,
    view_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional saved dashboard view ID to reuse filter config."),
    ] = None,
) -> ResponseEnvelope[AttributionResponse]:
    portfolio = await PortfolioRepository(session).get_by_id(
        portfolio_id,
        current_user.id,
    )
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="portfolio not found",
        )

    if view_id is not None and (from_date is not None or to_date is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="use either view_id or from_date/to_date query filters",
        )

    if view_id is not None:
        view_repo = SavedDashboardViewRepository(session)
        view = await view_repo.get_by_id(view_id)
        if (
            view is None
            or view.user_id != current_user.id
            or view.portfolio_id != portfolio_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="view not found",
            )
        filter_config = DashboardFilterConfig.model_validate(view.filter_config)
    else:
        filter_config = DashboardFilterConfig(date_from=from_date, date_to=to_date)

    try:
        data = await service.get_market_phase_correlation(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            filter_config=filter_config,
        )
    except Spec5NotDeployedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    return ResponseEnvelope[AttributionResponse](data=data)
