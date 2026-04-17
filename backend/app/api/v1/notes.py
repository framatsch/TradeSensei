"""Route handlers for the ``/api/v1/trades/{trade_id}/notes`` resource.

Provides full CRUD for trade notes nested under a specific trade.
All endpoints require a valid Bearer token.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
from app.core.exceptions import NoteNotFoundError
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.note import TradeNoteCreate, TradeNoteRead, TradeNoteUpdate
from app.services.note_service import NoteService

router = APIRouter(
    prefix="/trades/{trade_id}/notes",
    tags=["notes"],
)


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> NoteService:
    """FastAPI dependency that constructs a :class:`NoteService`.

    Args:
        session: Injected async database session.

    Returns:
        A :class:`NoteService` bound to the current session.
    """
    return NoteService(session)


@router.get(
    "",
    response_model=ResponseEnvelope[list[TradeNoteRead]],
    summary="List Trade Notes",
    description=(
        "Return all notes attached to the specified trade, ordered by "
        "``created_at`` ascending. Only notes belonging to the authenticated "
        "user are returned."
    ),
    response_description="A list of trade notes wrapped in a response envelope.",
    responses={
        200: {"description": "Note list returned successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        422: {"description": "The supplied ``trade_id`` is not a valid UUID."},
    },
)
async def list_notes(
    trade_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NoteService, Depends(_get_service)],
) -> ResponseEnvelope[list[TradeNoteRead]]:
    """Return all notes for the given trade belonging to the authenticated user.

    Args:
        trade_id: UUID path parameter identifying the parent trade.
        current_user: Injected authenticated user ORM instance.
        service: Injected note service.

    Returns:
        A :class:`ResponseEnvelope` containing a list of
        :class:`TradeNoteRead` DTOs.
    """
    notes = await service.list_notes(trade_id, current_user.id)
    return ResponseEnvelope[list[TradeNoteRead]](data=notes)


@router.post(
    "",
    response_model=ResponseEnvelope[TradeNoteRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add a Trade Note",
    description=(
        "Attach a new note to the specified trade. The note is scoped to the "
        "authenticated user."
    ),
    response_description="The newly created trade note wrapped in a response envelope.",
    responses={
        201: {"description": "Note created successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        422: {
            "description": (
                "Request payload failed schema validation, or ``trade_id`` is "
                "not a valid UUID."
            )
        },
    },
)
async def create_note(
    trade_id: uuid.UUID,
    payload: TradeNoteCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NoteService, Depends(_get_service)],
) -> ResponseEnvelope[TradeNoteRead]:
    """Add a new note to the given trade.

    Args:
        trade_id: UUID path parameter identifying the parent trade.
        payload: Validated note creation data.
        current_user: Injected authenticated user ORM instance.
        service: Injected note service.

    Returns:
        A :class:`ResponseEnvelope` containing the created
        :class:`TradeNoteRead` DTO.
    """
    note = await service.add_note(trade_id, payload, current_user.id)
    return ResponseEnvelope[TradeNoteRead](data=note)


@router.patch(
    "/{note_id}",
    response_model=ResponseEnvelope[TradeNoteRead],
    summary="Update a Trade Note",
    description=(
        "Apply a partial update to a note. Only fields present in the request "
        "body are modified. Returns 404 if the note does not exist, belongs to "
        "a different trade, or belongs to a different user."
    ),
    response_description=(
        "The note after applying the partial update, wrapped in a response envelope."
    ),
    responses={
        200: {"description": "Note updated successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Note not found."},
        422: {"description": "Request payload failed schema validation."},
    },
)
async def update_note(
    trade_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: TradeNoteUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NoteService, Depends(_get_service)],
) -> ResponseEnvelope[TradeNoteRead]:
    """Partially update a trade note.

    Args:
        trade_id: UUID path parameter identifying the parent trade.
        note_id: UUID path parameter identifying the note to update.
        payload: Partial update data.
        current_user: Injected authenticated user ORM instance.
        service: Injected note service.

    Returns:
        A :class:`ResponseEnvelope` containing the updated
        :class:`TradeNoteRead` DTO.

    Raises:
        HTTPException: 404 if the note is not found for this user and trade.
    """
    try:
        note = await service.update_note(note_id, trade_id, payload, current_user.id)
    except NoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found."
        ) from exc
    return ResponseEnvelope[TradeNoteRead](data=note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Trade Note",
    description=(
        "Permanently delete a trade note. Returns 404 if the note does not "
        "exist, belongs to a different trade, or belongs to a different user."
    ),
    response_description="No content — the note has been deleted.",
    responses={
        204: {"description": "Note deleted successfully."},
        401: {"description": "Missing or invalid Bearer token."},
        404: {"description": "Note not found."},
        422: {
            "description": (
                "The supplied ``trade_id`` or ``note_id`` is not a valid UUID."
            )
        },
    },
)
async def delete_note(
    trade_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NoteService, Depends(_get_service)],
) -> None:
    """Delete a trade note.

    Args:
        trade_id: UUID path parameter identifying the parent trade.
        note_id: UUID path parameter identifying the note to delete.
        current_user: Injected authenticated user ORM instance.
        service: Injected note service.

    Raises:
        HTTPException: 404 if the note is not found for this user and trade.
    """
    try:
        await service.delete_note(note_id, trade_id, current_user.id)
    except NoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found."
        ) from exc
