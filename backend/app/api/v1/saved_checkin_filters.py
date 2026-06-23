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

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    SavedCheckinFilterConflictError,
    SavedCheckinFilterNotFoundError,
)
from app.models.user import User
from app.repositories.saved_checkin_filter_repository import SavedCheckinFilterRepository
from app.schemas.common import ResponseEnvelope
from app.schemas.saved_checkin_filter import (
    SavedCheckinFilterCreate,
    SavedCheckinFilterResponse,
    SavedCheckinFilterUpdate,
)
from app.services.saved_checkin_filter_service import SavedCheckinFilterService

router = APIRouter(prefix="/checkins/filters", tags=["checkin-filters"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> SavedCheckinFilterService:
    repo = SavedCheckinFilterRepository(session)
    return SavedCheckinFilterService(repo)


@router.post(
    "",
    response_model=ResponseEnvelope[SavedCheckinFilterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create saved checkin filter",
    description="Save a new checkin filter configuration for the current user.",
)
async def create_saved_checkin_filter(
    schema: SavedCheckinFilterCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedCheckinFilterService, Depends(_get_service)],
) -> ResponseEnvelope[SavedCheckinFilterResponse]:
    try:
        filter_obj = await service.create(user_id=current_user.id, schema=schema)
        return ResponseEnvelope[SavedCheckinFilterResponse](data=filter_obj)  # type: ignore[arg-type]
    except SavedCheckinFilterConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=ResponseEnvelope[list[SavedCheckinFilterResponse]],
    summary="List saved checkin filters",
    description="List all saved checkin filter configurations for the current user.",
)
async def list_saved_checkin_filters(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedCheckinFilterService, Depends(_get_service)],
) -> ResponseEnvelope[list[SavedCheckinFilterResponse]]:
    filters = await service.list_by_user(user_id=current_user.id)
    return ResponseEnvelope[list[SavedCheckinFilterResponse]](data=filters)  # type: ignore[arg-type]


@router.put(
    "/{filter_id}",
    response_model=ResponseEnvelope[SavedCheckinFilterResponse],
    summary="Update saved checkin filter",
    description="Update an existing saved checkin filter configuration.",
)
async def update_saved_checkin_filter(
    filter_id: uuid.UUID,
    schema: SavedCheckinFilterUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedCheckinFilterService, Depends(_get_service)],
) -> ResponseEnvelope[SavedCheckinFilterResponse]:
    try:
        filter_obj = await service.update(
            user_id=current_user.id,
            filter_id=filter_id,
            schema=schema,
        )
        return ResponseEnvelope[SavedCheckinFilterResponse](data=filter_obj)  # type: ignore[arg-type]
    except SavedCheckinFilterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SavedCheckinFilterConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{filter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete saved checkin filter",
    description="Delete a saved checkin filter configuration.",
)
async def delete_saved_checkin_filter(
    filter_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedCheckinFilterService, Depends(_get_service)],
) -> None:
    try:
        await service.delete(user_id=current_user.id, filter_id=filter_id)
    except SavedCheckinFilterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
