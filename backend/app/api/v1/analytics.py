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

"""Route handlers for portfolio-scoped analytics endpoints."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RETURN_DISTRIBUTION_DEFAULT_BUCKETS
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
    AxisType,
    DashboardFilterConfig,
    MetadataCorrelationRequest,
    MetadataCorrelationResponse,
)
from app.schemas.common import ResponseEnvelope
from app.schemas.timeseries import ReturnDistribution
from app.services.analytics_service import AnalyticsService
from app.services.attribution_service import AttributionService
from app.services.metadata_correlation_service import MetadataCorrelationService

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


def _get_metadata_correlation_service() -> MetadataCorrelationService:
    return MetadataCorrelationService()


@router.post(
    "/correlations/metadata",
    response_model=ResponseEnvelope[MetadataCorrelationResponse],
    summary="Compute metadata correlation",
    description="Compute correlation between two checkin/trade metadata axes using optional dashboard filters.",
)
async def get_metadata_correlation(
    portfolio_id: uuid.UUID,
    payload: MetadataCorrelationRequest,
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
    service: Annotated[MetadataCorrelationService, Depends(_get_metadata_correlation_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[MetadataCorrelationResponse]:
    if payload.view_id is not None:
        view_repo = SavedDashboardViewRepository(session)
        view = await view_repo.get_by_id(payload.view_id)
        if view is None or view.user_id != current_user.id or view.portfolio_id != portfolio_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="view not found",
            )
        filter_config = DashboardFilterConfig.model_validate(view.filter_config)
    else:
        filter_config = payload.filter_config or DashboardFilterConfig()

    data = await service.get_correlation(
        session=session,
        portfolio_id=portfolio_id,
        x_axis_type=payload.x_axis_type,
        x_axis_id=payload.x_axis_id,
        y_axis_type=payload.y_axis_type,
        y_axis_id=payload.y_axis_id,
        date_from=filter_config.date_from,
        date_to=filter_config.date_to,
        account_ids=filter_config.account_ids,
        base_asset=payload.base_asset,
    )
    return ResponseEnvelope[MetadataCorrelationResponse](data=data)


@router.post(
    "/summary",
    response_model=ResponseEnvelope[AnalyticsSummary],
    summary="Compute analytics summary",
    description=("Compute server-side summary metrics for either inline filter_config or a saved view ID."),
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


@router.post(
    "/correlations/market-phase",
    response_model=ResponseEnvelope[AttributionResponse],
    summary="Compute market-phase attribution correlation",
    description=("Group trade metrics by DailyCheckin market phase for one portfolio using optional filters."),
    response_description="Attribution buckets and exclusion counters.",
)
async def get_market_phase_correlation(
    portfolio_id: uuid.UUID,
    payload: AnalyticsSummaryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AttributionService, Depends(_get_attribution_service)],
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
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

    if payload.view_id is not None:
        view_repo = SavedDashboardViewRepository(session)
        view = await view_repo.get_by_id(payload.view_id)
        if view is None or view.user_id != current_user.id or view.portfolio_id != portfolio_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="view not found",
            )
        filter_config = DashboardFilterConfig.model_validate(view.filter_config)
    else:
        filter_config = payload.filter_config or DashboardFilterConfig()

    try:
        data = await service.get_market_phase_correlation(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            filter_config=filter_config,
        )
    except Spec5NotDeployedError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return ResponseEnvelope[AttributionResponse](data=data)

@router.post(
    "/return-distribution",
    response_model=ResponseEnvelope[list[ReturnDistribution]],
    summary="Compute return distribution",
    description="Compute return distribution histogram using optional dashboard filters.",
)
async def get_analytics_return_distribution(
    portfolio_id: uuid.UUID,
    payload: AnalyticsSummaryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnalyticsService, Depends(_get_analytics_service)],
    buckets: int = Query(
        RETURN_DISTRIBUTION_DEFAULT_BUCKETS,
        description="Number of equal-width histogram bins.",
    ),
) -> ResponseEnvelope[list[ReturnDistribution]]:
    data = await service.get_return_distribution(
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        request=payload,
        buckets=buckets,
    )
    return ResponseEnvelope[list[ReturnDistribution]](data=data)
