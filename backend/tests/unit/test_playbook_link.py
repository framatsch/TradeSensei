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

"""Unit tests for PlaybookLinkService."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import PlaybookLinkNotFoundError, PlaybookNotFoundError
from app.schemas.playbook_link import PlaybookLinkCreate, PlaybookLinkResponse
from app.services.playbook_link_service import PlaybookLinkService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_PLAYBOOK_ID = uuid.uuid4()
_LINK_ID = uuid.uuid4()


def _make_mock_playbook():
    p = MagicMock()
    p.id = _PLAYBOOK_ID
    return p


def _make_mock_link():
    lnk = MagicMock()
    lnk.id = _LINK_ID
    lnk.playbook_id = _PLAYBOOK_ID
    lnk.label = "My Link"
    lnk.url = "https://example.com"
    lnk.created_at = datetime(2024, 1, 1, 12, 0, 0)
    return lnk


def _make_service():
    svc = PlaybookLinkService.__new__(PlaybookLinkService)
    svc._playbook_repo = AsyncMock()
    svc._link_repo = AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# _ensure_playbook_exists
# ---------------------------------------------------------------------------


async def test_ensure_playbook_exists_raises_when_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlaybookNotFoundError):
        await svc._ensure_playbook_exists(_PLAYBOOK_ID, _USER_ID)


async def test_ensure_playbook_exists_passes_when_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    # Should not raise
    await svc._ensure_playbook_exists(_PLAYBOOK_ID, _USER_ID)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_link_success():
    svc = _make_service()
    mock_link = _make_mock_link()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._link_repo.create = AsyncMock(return_value=mock_link)

    payload = PlaybookLinkCreate(label="My Link", url="https://example.com")

    with patch.object(PlaybookLinkResponse, "model_validate", return_value=MagicMock()):
        result = await svc.create(_PLAYBOOK_ID, _USER_ID, payload)

    svc._link_repo.create.assert_called_once()


async def test_create_link_raises_when_playbook_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    payload = PlaybookLinkCreate(label="My Link", url="https://example.com")
    with pytest.raises(PlaybookNotFoundError):
        await svc.create(_PLAYBOOK_ID, _USER_ID, payload)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


async def test_list_links_success():
    svc = _make_service()
    mock_links = [_make_mock_link(), _make_mock_link()]
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._link_repo.list_for_playbook = AsyncMock(return_value=mock_links)

    with patch.object(PlaybookLinkResponse, "model_validate", return_value=MagicMock()):
        result = await svc.list(_PLAYBOOK_ID, _USER_ID)

    assert len(result) == 2


async def test_list_links_raises_when_playbook_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlaybookNotFoundError):
        await svc.list(_PLAYBOOK_ID, _USER_ID)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


async def test_delete_link_success():
    svc = _make_service()
    mock_link = _make_mock_link()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._link_repo.get = AsyncMock(return_value=mock_link)
    svc._link_repo.delete = AsyncMock()

    await svc.delete(_PLAYBOOK_ID, _LINK_ID, _USER_ID)

    svc._link_repo.delete.assert_called_once_with(mock_link)


async def test_delete_link_raises_when_playbook_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlaybookNotFoundError):
        await svc.delete(_PLAYBOOK_ID, _LINK_ID, _USER_ID)


async def test_delete_link_raises_when_link_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._link_repo.get = AsyncMock(return_value=None)

    with pytest.raises(PlaybookLinkNotFoundError):
        await svc.delete(_PLAYBOOK_ID, _LINK_ID, _USER_ID)
