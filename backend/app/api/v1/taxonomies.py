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

"""Route handlers for taxonomy definition management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import TaxonomyNotFoundError, TaxonomyValidationError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.taxonomy import TaxonomyCreate, TaxonomyResponse, TaxonomyUpdate
from app.services.taxonomy_service import TaxonomyService

router = APIRouter(prefix="/taxonomies", tags=["taxonomies"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> TaxonomyService:
    """Build taxonomy service from request session."""
    return TaxonomyService(session)


@router.post(
    "",
    response_model=ResponseEnvelope[TaxonomyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create taxonomy",
)
async def create_taxonomy(
    payload: TaxonomyCreate,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
) -> ResponseEnvelope[TaxonomyResponse]:
    """Create a taxonomy definition."""
    try:
        created = await service.create(user_id=_current_user.id, payload=payload)
    except TaxonomyValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ResponseEnvelope[TaxonomyResponse](data=created)


@router.get(
    "",
    response_model=ResponseEnvelope[list[TaxonomyResponse]],
    summary="List taxonomies",
)
async def list_taxonomies(
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
    scope: Annotated[str | None, Query()] = None,
    show_archived: Annotated[bool, Query()] = False,
) -> ResponseEnvelope[list[TaxonomyResponse]]:
    """List taxonomies with optional scope filter. Excludes archived by default."""
    items = await service.list(user_id=_current_user.id, scope=scope, show_archived=show_archived)
    return ResponseEnvelope[list[TaxonomyResponse]](data=items)


@router.get(
    "/{taxonomy_id}",
    response_model=ResponseEnvelope[TaxonomyResponse],
    summary="Get taxonomy",
)
async def get_taxonomy(
    taxonomy_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
) -> ResponseEnvelope[TaxonomyResponse]:
    """Get taxonomy by id, including archived definitions."""
    try:
        item = await service.get(user_id=_current_user.id, taxonomy_id=taxonomy_id)
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope[TaxonomyResponse](data=item)


@router.put(
    "/{taxonomy_id}",
    response_model=ResponseEnvelope[TaxonomyResponse],
    summary="Update taxonomy",
)
@router.patch(
    "/{taxonomy_id}",
    response_model=ResponseEnvelope[TaxonomyResponse],
    summary="Update taxonomy",
)
async def update_taxonomy(
    taxonomy_id: uuid.UUID,
    payload: TaxonomyUpdate,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
) -> ResponseEnvelope[TaxonomyResponse]:
    """Update taxonomy definition fields."""
    try:
        updated = await service.update(user_id=_current_user.id, taxonomy_id=taxonomy_id, payload=payload)
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaxonomyValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ResponseEnvelope[TaxonomyResponse](data=updated)


@router.delete(
    "/{taxonomy_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Delete taxonomy",
)
async def delete_taxonomy(
    taxonomy_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
    force: bool = False,
) -> ResponseEnvelope[TaxonomyResponse] | Response:
    """Delete taxonomy; archives instead when assignments exist, unless force=True."""
    try:
        result = await service.delete(user_id=_current_user.id, taxonomy_id=taxonomy_id, force=force)
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return ResponseEnvelope[TaxonomyResponse](data=result)


@router.patch(
    "/{taxonomy_id}/archive",
    response_model=ResponseEnvelope[TaxonomyResponse],
    summary="Archive taxonomy",
)
async def archive_taxonomy(
    taxonomy_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
) -> ResponseEnvelope[TaxonomyResponse]:
    """Archive a taxonomy definition."""
    try:
        result = await service.archive(taxonomy_id=taxonomy_id, user_id=_current_user.id)
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope[TaxonomyResponse](data=result)


@router.patch(
    "/{taxonomy_id}/unarchive",
    response_model=ResponseEnvelope[TaxonomyResponse],
    summary="Unarchive taxonomy",
)
async def unarchive_taxonomy(
    taxonomy_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
) -> ResponseEnvelope[TaxonomyResponse]:
    """Unarchive a taxonomy definition."""
    try:
        result = await service.unarchive(taxonomy_id=taxonomy_id, user_id=_current_user.id)
    except TaxonomyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResponseEnvelope[TaxonomyResponse](data=result)


@router.get(
    "/{taxonomy_id}/assignments/count",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Get taxonomy assignment counts",
)
async def get_taxonomy_assignments_count(
    taxonomy_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TaxonomyService, Depends(_get_service)],
) -> ResponseEnvelope[dict[str, int]]:
    """Return assignment counts (trades, checkins, playbooks) for a taxonomy."""
    counts = await service._repo.count_assignments(taxonomy_id)
    trade_count, checkin_count = counts[0], counts[1]
    playbook_count = counts[2] if len(counts) > 2 else 0
    total_count = trade_count + checkin_count + playbook_count
    return ResponseEnvelope[dict[str, int]](data={
        "trade_count": trade_count,
        "checkin_count": checkin_count,
        "playbook_count": playbook_count,
        "total_count": total_count,
    })
