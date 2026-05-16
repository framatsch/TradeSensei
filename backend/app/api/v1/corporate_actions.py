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

"""Route handlers for the ``/api/v1/corporate-actions`` resource.

Provides CRUD for corporate actions (stock splits / reverse splits),
scoped to the authenticated user.  All endpoints require a valid Bearer token.

The ``ratio`` field should be computed by the frontend as ``after / before``
(e.g. for a 1-for-20 reverse split: ``ratio = 1 / 20 = 0.05``).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import CorporateActionNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.corporate_action import (
    CorporateActionCreateRequest,
    CorporateActionRead,
    CorporateActionUpdate,
)
from app.services.corporate_action_service import CorporateActionService

router = APIRouter(prefix="/corporate-actions", tags=["corporate-actions"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> CorporateActionService:
    """FastAPI dependency that constructs a :class:`CorporateActionService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`CorporateActionService` bound to the current session.
    """
    return CorporateActionService(session)


@router.get(
    "",
    response_model=ResponseEnvelope[list[CorporateActionRead]],
    summary="List Corporate Actions",
    description=("Return all corporate actions (stock splits / reverse splits) owned by the currently authenticated user, ordered by date ascending."),
    response_description=("A list of corporate actions wrapped in a response envelope."),
    responses={
        200: {"description": "Corporate action list returned successfully."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def list_corporate_actions(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CorporateActionService, Depends(_get_service)],
) -> ResponseEnvelope[list[CorporateActionRead]]:
    """Return all corporate actions for the authenticated user.

    Args:
        current_user: Injected authenticated user ORM instance.
        service: Injected corporate action service.

    Returns:
        A :class:`ResponseEnvelope` containing a list of
        :class:`CorporateActionRead` DTOs.
    """
    actions = await service.list_corporate_actions(current_user.id)
    return ResponseEnvelope[list[CorporateActionRead]](data=actions)


@router.post(
    "",
    response_model=ResponseEnvelope[CorporateActionRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a Corporate Action",
    description=(
        "Record a new corporate action (stock split or reverse split) for the "
        "authenticated user.  The ``ratio`` should be supplied as "
        "``after_shares / before_shares`` (e.g. ``0.05`` for a 1:20 reverse "
        "split, ``2.0`` for a 2:1 forward split).  The ``old_conid`` and "
        "``new_conid`` fields are optional and only relevant for IBKR imports "
        "where the broker reassigns a new contract ID after the split."
    ),
    response_description=("The newly created corporate action wrapped in a response envelope."),
    responses={
        201: {"description": "Corporate action created successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def create_corporate_action(
    payload: CorporateActionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CorporateActionService, Depends(_get_service)],
) -> ResponseEnvelope[CorporateActionRead]:
    """Create a new corporate action for the authenticated user.

    Args:
        payload: Validated corporate action creation data.  The ``user_id``
            is injected from the JWT claim — do not include it in the request.
        current_user: Injected authenticated user ORM instance.
        service: Injected corporate action service.

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`CorporateActionRead` DTO.
    """
    create_schema = payload.to_corporate_action_create(current_user.id)
    action = await service.create_corporate_action(create_schema, current_user.id)
    return ResponseEnvelope[CorporateActionRead](data=action)


@router.put(
    "/{corporate_action_id}",
    response_model=ResponseEnvelope[CorporateActionRead],
    summary="Update a Corporate Action",
    description=(
        "Apply a partial update to a corporate action owned by the authenticated "
        "user.  Only fields present in the request body are modified.  Returns "
        "404 if the record does not exist or belongs to a different user."
    ),
    response_description=("The corporate action after applying the update, wrapped in a response envelope."),
    responses={
        200: {"description": "Corporate action updated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Corporate action not found."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def update_corporate_action(
    corporate_action_id: uuid.UUID,
    payload: CorporateActionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CorporateActionService, Depends(_get_service)],
) -> ResponseEnvelope[CorporateActionRead]:
    """Partially update a corporate action owned by the authenticated user.

    Args:
        corporate_action_id: UUID path parameter identifying the record.
        payload: Partial update data.  Only supplied fields are changed.
        current_user: Injected authenticated user ORM instance.
        service: Injected corporate action service.

    Returns:
        A :class:`ResponseEnvelope` containing the updated
        :class:`CorporateActionRead` DTO.

    Raises:
        HTTPException: 404 if the record is not found for this user.
    """
    try:
        action = await service.update_corporate_action(corporate_action_id, payload, current_user.id)
    except CorporateActionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corporate action not found.",
        ) from exc
    return ResponseEnvelope[CorporateActionRead](data=action)


@router.delete(
    "/{corporate_action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Corporate Action",
    description=(
        "Permanently delete a corporate action owned by the authenticated user. Returns 404 if the record does not exist or belongs to a different user."
    ),
    response_description="No content — the corporate action has been deleted.",
    responses={
        204: {"description": "Corporate action deleted successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Corporate action not found."},
        422: {"description": "The supplied ``corporate_action_id`` is not a valid UUID."},
    },
)
async def delete_corporate_action(
    corporate_action_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CorporateActionService, Depends(_get_service)],
) -> None:
    """Delete a corporate action owned by the authenticated user.

    Args:
        corporate_action_id: UUID path parameter identifying the record.
        current_user: Injected authenticated user ORM instance.
        service: Injected corporate action service.

    Raises:
        HTTPException: 404 if the record is not found for this user.
    """
    try:
        await service.delete_corporate_action(corporate_action_id, current_user.id)
    except CorporateActionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corporate action not found.",
        ) from exc
