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

"""Business-logic service for trade note operations.

This layer orchestrates the repository and owns transaction semantics.
No HTTP concepts (``Request``, ``Response``, status codes) appear here.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NoteNotFoundError
from app.repositories.note_repository import NoteRepository
from app.schemas.note import TradeNoteCreate, TradeNoteRead, TradeNoteUpdate


class NoteService:
    """Service layer for trade note operations.

    All operations are scoped to both ``trade_id`` and ``user_id`` for
    data isolation.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request.
        """
        self._repo = NoteRepository(session)

    async def list_notes(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[TradeNoteRead]:
        """Return all notes for a given trade, scoped to a user.

        Args:
            trade_id: UUID of the trade whose notes to list.
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`TradeNoteRead` DTOs (may be empty).
        """
        notes = await self._repo.list_by_trade(trade_id, user_id)
        return [TradeNoteRead.model_validate(n) for n in notes]

    async def add_note(
        self,
        trade_id: uuid.UUID,
        data: TradeNoteCreate,
        user_id: uuid.UUID,
    ) -> TradeNoteRead:
        """Add a new note to a trade.

        Args:
            trade_id: UUID of the trade to annotate.
            data: Validated note creation payload.
            user_id: UUID of the authenticated user (note author).

        Returns:
            A :class:`TradeNoteRead` DTO for the newly created note.
        """
        note = await self._repo.create(data, trade_id, user_id)
        return TradeNoteRead.model_validate(note)

    async def update_note(
        self,
        note_id: uuid.UUID,
        trade_id: uuid.UUID,
        data: TradeNoteUpdate,
        user_id: uuid.UUID,
    ) -> TradeNoteRead:
        """Apply a partial update to an existing trade note.

        Args:
            note_id: UUID of the note to update.
            trade_id: UUID of the parent trade — used to scope the query.
            data: Validated partial update payload.
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`TradeNoteRead` DTO reflecting the updated state.

        Raises:
            NoteNotFoundError: If no note with that ID exists for the
                requesting user and trade combination.
        """
        note = await self._repo.get_by_id(note_id, trade_id, user_id)
        if note is None:
            raise NoteNotFoundError(f"Note {note_id} not found.")
        updated = await self._repo.update(note, data)
        return TradeNoteRead.model_validate(updated)

    async def delete_note(
        self,
        note_id: uuid.UUID,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete a trade note.

        Args:
            note_id: UUID of the note to delete.
            trade_id: UUID of the parent trade — used to scope the query.
            user_id: UUID of the authenticated user.

        Raises:
            NoteNotFoundError: If no note with that ID exists for the
                requesting user and trade combination.
        """
        note = await self._repo.get_by_id(note_id, trade_id, user_id)
        if note is None:
            raise NoteNotFoundError(f"Note {note_id} not found.")
        await self._repo.delete(note)
