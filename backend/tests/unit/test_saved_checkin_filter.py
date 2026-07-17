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

"""Unit tests for SavedCheckinFilterService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import SavedCheckinFilterConflictError, SavedCheckinFilterNotFoundError
from app.schemas.saved_checkin_filter import CheckinFilterConfig, SavedCheckinFilterCreate, SavedCheckinFilterUpdate
from app.services.saved_checkin_filter_service import SavedCheckinFilterService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_FILTER_ID = uuid.uuid4()


def _make_mock_filter(user_id: uuid.UUID = _USER_ID, filter_id: uuid.UUID = _FILTER_ID) -> MagicMock:
    f = MagicMock()
    f.user_id = user_id
    f.id = filter_id
    return f


def _make_service(repo=None) -> SavedCheckinFilterService:
    repo = repo or AsyncMock()
    return SavedCheckinFilterService(repo=repo)


def _make_create_schema(is_default: bool = False) -> SavedCheckinFilterCreate:
    return SavedCheckinFilterCreate(
        name="My Filter",
        is_default=is_default,
        filter_config=CheckinFilterConfig(),
    )


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_success():
    mock_repo = AsyncMock()
    mock_filter = _make_mock_filter()
    mock_repo.create = AsyncMock(return_value=mock_filter)
    mock_repo.unset_default = AsyncMock()

    svc = _make_service(mock_repo)
    schema = _make_create_schema()
    result = await svc.create(_USER_ID, schema)

    assert result is mock_filter
    mock_repo.create.assert_called_once()
    mock_repo.unset_default.assert_not_called()


async def test_create_with_is_default_calls_unset_default():
    mock_repo = AsyncMock()
    mock_repo.create = AsyncMock(return_value=_make_mock_filter())
    mock_repo.unset_default = AsyncMock()

    svc = _make_service(mock_repo)
    schema = _make_create_schema(is_default=True)
    await svc.create(_USER_ID, schema)

    mock_repo.unset_default.assert_called_once_with(user_id=_USER_ID)


async def test_create_raises_conflict_on_integrity_error():
    mock_repo = AsyncMock()
    mock_repo.unset_default = AsyncMock()
    mock_repo.create = AsyncMock(side_effect=IntegrityError("dup", None, None))

    svc = _make_service(mock_repo)
    schema = _make_create_schema()
    with pytest.raises(SavedCheckinFilterConflictError):
        await svc.create(_USER_ID, schema)


# ---------------------------------------------------------------------------
# list_by_user
# ---------------------------------------------------------------------------


async def test_list_by_user_returns_list():
    mock_repo = AsyncMock()
    mock_repo.list_by_user = AsyncMock(return_value=[_make_mock_filter(), _make_mock_filter()])

    svc = _make_service(mock_repo)
    result = await svc.list_by_user(_USER_ID)

    assert isinstance(result, list)
    assert len(result) == 2


async def test_list_by_user_empty():
    mock_repo = AsyncMock()
    mock_repo.list_by_user = AsyncMock(return_value=[])

    svc = _make_service(mock_repo)
    result = await svc.list_by_user(_USER_ID)

    assert result == []


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_returns_updated_filter():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    updated = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock(return_value=updated)
    mock_repo.unset_default = AsyncMock()

    svc = _make_service(mock_repo)
    schema = SavedCheckinFilterUpdate(name="New Name")
    result = await svc.update(_USER_ID, _FILTER_ID, schema)

    assert result is updated


async def test_update_raises_not_found_when_missing():
    mock_repo = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)

    svc = _make_service(mock_repo)
    schema = SavedCheckinFilterUpdate(name="X")
    with pytest.raises(SavedCheckinFilterNotFoundError):
        await svc.update(_USER_ID, _FILTER_ID, schema)


async def test_update_raises_not_found_when_different_user():
    mock_repo = AsyncMock()
    other_user = uuid.uuid4()
    existing = _make_mock_filter(user_id=other_user)
    mock_repo.get_by_id = AsyncMock(return_value=existing)

    svc = _make_service(mock_repo)
    schema = SavedCheckinFilterUpdate(name="X")
    with pytest.raises(SavedCheckinFilterNotFoundError):
        await svc.update(_USER_ID, _FILTER_ID, schema)


async def test_update_returns_existing_when_no_update_data():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock()

    svc = _make_service(mock_repo)
    schema = SavedCheckinFilterUpdate()  # all fields None
    result = await svc.update(_USER_ID, _FILTER_ID, schema)

    assert result is existing
    mock_repo.update.assert_not_called()


async def test_update_calls_unset_default_when_is_default_true():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    updated = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock(return_value=updated)
    mock_repo.unset_default = AsyncMock()

    svc = _make_service(mock_repo)
    schema = SavedCheckinFilterUpdate(is_default=True)
    await svc.update(_USER_ID, _FILTER_ID, schema)

    mock_repo.unset_default.assert_called_once_with(user_id=_USER_ID, exclude_id=_FILTER_ID)


async def test_update_raises_not_found_when_repo_returns_none():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock(return_value=None)
    mock_repo.unset_default = AsyncMock()

    svc = _make_service(mock_repo)
    schema = SavedCheckinFilterUpdate(name="X")
    with pytest.raises(SavedCheckinFilterNotFoundError):
        await svc.update(_USER_ID, _FILTER_ID, schema)


async def test_update_raises_conflict_on_integrity_error():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock(side_effect=IntegrityError("dup", None, None))
    mock_repo.unset_default = AsyncMock()

    svc = _make_service(mock_repo)
    schema = SavedCheckinFilterUpdate(name="X")
    with pytest.raises(SavedCheckinFilterConflictError):
        await svc.update(_USER_ID, _FILTER_ID, schema)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


async def test_delete_success():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.delete = AsyncMock(return_value=True)

    svc = _make_service(mock_repo)
    await svc.delete(_USER_ID, _FILTER_ID)

    mock_repo.delete.assert_called_once_with(_FILTER_ID)


async def test_delete_raises_not_found_when_missing():
    mock_repo = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedCheckinFilterNotFoundError):
        await svc.delete(_USER_ID, _FILTER_ID)


async def test_delete_raises_not_found_when_different_user():
    mock_repo = AsyncMock()
    other_user = uuid.uuid4()
    existing = _make_mock_filter(user_id=other_user)
    mock_repo.get_by_id = AsyncMock(return_value=existing)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedCheckinFilterNotFoundError):
        await svc.delete(_USER_ID, _FILTER_ID)


async def test_delete_raises_not_found_when_repo_delete_returns_false():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.delete = AsyncMock(return_value=False)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedCheckinFilterNotFoundError):
        await svc.delete(_USER_ID, _FILTER_ID)
