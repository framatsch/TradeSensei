"""Route handlers for annotation definition management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    AnnotationDefinitionNotFoundError,
    AnnotationDefinitionValidationError,
)
from app.models.user import User
from app.schemas.annotation_definition import (
    AnnotationDefinitionCreate,
    AnnotationDefinitionResponse,
    AnnotationDefinitionUpdate,
)
from app.schemas.common import ResponseEnvelope
from app.services.annotation_definition_service import AnnotationDefinitionService

router = APIRouter(prefix="/annotation-definitions", tags=["annotation-definitions"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> AnnotationDefinitionService:
    """Build annotation definition service from request session."""
    return AnnotationDefinitionService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[AnnotationDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create annotation definition",
)
async def create_annotation_definition(
    payload: AnnotationDefinitionCreate,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[AnnotationDefinitionResponse]:
    """Create an annotation definition."""
    try:
        created = await service.create(user_id=_current_user.id, payload=payload)
    except AnnotationDefinitionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ResponseEnvelope[AnnotationDefinitionResponse](data=created)


@router.get(
    "",
    response_model=ResponseEnvelope[list[AnnotationDefinitionResponse]],
    summary="List annotation definitions",
)
async def list_annotation_definitions(
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
    scope: Annotated[str | None, Query()] = None,
) -> ResponseEnvelope[list[AnnotationDefinitionResponse]]:
    """List non-archived annotation definitions with optional scope filter."""
    items = await service.list(user_id=_current_user.id, scope=scope)
    return ResponseEnvelope[list[AnnotationDefinitionResponse]](data=items)


@router.get(
    "/{definition_id}",
    response_model=ResponseEnvelope[AnnotationDefinitionResponse],
    summary="Get annotation definition",
)
async def get_annotation_definition(
    definition_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[AnnotationDefinitionResponse]:
    """Get annotation definition by id, including archived definitions."""
    try:
        item = await service.get(user_id=_current_user.id, definition_id=definition_id)
    except AnnotationDefinitionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope[AnnotationDefinitionResponse](data=item)


@router.put(
    "/{definition_id}",
    response_model=ResponseEnvelope[AnnotationDefinitionResponse],
    summary="Update annotation definition",
)
async def update_annotation_definition(
    definition_id: uuid.UUID,
    payload: AnnotationDefinitionUpdate,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[AnnotationDefinitionResponse]:
    """Update annotation definition fields."""
    try:
        updated = await service.update(user_id=_current_user.id, definition_id=definition_id, payload=payload)
    except AnnotationDefinitionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AnnotationDefinitionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ResponseEnvelope[AnnotationDefinitionResponse](data=updated)


@router.delete(
    "/{definition_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Delete annotation definition",
)
async def delete_annotation_definition(
    definition_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[AnnotationDefinitionResponse] | Response:
    """Delete annotation definition; archives instead when assignments exist."""
    try:
        result = await service.delete(user_id=_current_user.id, definition_id=definition_id)
    except AnnotationDefinitionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return ResponseEnvelope[AnnotationDefinitionResponse](data=result)
