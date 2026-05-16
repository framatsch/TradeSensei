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

"""Route handlers for playbook taxonomy assignments."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import (
    MetadataAssignmentNotFoundError,
    MetadataAssignmentValidationError,
    PlaybookNotFoundError,
    TaxonomyNotFoundError,
)
from app.models.user import User
from app.schemas.playbook_taxonomy import PlaybookTaxonomyCreate
from app.schemas.taxonomy import TaxonomyResponse
from app.services.playbook_taxonomy_service import PlaybookTaxonomyService

router = APIRouter(prefix="/playbooks", tags=["playbook-metadata"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> PlaybookTaxonomyService:
    return PlaybookTaxonomyService(session)


@router.get(
    "/{playbook_id}/taxonomies",
    response_model=list[TaxonomyResponse],
    summary="List taxonomy assignments for playbook",
)
async def list_playbook_taxonomies(
    playbook_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookTaxonomyService, Depends(_get_service)],
) -> list[TaxonomyResponse]:
    """Return all taxonomy assignments for a playbook."""
    try:
        return await service.list(playbook_id, current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{playbook_id}/taxonomies",
    status_code=status.HTTP_201_CREATED,
    summary="Assign taxonomy to playbook",
)
async def assign_playbook_taxonomy(
    playbook_id: uuid.UUID,
    payload: PlaybookTaxonomyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookTaxonomyService, Depends(_get_service)],
) -> None:
    """Assign a taxonomy with scope=playbook or scope=both to a playbook."""
    try:
        await service.assign(playbook_id, payload.taxonomy_id, current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentValidationError as exc:
        status_code = status.HTTP_409_CONFLICT if "already assigned" in str(exc) else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete(
    "/{playbook_id}/taxonomies/{taxonomy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove taxonomy from playbook",
)
async def remove_playbook_taxonomy(
    playbook_id: uuid.UUID,
    taxonomy_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PlaybookTaxonomyService, Depends(_get_service)],
) -> None:
    """Remove a taxonomy assignment from a playbook."""
    try:
        await service.remove(playbook_id, taxonomy_id, current_user.id)
    except PlaybookNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetadataAssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
