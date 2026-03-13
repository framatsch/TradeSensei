"""Unit tests for PlaybookService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import PlaybookNotFoundError
from app.models.playbook import Playbook
from app.schemas.playbook import PlaybookCreate, PlaybookRead, PlaybookUpdate
from app.services.playbook_service import PlaybookService


def _make_playbook(
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    name: str = "Breakout Long",
    description: str | None = None,
    is_active: bool = True,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Playbook:
    """Build a minimal :class:`Playbook` ORM instance for testing.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        user_id: UUID of the owning user. Defaults to a new random UUID.
        name: Playbook name. Defaults to ``"Breakout Long"``.
        description: Optional description. Defaults to ``None``.
        is_active: Active flag. Defaults to ``True``.
        created_at: Row-creation timestamp. Defaults to now (UTC).
        updated_at: Row-update timestamp. Defaults to now (UTC).

    Returns:
        A :class:`Playbook` with sensible defaults.
    """
    now = datetime.now(tz=UTC)
    pb = Playbook()
    pb.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    pb.user_id = user_id if user_id is not None else uuid.uuid4()  # type: ignore[assignment]
    pb.name = name  # type: ignore[assignment]
    pb.description = description  # type: ignore[assignment]
    pb.is_active = is_active  # type: ignore[assignment]
    pb.created_at = created_at if created_at is not None else now  # type: ignore[assignment]
    pb.updated_at = updated_at if updated_at is not None else now  # type: ignore[assignment]
    return pb


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return a mock :class:`AsyncSession`."""
    return AsyncMock()


@pytest.fixture()
def service(mock_session: AsyncMock) -> PlaybookService:
    """Return a :class:`PlaybookService` wired to a mock session."""
    return PlaybookService(mock_session)


class TestListPlaybooks:
    """Unit tests for :meth:`PlaybookService.list_playbooks`."""

    @pytest.mark.unit
    async def test_returns_list_of_playbook_reads(
        self, service: PlaybookService
    ) -> None:
        """list_playbooks should return a list of PlaybookRead DTOs."""
        playbooks = [_make_playbook(name=f"PB{i}") for i in range(3)]
        with patch(
            "app.services.playbook_service.PlaybookRepository.list_by_user",
            new_callable=AsyncMock,
            return_value=playbooks,
        ):
            result = await service.list_playbooks(uuid.uuid4())

        assert len(result) == 3
        assert all(isinstance(p, PlaybookRead) for p in result)

    @pytest.mark.unit
    async def test_returns_empty_list_when_none(self, service: PlaybookService) -> None:
        """list_playbooks should return an empty list when there are no playbooks."""
        with patch(
            "app.services.playbook_service.PlaybookRepository.list_by_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.list_playbooks(uuid.uuid4())

        assert result == []


class TestGetPlaybook:
    """Unit tests for :meth:`PlaybookService.get_playbook`."""

    @pytest.mark.unit
    async def test_returns_playbook_read_when_found(
        self, service: PlaybookService
    ) -> None:
        """get_playbook should return a PlaybookRead when the playbook exists."""
        pb = _make_playbook()
        with patch(
            "app.services.playbook_service.PlaybookRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=pb,
        ):
            result = await service.get_playbook(pb.id, pb.user_id)  # type: ignore[arg-type]

        assert isinstance(result, PlaybookRead)
        assert result.name == "Breakout Long"

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(
        self, service: PlaybookService
    ) -> None:
        """get_playbook should raise PlaybookNotFoundError when missing."""
        with (
            patch(
                "app.services.playbook_service.PlaybookRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(PlaybookNotFoundError),
        ):
            await service.get_playbook(uuid.uuid4(), uuid.uuid4())


class TestCreatePlaybook:
    """Unit tests for :meth:`PlaybookService.create_playbook`."""

    @pytest.mark.unit
    async def test_returns_playbook_read(self, service: PlaybookService) -> None:
        """create_playbook should return a PlaybookRead DTO."""
        pb = _make_playbook(name="VWAP Fade")
        with patch(
            "app.services.playbook_service.PlaybookRepository.create",
            new_callable=AsyncMock,
            return_value=pb,
        ):
            result = await service.create_playbook(
                PlaybookCreate(name="VWAP Fade"), uuid.uuid4()
            )

        assert isinstance(result, PlaybookRead)
        assert result.name == "VWAP Fade"


class TestUpdatePlaybook:
    """Unit tests for :meth:`PlaybookService.update_playbook`."""

    @pytest.mark.unit
    async def test_returns_updated_playbook_read(
        self, service: PlaybookService
    ) -> None:
        """update_playbook should return the updated PlaybookRead DTO."""
        pb = _make_playbook()
        updated_pb = _make_playbook(id=pb.id, name="Trend Follow")  # type: ignore[arg-type]
        with (
            patch(
                "app.services.playbook_service.PlaybookRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=pb,
            ),
            patch(
                "app.services.playbook_service.PlaybookRepository.update",
                new_callable=AsyncMock,
                return_value=updated_pb,
            ),
        ):
            result = await service.update_playbook(
                pb.id,  # type: ignore[arg-type]
                PlaybookUpdate(name="Trend Follow"),
                pb.user_id,  # type: ignore[arg-type]
            )

        assert result.name == "Trend Follow"

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(
        self, service: PlaybookService
    ) -> None:
        """update_playbook should raise PlaybookNotFoundError when missing."""
        with (
            patch(
                "app.services.playbook_service.PlaybookRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(PlaybookNotFoundError),
        ):
            await service.update_playbook(
                uuid.uuid4(), PlaybookUpdate(name="X"), uuid.uuid4()
            )


class TestDeletePlaybook:
    """Unit tests for :meth:`PlaybookService.delete_playbook`."""

    @pytest.mark.unit
    async def test_delete_calls_repo(self, service: PlaybookService) -> None:
        """delete_playbook should call the repository delete method."""
        pb = _make_playbook()
        mock_delete = AsyncMock()
        with (
            patch(
                "app.services.playbook_service.PlaybookRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=pb,
            ),
            patch(
                "app.services.playbook_service.PlaybookRepository.delete",
                new=mock_delete,
            ),
        ):
            await service.delete_playbook(pb.id, pb.user_id)  # type: ignore[arg-type]

        mock_delete.assert_awaited_once_with(pb)

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(
        self, service: PlaybookService
    ) -> None:
        """delete_playbook should raise PlaybookNotFoundError when missing."""
        with (
            patch(
                "app.services.playbook_service.PlaybookRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(PlaybookNotFoundError),
        ):
            await service.delete_playbook(uuid.uuid4(), uuid.uuid4())
