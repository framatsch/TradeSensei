"""Route handlers for check-in field definitions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    CheckinFieldDefinitionNotFoundError,
    CheckinFieldDefinitionValidationError,
)
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.daily_checkin import (
    CheckinFieldDefinitionCreate,
    CheckinFieldDefinitionRead,
    CheckinFieldDefinitionUpdate,
)
from app.services.checkin_field_definition_service import (
    CheckinFieldDefinitionService,
)

router = APIRouter(prefix="/checkin-fields", tags=["checkin-fields"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> CheckinFieldDefinitionService:
    return CheckinFieldDefinitionService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[CheckinFieldDefinitionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create check-in field definition",
    description="Create a user-scoped check-in field definition.",
)
async def create_checkin_field(
    payload: CheckinFieldDefinitionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinFieldDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[CheckinFieldDefinitionRead]:
    try:
        item = await service.create_field(user_id=current_user.id, payload=payload)
    except CheckinFieldDefinitionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[CheckinFieldDefinitionRead](data=item)


@router.get(
    "",
    response_model=ResponseEnvelope[list[CheckinFieldDefinitionRead]],
    summary="List check-in field definitions",
    description=(
        "List user-scoped check-in field definitions with optional active filter."
    ),
)
async def list_checkin_fields(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinFieldDefinitionService, Depends(_get_service)],
    is_active: bool | None = None,
) -> ResponseEnvelope[list[CheckinFieldDefinitionRead]]:
    items = await service.list_fields(user_id=current_user.id, is_active=is_active)
    return ResponseEnvelope[list[CheckinFieldDefinitionRead]](data=items)


@router.patch(
    "/{field_id}",
    response_model=ResponseEnvelope[CheckinFieldDefinitionRead],
    summary="Update check-in field definition",
    description="Update mutable properties of a check-in field definition.",
)
async def update_checkin_field(
    field_id: uuid.UUID,
    payload: CheckinFieldDefinitionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinFieldDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[CheckinFieldDefinitionRead]:
    try:
        item = await service.update_field(
            user_id=current_user.id,
            field_id=field_id,
            payload=payload,
        )
    except CheckinFieldDefinitionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CheckinFieldDefinitionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope[CheckinFieldDefinitionRead](data=item)


@router.delete(
    "/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete check-in field definition",
    description="Delete one check-in field definition by id.",
)
async def delete_checkin_field(
    field_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CheckinFieldDefinitionService, Depends(_get_service)],
) -> None:
    try:
        await service.delete_field(user_id=current_user.id, field_id=field_id)
    except CheckinFieldDefinitionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
