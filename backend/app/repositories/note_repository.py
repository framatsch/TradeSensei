"""Async repository for the ``trade_notes`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_note import TradeNote
from app.schemas.note import TradeNoteCreate, TradeNoteUpdate


class NoteRepository:
    """Data-access object for the ``trade_notes`` table.

    Every query is scoped to both ``trade_id`` and ``user_id`` so that
    notes cannot be accessed across trade or user boundaries.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    async def get_by_id(
        self,
        note_id: uuid.UUID,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> TradeNote | None:
        """Retrieve a single note by primary key, scoped to a trade and user.

        Args:
            note_id: UUID of the note to fetch.
            trade_id: UUID of the parent trade — enforces ownership.
            user_id: UUID of the requesting user — enforces isolation.

        Returns:
            The matching :class:`TradeNote`, or ``None`` if not found.
        """
        result = await self._session.execute(
            select(TradeNote).where(
                TradeNote.id == note_id,
                TradeNote.trade_id == trade_id,
                TradeNote.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_trade(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[TradeNote]:
        """Return all notes for a given trade, scoped to a user.

        Results are ordered by ``created_at`` ascending.

        Args:
            trade_id: UUID of the trade whose notes to list.
            user_id: UUID of the requesting user.

        Returns:
            A list of :class:`TradeNote` ORM instances (may be empty).
        """
        result = await self._session.execute(
            select(TradeNote)
            .where(
                TradeNote.trade_id == trade_id,
                TradeNote.user_id == user_id,
            )
            .order_by(TradeNote.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        data: TradeNoteCreate,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> TradeNote:
        """Persist a new trade note and return the flushed ORM instance.

        The session is *flushed* so the database assigns server defaults
        but not committed — the service layer commits.

        Args:
            data: Validated note creation payload.
            trade_id: UUID of the parent trade.
            user_id: UUID of the authoring user.

        Returns:
            The newly created :class:`TradeNote` with all server defaults
            populated.
        """
        note = TradeNote(
            trade_id=trade_id,
            user_id=user_id,
            content=data.content,
            emotion=data.emotion,
        )
        self._session.add(note)
        await self._session.flush()
        await self._session.refresh(note)
        return note

    async def update(
        self,
        note: TradeNote,
        data: TradeNoteUpdate,
    ) -> TradeNote:
        """Apply a partial update to an existing trade note.

        Only fields explicitly set in *data* (non-``None``) are written.
        The session is flushed but not committed.

        Args:
            note: The ORM instance to update.
            data: Validated partial update payload.

        Returns:
            The updated :class:`TradeNote` instance after flush.
        """
        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(note, field, value)
        self._session.add(note)
        await self._session.flush()
        await self._session.refresh(note)
        return note

    async def delete(self, note: TradeNote) -> None:
        """Delete a trade note from the database.

        The session is flushed but not committed.

        Args:
            note: The ORM instance to delete.
        """
        await self._session.delete(note)
        await self._session.flush()
