"""Route handlers for the ``/api/v1/tags`` resource.

Provides full CRUD on tags, scoped to the authenticated user.
All endpoints require a valid Bearer token.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import TagNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services.tag_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TagService:
    """FastAPI dependency that constructs a :class:`TagService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`TagService` bound to the current session.
    """
    return TagService(session)


@router.get(
    "",
    response_model=ResponseEnvelope[list[TagRead]],
    summary="List Tags",
    description=(
        "Return all tags owned by the currently authenticated user, "
        "ordered by name ascending."
    ),
    response_description="A list of tags wrapped in a response envelope.",
    responses={
        200: {"description": "Tag list returned successfully."},
        401: {"description": "Missing or invalid Bearer token."},
    },
)
async def list_tags(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TagService, Depends(_get_service)],
) -> ResponseEnvelope[list[TagRead]]:
    """Return all tags for the authenticated user.

    Args:
        current_user: Injected authenticated user ORM instance.
        service: Injected tag service.

    Returns:
        A :class:`ResponseEnvelope` containing a list of
        :class:`TagRead` DTOs.
    """
    tags = await service.list_tags(current_user.id)
    return ResponseEnvelope[list[TagRead]](data=tags)


@router.post(
    "",
    response_model=ResponseEnvelope[TagRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a Tag",
    description=(
        "Create a new tag owned by the currently authenticated user. "
        "Tag names must be unique per user."
    ),
    response_description="The newly created tag wrapped in a response envelope.",
    responses={
        201: {"description": "Tag created successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def create_tag(
    payload: TagCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TagService, Depends(_get_service)],
) -> ResponseEnvelope[TagRead]:
    """Create a new tag for the authenticated user.

    Args:
        payload: Validated tag creation data.
        current_user: Injected authenticated user ORM instance.
        service: Injected tag service.

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`TagRead` DTO.
    """
    tag = await service.create_tag(payload, current_user.id)
    return ResponseEnvelope[TagRead](data=tag)


@router.get(
    "/{tag_id}",
    response_model=ResponseEnvelope[TagRead],
    summary="Get a Tag",
    description=(
        "Retrieve a single tag by its UUID. Returns 404 if the tag does not "
        "exist or belongs to a different user."
    ),
    response_description="The requested tag wrapped in a response envelope.",
    responses={
        200: {"description": "Tag found and returned."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Tag not found."},
        422: {"description": "The supplied ``tag_id`` is not a valid UUID."},
    },
)
async def get_tag(
    tag_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TagService, Depends(_get_service)],
) -> ResponseEnvelope[TagRead]:
    """Retrieve a single tag owned by the authenticated user.

    Args:
        tag_id: UUID path parameter identifying the tag.
        current_user: Injected authenticated user ORM instance.
        service: Injected tag service.

    Returns:
        A :class:`ResponseEnvelope` containing the :class:`TagRead` DTO.

    Raises:
        HTTPException: 404 if the tag is not found for this user.
    """
    try:
        tag = await service.get_tag(tag_id, current_user.id)
    except TagNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found."
        ) from exc
    return ResponseEnvelope[TagRead](data=tag)


@router.patch(
    "/{tag_id}",
    response_model=ResponseEnvelope[TagRead],
    summary="Update a Tag",
    description=(
        "Apply a partial update to a tag owned by the authenticated user. "
        "Only fields present in the request body are modified."
    ),
    response_description=(
        "The tag after applying the partial update, wrapped in a response envelope."
    ),
    responses={
        200: {"description": "Tag updated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Tag not found."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def update_tag(
    tag_id: uuid.UUID,
    payload: TagUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TagService, Depends(_get_service)],
) -> ResponseEnvelope[TagRead]:
    """Partially update a tag owned by the authenticated user.

    Args:
        tag_id: UUID path parameter identifying the tag.
        payload: Partial update data.
        current_user: Injected authenticated user ORM instance.
        service: Injected tag service.

    Returns:
        A :class:`ResponseEnvelope` containing the updated
        :class:`TagRead` DTO.

    Raises:
        HTTPException: 404 if the tag is not found for this user.
    """
    try:
        tag = await service.update_tag(tag_id, payload, current_user.id)
    except TagNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found."
        ) from exc
    return ResponseEnvelope[TagRead](data=tag)


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Tag",
    description=(
        "Permanently delete a tag. The tag will be detached from all trades "
        "automatically (cascade delete on ``trade_tags``). "
        "Returns 404 if the tag does not exist or belongs to a different user."
    ),
    response_description="No content — the tag has been deleted.",
    responses={
        204: {"description": "Tag deleted successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Tag not found."},
        422: {"description": "The supplied ``tag_id`` is not a valid UUID."},
    },
)
async def delete_tag(
    tag_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TagService, Depends(_get_service)],
) -> None:
    """Delete a tag owned by the authenticated user.

    Args:
        tag_id: UUID path parameter identifying the tag.
        current_user: Injected authenticated user ORM instance.
        service: Injected tag service.

    Raises:
        HTTPException: 404 if the tag is not found for this user.
    """
    try:
        await service.delete_tag(tag_id, current_user.id)
    except TagNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found."
        ) from exc
