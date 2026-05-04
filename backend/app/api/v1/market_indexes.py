"""Route handlers for market index definitions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.market_index import (
    MarketIndexDefinitionCreate,
    MarketIndexDefinitionResponse,
    MarketIndexDefinitionUpdate,
)
from app.services.market_index_definition_service import MarketIndexDefinitionService

router = APIRouter(prefix="/market-indexes", tags=["market-indexes"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> MarketIndexDefinitionService:
    return MarketIndexDefinitionService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[MarketIndexDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create market index definition",
    description="Create a user-scoped market index definition.",
)
async def create_market_index(
    payload: MarketIndexDefinitionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MarketIndexDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[MarketIndexDefinitionResponse]:
    item = await service.create_index(user_id=current_user.id, payload=payload)
    return ResponseEnvelope[MarketIndexDefinitionResponse](data=item)


@router.get(
    "",
    response_model=ResponseEnvelope[list[MarketIndexDefinitionResponse]],
    summary="List market index definitions",
    description=(
        "List user-scoped market index definitions with optional active filter."
    ),
)
async def list_market_indexes(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MarketIndexDefinitionService, Depends(_get_service)],
    is_active: bool | None = None,
) -> ResponseEnvelope[list[MarketIndexDefinitionResponse]]:
    items = await service.list_indices(user_id=current_user.id, is_active=is_active)
    return ResponseEnvelope[list[MarketIndexDefinitionResponse]](data=items)


@router.put(
    "/{index_id}",
    response_model=ResponseEnvelope[MarketIndexDefinitionResponse],
    summary="Update market index definition",
    description="Update mutable properties of a market index definition.",
)
async def update_market_index(
    index_id: uuid.UUID,
    payload: MarketIndexDefinitionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MarketIndexDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[MarketIndexDefinitionResponse]:
    item = await service.update_index(
        user_id=current_user.id,
        index_id=index_id,
        payload=payload,
    )
    return ResponseEnvelope[MarketIndexDefinitionResponse](data=item)


@router.delete(
    "/{index_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete market index definition",
    description="Delete one market index definition by id.",
)
async def delete_market_index(
    index_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MarketIndexDefinitionService, Depends(_get_service)],
) -> None:
    await service.delete_index(user_id=current_user.id, index_id=index_id)
