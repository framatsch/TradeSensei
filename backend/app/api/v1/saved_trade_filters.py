import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.saved_trade_filter_repository import SavedTradeFilterRepository
from app.schemas.common import ResponseEnvelope
from app.schemas.saved_trade_filter import (
    SavedTradeFilterCreate,
    SavedTradeFilterRead,
    SavedTradeFilterUpdate,
)
from app.services.saved_trade_filter_service import SavedTradeFilterService

router = APIRouter()


def get_saved_trade_filter_service(
    session: AsyncSession = Depends(get_session),
) -> SavedTradeFilterService:
    """Dependency injection for the saved trade filter service."""
    repository = SavedTradeFilterRepository(session)
    return SavedTradeFilterService(repository)


@router.get(
    "",
    response_model=ResponseEnvelope[Sequence[SavedTradeFilterRead]],
    summary="List saved trade filters",
    description="List all system-level saved trade filters and user-owned ones.",
)
async def list_saved_trade_filters(
    user: User = Depends(get_current_user),
    service: SavedTradeFilterService = Depends(get_saved_trade_filter_service),
) -> ResponseEnvelope[Sequence[SavedTradeFilterRead]]:
    filters = await service.list_for_user(user.id)
    return ResponseEnvelope(data=filters)


@router.post(
    "",
    response_model=ResponseEnvelope[SavedTradeFilterRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a saved trade filter",
    description="Create a new user-owned saved trade filter.",
)
async def create_saved_trade_filter(
    payload: SavedTradeFilterCreate,
    user: User = Depends(get_current_user),
    service: SavedTradeFilterService = Depends(get_saved_trade_filter_service),
) -> ResponseEnvelope[SavedTradeFilterRead]:
    db_filter = await service.create_user_filter(
        user_id=user.id,
        name=payload.name,
        definition=payload.definition,
    )
    return ResponseEnvelope(data=db_filter)


@router.patch(
    "/{filter_id}",
    response_model=ResponseEnvelope[SavedTradeFilterRead],
    summary="Update a saved trade filter",
    description="Update an existing user-owned saved trade filter. System filters cannot be modified.",
)
async def update_saved_trade_filter(
    filter_id: uuid.UUID,
    payload: SavedTradeFilterUpdate,
    user: User = Depends(get_current_user),
    service: SavedTradeFilterService = Depends(get_saved_trade_filter_service),
) -> ResponseEnvelope[SavedTradeFilterRead]:
    db_filter = await service.update_user_filter(
        user_id=user.id,
        filter_id=filter_id,
        name=payload.name,
        definition=payload.definition,
    )
    return ResponseEnvelope(data=db_filter)


@router.delete(
    "/{filter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved trade filter",
    description="Delete a user-owned saved trade filter. System filters cannot be deleted.",
)
async def delete_saved_trade_filter(
    filter_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: SavedTradeFilterService = Depends(get_saved_trade_filter_service),
) -> None:
    await service.delete_user_filter(user_id=user.id, filter_id=filter_id)
