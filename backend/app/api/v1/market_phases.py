"""Route handlers for market phase definitions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.daily_checkin import (
    MarketPhaseDefinitionCreate,
    MarketPhaseDefinitionRead,
    MarketPhaseDefinitionUpdate,
)
from app.services.market_phase_definition_service import (
    MarketPhaseDefinitionService,
)

router = APIRouter(prefix="/market-phases", tags=["market-phases"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> MarketPhaseDefinitionService:
    return MarketPhaseDefinitionService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[MarketPhaseDefinitionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create market phase definition",
    description="Create a user-scoped market phase definition.",
)
async def create_market_phase(
    payload: MarketPhaseDefinitionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MarketPhaseDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[MarketPhaseDefinitionRead]:
    item = await service.create_phase(user_id=current_user.id, payload=payload)
    return ResponseEnvelope[MarketPhaseDefinitionRead](data=item)


@router.get(
    "",
    response_model=ResponseEnvelope[list[MarketPhaseDefinitionRead]],
    summary="List market phase definitions",
    description=(
        "List user-scoped market phase definitions "
        "with optional active filter."
    ),
)
async def list_market_phases(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MarketPhaseDefinitionService, Depends(_get_service)],
    is_active: bool | None = None,
) -> ResponseEnvelope[list[MarketPhaseDefinitionRead]]:
    items = await service.list_phases(user_id=current_user.id, is_active=is_active)
    return ResponseEnvelope[list[MarketPhaseDefinitionRead]](data=items)


@router.patch(
    "/{phase_id}",
    response_model=ResponseEnvelope[MarketPhaseDefinitionRead],
    summary="Update market phase definition",
    description="Update mutable properties of a market phase definition.",
)
async def update_market_phase(
    phase_id: uuid.UUID,
    payload: MarketPhaseDefinitionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MarketPhaseDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[MarketPhaseDefinitionRead]:
    item = await service.update_phase(
        user_id=current_user.id,
        phase_id=phase_id,
        payload=payload,
    )
    return ResponseEnvelope[MarketPhaseDefinitionRead](data=item)
