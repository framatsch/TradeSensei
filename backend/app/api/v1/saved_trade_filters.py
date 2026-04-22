import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    SavedTradeFilterNotFoundError,
    SavedTradeFilterPermissionError,
    SavedTradeFilterValidationError,
)
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
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
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
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        SavedTradeFilterService, Depends(get_saved_trade_filter_service)
    ],
) -> ResponseEnvelope[Sequence[SavedTradeFilterRead]]:
    filters = await service.list_for_user(user.id)
    return ResponseEnvelope(
        data=[SavedTradeFilterRead.model_validate(f) for f in filters]
    )


@router.post(
    "",
    response_model=ResponseEnvelope[SavedTradeFilterRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a saved trade filter",
    description="Create a new user-owned saved trade filter.",
)
async def create_saved_trade_filter(
    payload: SavedTradeFilterCreate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        SavedTradeFilterService, Depends(get_saved_trade_filter_service)
    ],
) -> ResponseEnvelope[SavedTradeFilterRead]:
    db_filter = await service.create_user_filter(
        user_id=user.id,
        name=payload.name,
        definition=payload.definition,
    )
    return ResponseEnvelope(data=SavedTradeFilterRead.model_validate(db_filter))


@router.patch(
    "/{filter_id}",
    response_model=ResponseEnvelope[SavedTradeFilterRead],
    summary="Update a saved trade filter",
    description=(
        "Update an existing user-owned saved trade filter."
        " System filters cannot be modified."
    ),
)
async def update_saved_trade_filter(
    filter_id: uuid.UUID,
    payload: SavedTradeFilterUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        SavedTradeFilterService, Depends(get_saved_trade_filter_service)
    ],
) -> ResponseEnvelope[SavedTradeFilterRead]:
    try:
        db_filter = await service.update_user_filter(
            user_id=user.id,
            filter_id=filter_id,
            name=payload.name,
            definition=payload.definition,
        )
    except SavedTradeFilterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SavedTradeFilterPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except SavedTradeFilterValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(data=SavedTradeFilterRead.model_validate(db_filter))


@router.delete(
    "/{filter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved trade filter",
    description=(
        "Delete a user-owned saved trade filter. System filters cannot be deleted."
    ),
)
async def delete_saved_trade_filter(
    filter_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        SavedTradeFilterService, Depends(get_saved_trade_filter_service)
    ],
) -> None:
    try:
        await service.delete_user_filter(user_id=user.id, filter_id=filter_id)
    except SavedTradeFilterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SavedTradeFilterPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
