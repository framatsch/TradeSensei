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

"""Unit tests for SavedTradeFilterService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import (
    SavedTradeFilterNotFoundError,
    SavedTradeFilterPermissionError,
    SavedTradeFilterValidationError,
)
from app.models.saved_trade_filter import FilterScope
from app.services.saved_trade_filter_service import SavedTradeFilterService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_FILTER_ID = uuid.uuid4()


def _make_mock_filter(
    scope: FilterScope = FilterScope.USER,
    owner_id: uuid.UUID | None = None,
    filter_id: uuid.UUID | None = None,
) -> MagicMock:
    f = MagicMock()
    f.scope = scope
    f.owner_id = owner_id or _USER_ID
    f.id = filter_id or _FILTER_ID
    return f


def _make_service(repo=None) -> SavedTradeFilterService:
    repo = repo or AsyncMock()
    return SavedTradeFilterService(repository=repo)


# ---------------------------------------------------------------------------
# list_for_user
# ---------------------------------------------------------------------------


async def test_list_for_user_delegates_to_repo():
    mock_repo = AsyncMock()
    filters = [_make_mock_filter(), _make_mock_filter()]
    mock_repo.list_for_user = AsyncMock(return_value=filters)

    svc = _make_service(mock_repo)
    result = await svc.list_for_user(_USER_ID)

    assert result is filters
    mock_repo.list_for_user.assert_called_once_with(_USER_ID)


# ---------------------------------------------------------------------------
# _validate_definition
# ---------------------------------------------------------------------------


async def test_validate_definition_accepts_empty_dict():
    svc = _make_service()
    # should not raise
    svc._validate_definition({})


async def test_validate_definition_raises_on_invalid_field():
    svc = _make_service()
    with pytest.raises(SavedTradeFilterValidationError):
        svc._validate_definition({"opened_at_from": "not-a-date"})


# ---------------------------------------------------------------------------
# create_user_filter
# ---------------------------------------------------------------------------


async def test_create_user_filter_success():
    mock_repo = AsyncMock()
    created = _make_mock_filter()
    mock_repo.create = AsyncMock(return_value=created)

    svc = _make_service(mock_repo)
    result = await svc.create_user_filter(_USER_ID, "My Filter", {})

    assert result is created
    mock_repo.create.assert_called_once()


async def test_create_user_filter_raises_on_invalid_definition():
    svc = _make_service()
    with pytest.raises(SavedTradeFilterValidationError):
        await svc.create_user_filter(_USER_ID, "Bad Filter", {"opened_at_from": "not-a-date"})


# ---------------------------------------------------------------------------
# update_user_filter
# ---------------------------------------------------------------------------


async def test_update_user_filter_success():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    updated = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock(return_value=updated)

    svc = _make_service(mock_repo)
    result = await svc.update_user_filter(_USER_ID, _FILTER_ID, name="New Name")

    assert result is updated


async def test_update_user_filter_raises_not_found():
    mock_repo = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedTradeFilterNotFoundError):
        await svc.update_user_filter(_USER_ID, _FILTER_ID, name="X")


async def test_update_user_filter_raises_permission_for_system_filter():
    mock_repo = AsyncMock()
    existing = _make_mock_filter(scope=FilterScope.SYSTEM)
    mock_repo.get_by_id = AsyncMock(return_value=existing)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedTradeFilterPermissionError):
        await svc.update_user_filter(_USER_ID, _FILTER_ID, name="X")


async def test_update_user_filter_raises_permission_for_wrong_owner():
    mock_repo = AsyncMock()
    other_user = uuid.uuid4()
    existing = _make_mock_filter(owner_id=other_user)
    mock_repo.get_by_id = AsyncMock(return_value=existing)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedTradeFilterPermissionError):
        await svc.update_user_filter(_USER_ID, _FILTER_ID, name="X")


async def test_update_user_filter_validates_definition_when_provided():
    svc = _make_service()
    # Inject a non-None repo that returns an existing filter
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    svc = _make_service(mock_repo)

    with pytest.raises(SavedTradeFilterValidationError):
        await svc.update_user_filter(_USER_ID, _FILTER_ID, definition={"opened_at_from": "not-a-date"})


async def test_update_user_filter_clears_needs_review_when_definition_provided():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    updated = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock(return_value=updated)

    svc = _make_service(mock_repo)
    await svc.update_user_filter(_USER_ID, _FILTER_ID, definition={})

    call_kwargs = mock_repo.update.call_args[1]
    assert call_kwargs["needs_review"] is False


async def test_update_user_filter_needs_review_none_when_no_definition():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    updated = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.update = AsyncMock(return_value=updated)

    svc = _make_service(mock_repo)
    await svc.update_user_filter(_USER_ID, _FILTER_ID, name="New Name")

    call_kwargs = mock_repo.update.call_args[1]
    assert call_kwargs["needs_review"] is None


# ---------------------------------------------------------------------------
# delete_user_filter
# ---------------------------------------------------------------------------


async def test_delete_user_filter_success():
    mock_repo = AsyncMock()
    existing = _make_mock_filter()
    mock_repo.get_by_id = AsyncMock(return_value=existing)
    mock_repo.delete = AsyncMock()

    svc = _make_service(mock_repo)
    await svc.delete_user_filter(_USER_ID, _FILTER_ID)

    mock_repo.delete.assert_called_once_with(_FILTER_ID)


async def test_delete_user_filter_raises_not_found():
    mock_repo = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedTradeFilterNotFoundError):
        await svc.delete_user_filter(_USER_ID, _FILTER_ID)


async def test_delete_user_filter_raises_permission_for_system_filter():
    mock_repo = AsyncMock()
    existing = _make_mock_filter(scope=FilterScope.SYSTEM)
    mock_repo.get_by_id = AsyncMock(return_value=existing)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedTradeFilterPermissionError):
        await svc.delete_user_filter(_USER_ID, _FILTER_ID)


async def test_delete_user_filter_raises_permission_for_wrong_owner():
    mock_repo = AsyncMock()
    other_user = uuid.uuid4()
    existing = _make_mock_filter(owner_id=other_user)
    mock_repo.get_by_id = AsyncMock(return_value=existing)

    svc = _make_service(mock_repo)
    with pytest.raises(SavedTradeFilterPermissionError):
        await svc.delete_user_filter(_USER_ID, _FILTER_ID)
