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

"""Unit tests for PlaybookAttachmentService."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    ConfigurationError,
    PlaybookAttachmentNotFoundError,
    PlaybookNotFoundError,
    UnsupportedContentTypeError,
)
from app.schemas.playbook_attachment import (
    PlaybookImageRegisterRequest,
    PlaybookImageResponse,
    PlaybookImageUploadUrlResponse,
)
from app.services.playbook_attachment_service import PlaybookAttachmentService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_PLAYBOOK_ID = uuid.uuid4()
_ATTACHMENT_ID = uuid.uuid4()


def _make_service():
    svc = PlaybookAttachmentService.__new__(PlaybookAttachmentService)
    svc._session = AsyncMock()
    svc._playbook_repo = AsyncMock()
    svc._attachment_repo = AsyncMock()
    svc._storage = MagicMock()
    return svc


def _make_mock_playbook():
    p = MagicMock()
    p.id = _PLAYBOOK_ID
    return p


def _make_mock_attachment():
    a = MagicMock()
    a.id = _ATTACHMENT_ID
    a.playbook_id = _PLAYBOOK_ID
    a.filename = "test.png"
    a.storage_url = "my-bucket/test.png"
    a.content_type = "image/png"
    a.created_at = datetime(2024, 1, 1)
    return a


# ---------------------------------------------------------------------------
# generate_upload_url
# ---------------------------------------------------------------------------


async def test_generate_upload_url_raises_when_playbook_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlaybookNotFoundError):
        await svc.generate_upload_url(_PLAYBOOK_ID, _USER_ID, "test.png", "image/png")


async def test_generate_upload_url_raises_for_unsupported_content_type(monkeypatch):
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    monkeypatch.setattr("app.services.playbook_attachment_service.settings.storage_backend", "s3")

    with pytest.raises(UnsupportedContentTypeError):
        await svc.generate_upload_url(_PLAYBOOK_ID, _USER_ID, "file.pdf", "application/pdf")


async def test_generate_upload_url_raises_when_storage_not_configured(monkeypatch):
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    monkeypatch.setattr("app.services.playbook_attachment_service.settings.storage_backend", None)

    with pytest.raises(ConfigurationError):
        await svc.generate_upload_url(_PLAYBOOK_ID, _USER_ID, "test.png", "image/png")


async def test_generate_upload_url_success(monkeypatch):
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    monkeypatch.setattr("app.services.playbook_attachment_service.settings.storage_backend", "s3")
    svc._storage.generate_playbook_upload_url = MagicMock(
        return_value=("https://upload.example.com", "my-bucket/key.png")
    )

    result = await svc.generate_upload_url(_PLAYBOOK_ID, _USER_ID, "test.png", "image/png")

    assert isinstance(result, PlaybookImageUploadUrlResponse)
    assert result.upload_url == "https://upload.example.com"
    assert result.key == "my-bucket/key.png"


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------


async def test_register_raises_when_playbook_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    payload = PlaybookImageRegisterRequest(
        filename="test.png",
        storage_url="bucket/key.png",
        content_type="image/png",
    )
    with pytest.raises(PlaybookNotFoundError):
        await svc.register(_PLAYBOOK_ID, _USER_ID, payload)


async def test_register_raises_for_bad_storage_url_format(monkeypatch):
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._storage.parse_storage_ref = MagicMock(side_effect=ValueError("bad format"))

    payload = PlaybookImageRegisterRequest(
        filename="test.png",
        storage_url="invalid",
        content_type="image/png",
    )
    with pytest.raises(UnsupportedContentTypeError):
        await svc.register(_PLAYBOOK_ID, _USER_ID, payload)


async def test_register_raises_for_wrong_bucket(monkeypatch):
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._storage.parse_storage_ref = MagicMock(return_value=("wrong-bucket", "key.png"))
    monkeypatch.setattr("app.services.playbook_attachment_service.settings.storage_bucket", "correct-bucket")

    payload = PlaybookImageRegisterRequest(
        filename="test.png",
        storage_url="wrong-bucket/key.png",
        content_type="image/png",
    )
    with pytest.raises(UnsupportedContentTypeError):
        await svc.register(_PLAYBOOK_ID, _USER_ID, payload)


async def test_register_raises_for_unsupported_content_type(monkeypatch):
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._storage.parse_storage_ref = MagicMock(return_value=("my-bucket", "key.pdf"))
    monkeypatch.setattr("app.services.playbook_attachment_service.settings.storage_bucket", "my-bucket")

    payload = PlaybookImageRegisterRequest(
        filename="test.pdf",
        storage_url="my-bucket/key.pdf",
        content_type="application/pdf",
    )
    with pytest.raises(UnsupportedContentTypeError):
        await svc.register(_PLAYBOOK_ID, _USER_ID, payload)


async def test_register_success(monkeypatch):
    svc = _make_service()
    mock_attachment = _make_mock_attachment()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._storage.parse_storage_ref = MagicMock(return_value=("my-bucket", "key.png"))
    svc._attachment_repo.create = AsyncMock(return_value=mock_attachment)
    monkeypatch.setattr("app.services.playbook_attachment_service.settings.storage_bucket", "my-bucket")

    payload = PlaybookImageRegisterRequest(
        filename="test.png",
        storage_url="my-bucket/key.png",
        content_type="image/png",
    )
    with patch.object(PlaybookImageResponse, "model_validate", return_value=MagicMock()):
        result = await svc.register(_PLAYBOOK_ID, _USER_ID, payload)

    svc._attachment_repo.create.assert_called_once()


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


async def test_list_attachments_raises_when_playbook_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlaybookNotFoundError):
        await svc.list(_PLAYBOOK_ID, _USER_ID)


async def test_list_attachments_success():
    svc = _make_service()
    attachments = [_make_mock_attachment(), _make_mock_attachment()]
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._attachment_repo.list_for_playbook = AsyncMock(return_value=attachments)

    with patch.object(PlaybookImageResponse, "model_validate", return_value=MagicMock()):
        result = await svc.list(_PLAYBOOK_ID, _USER_ID)

    assert len(result) == 2


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


async def test_delete_attachment_raises_when_playbook_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlaybookNotFoundError):
        await svc.delete(_PLAYBOOK_ID, _ATTACHMENT_ID, _USER_ID)


async def test_delete_attachment_raises_when_attachment_not_found():
    svc = _make_service()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._attachment_repo.get = AsyncMock(return_value=None)

    with pytest.raises(PlaybookAttachmentNotFoundError):
        await svc.delete(_PLAYBOOK_ID, _ATTACHMENT_ID, _USER_ID)


async def test_delete_attachment_success():
    svc = _make_service()
    mock_attachment = _make_mock_attachment()
    svc._playbook_repo.get_by_id = AsyncMock(return_value=_make_mock_playbook())
    svc._attachment_repo.get = AsyncMock(return_value=mock_attachment)
    svc._attachment_repo.delete = AsyncMock()

    await svc.delete(_PLAYBOOK_ID, _ATTACHMENT_ID, _USER_ID)

    svc._attachment_repo.delete.assert_called_once_with(mock_attachment)
