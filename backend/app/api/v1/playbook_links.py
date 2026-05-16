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

"""Route handlers for playbook external links."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import PlaybookLinkNotFoundError, PlaybookNotFoundError
from app.models.user import User
from app.schemas.playbook_link import PlaybookLinkCreate, PlaybookLinkResponse
from app.services.playbook_link_service import PlaybookLinkService

router = APIRouter(prefix="/playbooks", tags=["playbook-metadata"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> PlaybookLinkService:
    return PlaybookLinkService(session)


@router.get(
    "/{playbook_id}/links",
    response_model=list[PlaybookLinkResponse],
    summary="List links for playbook",
)
async def list_links(
    playbook_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookLinkService, Depends(_get_service)],
) -> list[PlaybookLinkResponse]:
    """Return all labeled links for a playbook."""
    try:
        return await service.list(playbook_id=playbook_id, user_id=current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{playbook_id}/links",
    response_model=PlaybookLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add labeled link to playbook",
)
async def create_link(
    playbook_id: uuid.UUID,
    payload: PlaybookLinkCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookLinkService, Depends(_get_service)],
) -> PlaybookLinkResponse:
    """Add a labeled external URL to a playbook."""
    try:
        return await service.create(
            playbook_id=playbook_id,
            user_id=current_user.id,
            payload=payload,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{playbook_id}/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete playbook link",
)
async def delete_link(
    playbook_id: uuid.UUID,
    link_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookLinkService, Depends(_get_service)],
) -> None:
    """Remove a labeled link from a playbook."""
    try:
        await service.delete(
            playbook_id=playbook_id,
            link_id=link_id,
            user_id=current_user.id,
        )
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PlaybookLinkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
