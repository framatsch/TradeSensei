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

"""Unit tests for NoteService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import NoteNotFoundError
from app.models.trade_note import TradeNote
from app.schemas.note import TradeNoteCreate, TradeNoteRead, TradeNoteUpdate
from app.services.note_service import NoteService


def _make_note(
    id: uuid.UUID | None = None,
    trade_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    content: str = "Entered too early.",
    emotion: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> TradeNote:
    """Build a minimal :class:`TradeNote` ORM instance for testing.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        trade_id: UUID of the parent trade. Defaults to a new random UUID.
        user_id: UUID of the authoring user. Defaults to a new random UUID.
        content: Note body. Defaults to ``"Entered too early."``.
        emotion: Emotion label. Defaults to ``None``.
        created_at: Row-creation timestamp. Defaults to now (UTC).
        updated_at: Row-update timestamp. Defaults to now (UTC).

    Returns:
        A :class:`TradeNote` with sensible defaults.
    """
    now = datetime.now(tz=UTC)
    note = TradeNote()
    note.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    note.trade_id = trade_id if trade_id is not None else uuid.uuid4()  # type: ignore[assignment]
    note.user_id = user_id if user_id is not None else uuid.uuid4()  # type: ignore[assignment]
    note.content = content  # type: ignore[assignment]
    note.emotion = emotion  # type: ignore[assignment]
    note.created_at = created_at if created_at is not None else now  # type: ignore[assignment]
    note.updated_at = updated_at if updated_at is not None else now  # type: ignore[assignment]
    return note


@pytest.fixture()
def service(mock_session: AsyncMock) -> NoteService:
    """Return a :class:`NoteService` wired to a mock session."""
    return NoteService(mock_session)


class TestListNotes:
    """Unit tests for :meth:`NoteService.list_notes`."""

    @pytest.mark.unit
    async def test_returns_list_of_note_reads(self, service: NoteService) -> None:
        """list_notes should return a list of TradeNoteRead DTOs."""
        trade_id = uuid.uuid4()
        user_id = uuid.uuid4()
        notes = [_make_note(trade_id=trade_id, user_id=user_id) for _ in range(2)]
        with patch(
            "app.services.note_service.NoteRepository.list_by_trade",
            new_callable=AsyncMock,
            return_value=notes,
        ):
            result = await service.list_notes(trade_id, user_id)

        assert len(result) == 2
        assert all(isinstance(n, TradeNoteRead) for n in result)

    @pytest.mark.unit
    async def test_returns_empty_list_when_none(self, service: NoteService) -> None:
        """list_notes should return an empty list when there are no notes."""
        with patch(
            "app.services.note_service.NoteRepository.list_by_trade",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.list_notes(uuid.uuid4(), uuid.uuid4())

        assert result == []


class TestAddNote:
    """Unit tests for :meth:`NoteService.add_note`."""

    @pytest.mark.unit
    async def test_returns_note_read(self, service: NoteService) -> None:
        """add_note should return a TradeNoteRead DTO."""
        note = _make_note(content="Patience paid off.", emotion="calm")
        with patch(
            "app.services.note_service.NoteRepository.create",
            new_callable=AsyncMock,
            return_value=note,
        ):
            result = await service.add_note(
                uuid.uuid4(),
                TradeNoteCreate(content="Patience paid off.", emotion="calm"),
                uuid.uuid4(),
            )

        assert isinstance(result, TradeNoteRead)
        assert result.content == "Patience paid off."
        assert result.emotion == "calm"

    @pytest.mark.unit
    async def test_add_note_marks_trade_manually_edited(
        self,
        service: NoteService,
    ) -> None:
        trade_id = uuid.uuid4()
        user_id = uuid.uuid4()
        note = _make_note(trade_id=trade_id, user_id=user_id)

        with (
            patch(
                "app.services.note_service.NoteRepository.create",
                new_callable=AsyncMock,
                return_value=note,
            ),
            patch(
                "app.services.note_service.TradeRepository.mark_manually_edited",
                new_callable=AsyncMock,
                return_value=None,
            ) as mark_manually_edited,
        ):
            await service.add_note(
                trade_id,
                TradeNoteCreate(content="Note", emotion=None),
                user_id,
            )

        mark_manually_edited.assert_awaited_once_with(trade_id, user_id)


class TestUpdateNote:
    """Unit tests for :meth:`NoteService.update_note`."""

    @pytest.mark.unit
    async def test_returns_updated_note_read(self, service: NoteService) -> None:
        """update_note should return the updated TradeNoteRead DTO."""
        note = _make_note()
        updated_note = _make_note(
            id=note.id,
            content="Revised: actually a valid setup.",  # type: ignore[arg-type]
        )
        with (
            patch(
                "app.services.note_service.NoteRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=note,
            ),
            patch(
                "app.services.note_service.NoteRepository.update",
                new_callable=AsyncMock,
                return_value=updated_note,
            ),
        ):
            result = await service.update_note(
                note.id,  # type: ignore[arg-type]
                note.trade_id,  # type: ignore[arg-type]
                TradeNoteUpdate(content="Revised: actually a valid setup."),
                note.user_id,  # type: ignore[arg-type]
            )

        assert result.content == "Revised: actually a valid setup."

    @pytest.mark.unit
    async def test_update_note_marks_trade_manually_edited(
        self,
        service: NoteService,
    ) -> None:
        note = _make_note()
        updated_note = _make_note(id=note.id, trade_id=note.trade_id, user_id=note.user_id)
        with (
            patch(
                "app.services.note_service.NoteRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=note,
            ),
            patch(
                "app.services.note_service.NoteRepository.update",
                new_callable=AsyncMock,
                return_value=updated_note,
            ),
            patch(
                "app.services.note_service.TradeRepository.mark_manually_edited",
                new_callable=AsyncMock,
                return_value=None,
            ) as mark_manually_edited,
        ):
            await service.update_note(
                note.id,
                note.trade_id,
                TradeNoteUpdate(content="updated"),
                note.user_id,
            )

        mark_manually_edited.assert_awaited_once_with(note.trade_id, note.user_id)

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: NoteService) -> None:
        """update_note should raise NoteNotFoundError when the note is missing."""
        with (
            patch(
                "app.services.note_service.NoteRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(NoteNotFoundError),
        ):
            await service.update_note(
                uuid.uuid4(),
                uuid.uuid4(),
                TradeNoteUpdate(content="irrelevant"),
                uuid.uuid4(),
            )


class TestDeleteNote:
    """Unit tests for :meth:`NoteService.delete_note`."""

    @pytest.mark.unit
    async def test_delete_calls_repo(self, service: NoteService) -> None:
        """delete_note should call the repository delete method."""
        note = _make_note()
        mock_delete = AsyncMock()
        with (
            patch(
                "app.services.note_service.NoteRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=note,
            ),
            patch(
                "app.services.note_service.NoteRepository.delete",
                new=mock_delete,
            ),
        ):
            await service.delete_note(
                note.id,
                note.trade_id,
                note.user_id,  # type: ignore[arg-type]
            )

        mock_delete.assert_awaited_once_with(note)

    @pytest.mark.unit
    async def test_delete_note_marks_trade_manually_edited(
        self,
        service: NoteService,
    ) -> None:
        note = _make_note()
        with (
            patch(
                "app.services.note_service.NoteRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=note,
            ),
            patch(
                "app.services.note_service.NoteRepository.delete",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.note_service.TradeRepository.mark_manually_edited",
                new_callable=AsyncMock,
                return_value=None,
            ) as mark_manually_edited,
        ):
            await service.delete_note(note.id, note.trade_id, note.user_id)

        mark_manually_edited.assert_awaited_once_with(note.trade_id, note.user_id)

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: NoteService) -> None:
        """delete_note should raise NoteNotFoundError when the note is missing."""
        with (
            patch(
                "app.services.note_service.NoteRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(NoteNotFoundError),
        ):
            await service.delete_note(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
