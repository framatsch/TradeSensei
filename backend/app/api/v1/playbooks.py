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

"""Route handlers for the ``/api/v1/playbooks`` resource.

Provides full CRUD on playbooks, scoped to the authenticated user.
All endpoints require a valid Bearer token.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import PlaybookNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.playbook import PlaybookCreate, PlaybookRead, PlaybookUpdate
from app.services.playbook_service import PlaybookService

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> PlaybookService:
    """FastAPI dependency that constructs a :class:`PlaybookService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`PlaybookService` bound to the current session.
    """
    return PlaybookService(session)


@router.get(
    "",
    response_model=ResponseEnvelope[list[PlaybookRead]],
    summary="List Playbooks",
    description=("Return all playbooks owned by the currently authenticated user, ordered by creation date ascending."),
    response_description="A list of playbooks wrapped in a response envelope.",
    responses={
        200: {"description": "Playbook list returned successfully."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def list_playbooks(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookService, Depends(_get_service)],
) -> ResponseEnvelope[list[PlaybookRead]]:
    """Return all playbooks for the authenticated user.

    Args:
        current_user: Injected authenticated user ORM instance.
        service: Injected playbook service.

    Returns:
        A :class:`ResponseEnvelope` containing a list of
        :class:`PlaybookRead` DTOs.
    """
    playbooks = await service.list_playbooks(current_user.id)
    return ResponseEnvelope[list[PlaybookRead]](data=playbooks)


@router.post(
    "",
    response_model=ResponseEnvelope[PlaybookRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a Playbook",
    description=("Create a new trading playbook owned by the currently authenticated user. Playbook names must be unique per user."),
    response_description="The newly created playbook wrapped in a response envelope.",
    responses={
        201: {"description": "Playbook created successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def create_playbook(
    payload: PlaybookCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookService, Depends(_get_service)],
) -> ResponseEnvelope[PlaybookRead]:
    """Create a new playbook for the authenticated user.

    Args:
        payload: Validated playbook creation data.
        current_user: Injected authenticated user ORM instance.
        service: Injected playbook service.

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`PlaybookRead` DTO.
    """
    playbook = await service.create_playbook(payload, current_user.id)
    return ResponseEnvelope[PlaybookRead](data=playbook)


@router.get(
    "/{playbook_id}",
    response_model=ResponseEnvelope[PlaybookRead],
    summary="Get a Playbook",
    description=("Retrieve a single playbook by its UUID. Returns 404 if the playbook does not exist or belongs to a different user."),
    response_description="The requested playbook wrapped in a response envelope.",
    responses={
        200: {"description": "Playbook found and returned."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Playbook not found."},
        422: {"description": "The supplied ``playbook_id`` is not a valid UUID."},
    },
)
async def get_playbook(
    playbook_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookService, Depends(_get_service)],
) -> ResponseEnvelope[PlaybookRead]:
    """Retrieve a single playbook owned by the authenticated user.

    Args:
        playbook_id: UUID path parameter identifying the playbook.
        current_user: Injected authenticated user ORM instance.
        service: Injected playbook service.

    Returns:
        A :class:`ResponseEnvelope` containing the :class:`PlaybookRead` DTO.

    Raises:
        HTTPException: 404 if the playbook is not found for this user.
    """
    try:
        playbook = await service.get_playbook(playbook_id, current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found.") from exc
    return ResponseEnvelope[PlaybookRead](data=playbook)


@router.patch(
    "/{playbook_id}",
    response_model=ResponseEnvelope[PlaybookRead],
    summary="Update a Playbook",
    description=("Apply a partial update to a playbook owned by the authenticated user. Only fields present in the request body are modified."),
    response_description=("The playbook after applying the partial update, wrapped in a response envelope."),
    responses={
        200: {"description": "Playbook updated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Playbook not found."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def update_playbook(
    playbook_id: uuid.UUID,
    payload: PlaybookUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookService, Depends(_get_service)],
) -> ResponseEnvelope[PlaybookRead]:
    """Partially update a playbook owned by the authenticated user.

    Args:
        playbook_id: UUID path parameter identifying the playbook.
        payload: Partial update data.
        current_user: Injected authenticated user ORM instance.
        service: Injected playbook service.

    Returns:
        A :class:`ResponseEnvelope` containing the updated
        :class:`PlaybookRead` DTO.

    Raises:
        HTTPException: 404 if the playbook is not found for this user.
    """
    try:
        playbook = await service.update_playbook(playbook_id, payload, current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found.") from exc
    return ResponseEnvelope[PlaybookRead](data=playbook)


@router.delete(
    "/{playbook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Playbook",
    description=(
        "Permanently delete a playbook. Trades that reference this playbook "
        "will have their ``playbook_id`` set to null (ON DELETE SET NULL). "
        "Returns 404 if the playbook does not exist or belongs to a different user."
    ),
    response_description="No content — the playbook has been deleted.",
    responses={
        204: {"description": "Playbook deleted successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Playbook not found."},
        422: {"description": "The supplied ``playbook_id`` is not a valid UUID."},
    },
)
async def delete_playbook(
    playbook_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookService, Depends(_get_service)],
) -> None:
    """Delete a playbook owned by the authenticated user.

    Args:
        playbook_id: UUID path parameter identifying the playbook.
        current_user: Injected authenticated user ORM instance.
        service: Injected playbook service.

    Raises:
        HTTPException: 404 if the playbook is not found for this user.
    """
    try:
        await service.delete_playbook(playbook_id, current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found.") from exc
