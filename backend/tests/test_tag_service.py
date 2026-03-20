"""Unit tests for TagService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import TagNotFoundError
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services.tag_service import TagService


def _make_tag(
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    name: str = "gap-and-go",
    color: str | None = None,
    created_at: datetime | None = None,
) -> Tag:
    """Build a minimal :class:`Tag` ORM instance for testing.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        user_id: UUID of the owning user. Defaults to a new random UUID.
        name: Tag label. Defaults to ``"gap-and-go"``.
        color: Optional hex colour. Defaults to ``None``.
        created_at: Row-creation timestamp. Defaults to now (UTC).

    Returns:
        A :class:`Tag` with sensible defaults.
    """
    now = datetime.now(tz=UTC)
    tag = Tag()
    tag.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    tag.user_id = user_id if user_id is not None else uuid.uuid4()  # type: ignore[assignment]
    tag.name = name  # type: ignore[assignment]
    tag.color = color  # type: ignore[assignment]
    tag.created_at = created_at if created_at is not None else now  # type: ignore[assignment]
    return tag


@pytest.fixture()
def service(mock_session: AsyncMock) -> TagService:
    """Return a :class:`TagService` wired to a mock session."""
    return TagService(mock_session)


class TestListTags:
    """Unit tests for :meth:`TagService.list_tags`."""

    @pytest.mark.unit
    async def test_returns_list_of_tag_reads(self, service: TagService) -> None:
        """list_tags should return a list of TagRead DTOs."""
        tags = [_make_tag(name=f"tag-{i}") for i in range(3)]
        with patch(
            "app.services.tag_service.TagRepository.list_by_user",
            new_callable=AsyncMock,
            return_value=tags,
        ):
            result = await service.list_tags(uuid.uuid4())

        assert len(result) == 3
        assert all(isinstance(t, TagRead) for t in result)

    @pytest.mark.unit
    async def test_returns_empty_list_when_none(self, service: TagService) -> None:
        """list_tags should return an empty list when there are no tags."""
        with patch(
            "app.services.tag_service.TagRepository.list_by_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.list_tags(uuid.uuid4())

        assert result == []


class TestGetTag:
    """Unit tests for :meth:`TagService.get_tag`."""

    @pytest.mark.unit
    async def test_returns_tag_read_when_found(self, service: TagService) -> None:
        """get_tag should return a TagRead when the tag exists."""
        tag = _make_tag()
        with patch(
            "app.services.tag_service.TagRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=tag,
        ):
            result = await service.get_tag(tag.id, tag.user_id)  # type: ignore[arg-type]

        assert isinstance(result, TagRead)
        assert result.name == "gap-and-go"

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: TagService) -> None:
        """get_tag should raise TagNotFoundError when the tag is missing."""
        with (
            patch(
                "app.services.tag_service.TagRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(TagNotFoundError),
        ):
            await service.get_tag(uuid.uuid4(), uuid.uuid4())


class TestCreateTag:
    """Unit tests for :meth:`TagService.create_tag`."""

    @pytest.mark.unit
    async def test_returns_tag_read(self, service: TagService) -> None:
        """create_tag should return a TagRead DTO."""
        tag = _make_tag(name="breakout", color="#3b82f6")
        with patch(
            "app.services.tag_service.TagRepository.create",
            new_callable=AsyncMock,
            return_value=tag,
        ):
            result = await service.create_tag(
                TagCreate(name="breakout", color="#3b82f6"), uuid.uuid4()
            )

        assert isinstance(result, TagRead)
        assert result.name == "breakout"
        assert result.color == "#3b82f6"


class TestUpdateTag:
    """Unit tests for :meth:`TagService.update_tag`."""

    @pytest.mark.unit
    async def test_returns_updated_tag_read(self, service: TagService) -> None:
        """update_tag should return the updated TagRead DTO."""
        tag = _make_tag()
        updated_tag = _make_tag(id=tag.id, name="revenge-trade")  # type: ignore[arg-type]
        with (
            patch(
                "app.services.tag_service.TagRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=tag,
            ),
            patch(
                "app.services.tag_service.TagRepository.update",
                new_callable=AsyncMock,
                return_value=updated_tag,
            ),
        ):
            result = await service.update_tag(
                tag.id,  # type: ignore[arg-type]
                TagUpdate(name="revenge-trade"),
                tag.user_id,  # type: ignore[arg-type]
            )

        assert result.name == "revenge-trade"

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: TagService) -> None:
        """update_tag should raise TagNotFoundError when tag is missing."""
        with (
            patch(
                "app.services.tag_service.TagRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(TagNotFoundError),
        ):
            await service.update_tag(uuid.uuid4(), TagUpdate(name="X"), uuid.uuid4())


class TestDeleteTag:
    """Unit tests for :meth:`TagService.delete_tag`."""

    @pytest.mark.unit
    async def test_delete_calls_repo(self, service: TagService) -> None:
        """delete_tag should call the repository delete method."""
        tag = _make_tag()
        mock_delete = AsyncMock()
        with (
            patch(
                "app.services.tag_service.TagRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=tag,
            ),
            patch(
                "app.services.tag_service.TagRepository.delete",
                new=mock_delete,
            ),
        ):
            await service.delete_tag(tag.id, tag.user_id)  # type: ignore[arg-type]

        mock_delete.assert_awaited_once_with(tag)

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: TagService) -> None:
        """delete_tag should raise TagNotFoundError when tag is missing."""
        with (
            patch(
                "app.services.tag_service.TagRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(TagNotFoundError),
        ):
            await service.delete_tag(uuid.uuid4(), uuid.uuid4())
