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
    show_archived: Annotated[bool, Query()] = False,
) -> ResponseEnvelope[list[AnnotationDefinitionResponse]]:
    """List annotation definitions with optional scope filter. Excludes archived by default."""
    items = await service.list(user_id=_current_user.id, scope=scope, show_archived=show_archived)
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
    responses={204: {"description": "Definition permanently deleted (no assignments)."}},
    summary="Delete annotation definition",
)
async def delete_annotation_definition(
    definition_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
    force: bool = False,
) -> ResponseEnvelope[AnnotationDefinitionResponse] | Response:
    """Delete annotation definition; archives instead when assignments exist, unless force=True."""
    try:
        result = await service.delete(user_id=_current_user.id, definition_id=definition_id, force=force)
    except AnnotationDefinitionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return ResponseEnvelope[AnnotationDefinitionResponse](data=result)


@router.patch(
    "/{definition_id}/archive",
    response_model=ResponseEnvelope[AnnotationDefinitionResponse],
    summary="Archive annotation definition",
)
async def archive_annotation_definition(
    definition_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[AnnotationDefinitionResponse]:
    """Archive an annotation definition."""
    try:
        result = await service.archive(definition_id=definition_id, user_id=_current_user.id)
    except AnnotationDefinitionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope[AnnotationDefinitionResponse](data=result)


@router.patch(
    "/{definition_id}/unarchive",
    response_model=ResponseEnvelope[AnnotationDefinitionResponse],
    summary="Unarchive annotation definition",
)
async def unarchive_annotation_definition(
    definition_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[AnnotationDefinitionResponse]:
    """Unarchive an annotation definition."""
    try:
        result = await service.unarchive(definition_id=definition_id, user_id=_current_user.id)
    except AnnotationDefinitionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope[AnnotationDefinitionResponse](data=result)


@router.get(
    "/{definition_id}/assignments/count",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Get annotation definition assignment counts",
)
async def get_annotation_definition_assignments_count(
    definition_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AnnotationDefinitionService, Depends(_get_service)],
) -> ResponseEnvelope[dict[str, int]]:
    """Return assignment counts (trades, checkins) for an annotation definition."""
    try:
        counts = await service.get_assignment_counts(definition_id=definition_id, user_id=_current_user.id)
    except AnnotationDefinitionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope[dict[str, int]](data=counts)
