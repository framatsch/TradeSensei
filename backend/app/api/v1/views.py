"""Route handlers for portfolio-scoped saved dashboard views."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_portfolio_owner
from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    SavedDashboardViewNotFoundError,
    SavedDashboardViewPermissionError,
)
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.saved_dashboard_view_repository import (
    SavedDashboardViewRepository,
)
from app.schemas.analytics import (
    SavedDashboardViewCreate,
    SavedDashboardViewRead,
    SavedDashboardViewUpdate,
)
from app.schemas.common import ResponseEnvelope
from app.services.cache_service import CacheService
from app.services.saved_dashboard_view_service import SavedDashboardViewService

router = APIRouter(
    prefix="/portfolios/{portfolio_id}/views",
    tags=["analytics-views"],
    dependencies=[Depends(require_portfolio_owner)],
)


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> SavedDashboardViewService:
    return SavedDashboardViewService(
        SavedDashboardViewRepository(session),
        PortfolioRepository(session),
        CacheService(),
    )


@router.post(
    "",
    response_model=ResponseEnvelope[SavedDashboardViewRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create saved dashboard view",
    description="Create a named analytics view scoped to one portfolio.",
    response_description="Created saved dashboard view payload.",
)
async def create_saved_dashboard_view(
    portfolio_id: uuid.UUID,
    payload: SavedDashboardViewCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedDashboardViewService, Depends(_get_service)],
) -> ResponseEnvelope[SavedDashboardViewRead]:
    try:
        model = await service.create_view(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
            payload=payload,
        )
    except SavedDashboardViewPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[SavedDashboardViewRead](
        data=SavedDashboardViewRead.model_validate(model)
    )


@router.get(
    "",
    response_model=ResponseEnvelope[list[SavedDashboardViewRead]],
    summary="List saved dashboard views",
    description="List all saved dashboard views for one portfolio.",
    response_description="Ordered list of saved dashboard views.",
)
async def list_saved_dashboard_views(
    portfolio_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedDashboardViewService, Depends(_get_service)],
) -> ResponseEnvelope[list[SavedDashboardViewRead]]:
    try:
        models = await service.list_views(
            portfolio_id=portfolio_id,
            user_id=current_user.id,
        )
    except SavedDashboardViewPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[list[SavedDashboardViewRead]](
        data=[SavedDashboardViewRead.model_validate(model) for model in models]
    )


@router.get(
    "/{view_id}",
    response_model=ResponseEnvelope[SavedDashboardViewRead],
    summary="Get saved dashboard view",
    description="Return one saved dashboard view by ID.",
    response_description="Saved dashboard view payload.",
)
async def get_saved_dashboard_view(
    portfolio_id: uuid.UUID,
    view_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedDashboardViewService, Depends(_get_service)],
) -> ResponseEnvelope[SavedDashboardViewRead]:
    try:
        model = await service.get_view(
            portfolio_id=portfolio_id,
            view_id=view_id,
            user_id=current_user.id,
        )
    except SavedDashboardViewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[SavedDashboardViewRead](
        data=SavedDashboardViewRead.model_validate(model)
    )


@router.patch(
    "/{view_id}",
    response_model=ResponseEnvelope[SavedDashboardViewRead],
    summary="Update saved dashboard view",
    description="Rename a saved view or update its filter configuration.",
    response_description="Updated saved dashboard view payload.",
)
async def update_saved_dashboard_view(
    portfolio_id: uuid.UUID,
    view_id: uuid.UUID,
    payload: SavedDashboardViewUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedDashboardViewService, Depends(_get_service)],
) -> ResponseEnvelope[SavedDashboardViewRead]:
    try:
        model = await service.update_view(
            portfolio_id=portfolio_id,
            view_id=view_id,
            user_id=current_user.id,
            payload=payload,
        )
    except SavedDashboardViewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[SavedDashboardViewRead](
        data=SavedDashboardViewRead.model_validate(model)
    )


@router.delete(
    "/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete saved dashboard view",
    description="Delete one saved dashboard view by ID.",
    response_description="No response body.",
)
async def delete_saved_dashboard_view(
    portfolio_id: uuid.UUID,
    view_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedDashboardViewService, Depends(_get_service)],
) -> None:
    try:
        await service.delete_view(
            portfolio_id=portfolio_id,
            view_id=view_id,
            user_id=current_user.id,
        )
    except SavedDashboardViewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
