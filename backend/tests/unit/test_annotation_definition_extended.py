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

"""Unit tests for AnnotationDefinitionService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    AnnotationDefinitionNotFoundError,
    AnnotationDefinitionValidationError,
)
from app.schemas.annotation_definition import AnnotationDefinitionCreate, AnnotationDefinitionUpdate
from app.services.annotation_definition_service import AnnotationDefinitionService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_DEF_ID = uuid.uuid4()


def _make_service():
    svc = AnnotationDefinitionService.__new__(AnnotationDefinitionService)
    svc._session = AsyncMock()
    svc._repo = AsyncMock()
    svc._cache = AsyncMock()
    return svc


def _make_mock_def(scope: str = "trades", type_: str = "int", is_archived: bool = False):
    d = MagicMock()
    d.id = _DEF_ID
    d.name = "My Annotation"
    d.type = type_
    d.scope = scope
    d.is_archived = is_archived
    d.description = None
    d.scale_labels = None
    d.icon_identifier = None
    d.usage_count = 0
    d.created_at = MagicMock()
    d.updated_at = MagicMock()
    return d


def _make_create_payload():
    return AnnotationDefinitionCreate(name="Test", type="int", scope="trades")


def _make_update_payload(**kwargs):
    return AnnotationDefinitionUpdate(**kwargs)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_success():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.create = AsyncMock(return_value=mock_def)

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        result = await svc.create(_make_create_payload(), user_id=_USER_ID)

    svc._repo.create.assert_called_once()
    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_create_without_user_id_does_not_invalidate_cache():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.create = AsyncMock(return_value=mock_def)

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        await svc.create(_make_create_payload(), user_id=None)

    svc._cache.invalidate_user.assert_not_called()


async def test_create_raises_on_integrity_error():
    svc = _make_service()
    svc._repo.create = AsyncMock(side_effect=IntegrityError("dup", None, None))

    with pytest.raises(AnnotationDefinitionValidationError):
        await svc.create(_make_create_payload(), user_id=_USER_ID)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


async def test_list_with_invalid_scope_raises():
    svc = _make_service()

    with pytest.raises(AnnotationDefinitionValidationError):
        await svc.list(_USER_ID, scope="invalid_scope_xyz")


async def test_list_show_archived():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.list_including_archived = AsyncMock(return_value=[mock_def])

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        result = await svc.list(_USER_ID, show_archived=True)

    svc._repo.list_including_archived.assert_called_once()
    assert len(result) == 1


async def test_list_default_uses_usage_counts():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.list_with_usage_counts = AsyncMock(return_value=[(mock_def, 5)])

    mock_response = MagicMock()
    mock_response.model_copy = MagicMock(return_value=MagicMock())
    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=mock_response):
        await svc.list(_USER_ID)

    svc._repo.list_with_usage_counts.assert_called_once()


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


async def test_get_success():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        result = await svc.get(_USER_ID, _DEF_ID)

    svc._repo.get_by_id.assert_called_once_with(user_id=_USER_ID, definition_id=_DEF_ID)


async def test_get_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AnnotationDefinitionNotFoundError):
        await svc.get(_USER_ID, _DEF_ID)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AnnotationDefinitionNotFoundError):
        await svc.update(_DEF_ID, _make_update_payload(name="New"), user_id=_USER_ID)


async def test_update_raises_when_type_changes():
    svc = _make_service()
    mock_def = _make_mock_def(type_="int")
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)

    with pytest.raises(AnnotationDefinitionValidationError):
        await svc.update(_DEF_ID, _make_update_payload(type="float"), user_id=_USER_ID)


async def test_update_raises_when_scope_narrowing_with_assignments():
    svc = _make_service()
    mock_def = _make_mock_def(scope="trades,checkins")
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.count_assignments = AsyncMock(return_value=(5, 0))  # 5 trade assignments

    with pytest.raises(AnnotationDefinitionValidationError):
        await svc.update(_DEF_ID, _make_update_payload(scope="checkins"), user_id=_USER_ID)


async def test_update_success():
    svc = _make_service()
    mock_def = _make_mock_def()
    updated_def = _make_mock_def()
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.update = AsyncMock(return_value=updated_def)

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        await svc.update(_DEF_ID, _make_update_payload(name="New Name"), user_id=_USER_ID)

    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_update_raises_on_integrity_error():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.update = AsyncMock(side_effect=IntegrityError("dup", None, None))

    with pytest.raises(AnnotationDefinitionValidationError):
        await svc.update(_DEF_ID, _make_update_payload(name="New Name"), user_id=_USER_ID)


# ---------------------------------------------------------------------------
# get_assignment_counts
# ---------------------------------------------------------------------------


async def test_get_assignment_counts_success():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.count_assignments = AsyncMock(return_value=(3, 2))

    result = await svc.get_assignment_counts(_DEF_ID, _USER_ID)

    assert result["trade_count"] == 3
    assert result["checkin_count"] == 2
    assert result["total_count"] == 5


async def test_get_assignment_counts_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AnnotationDefinitionNotFoundError):
        await svc.get_assignment_counts(_DEF_ID, _USER_ID)


# ---------------------------------------------------------------------------
# archive / unarchive
# ---------------------------------------------------------------------------


async def test_archive_success():
    svc = _make_service()
    mock_def = _make_mock_def()
    archived = _make_mock_def(is_archived=True)
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.archive = AsyncMock(return_value=archived)

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        await svc.archive(_DEF_ID, _USER_ID)

    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_archive_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AnnotationDefinitionNotFoundError):
        await svc.archive(_DEF_ID, _USER_ID)


async def test_unarchive_success():
    svc = _make_service()
    mock_def = _make_mock_def(is_archived=True)
    unarchived = _make_mock_def(is_archived=False)
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.unarchive = AsyncMock(return_value=unarchived)

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        await svc.unarchive(_DEF_ID, _USER_ID)

    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_unarchive_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AnnotationDefinitionNotFoundError):
        await svc.unarchive(_DEF_ID, _USER_ID)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


async def test_delete_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AnnotationDefinitionNotFoundError):
        await svc.delete(_DEF_ID, user_id=_USER_ID)


async def test_delete_force_deletes_all():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.delete_assignments = AsyncMock()
    svc._repo.delete = AsyncMock()

    result = await svc.delete(_DEF_ID, user_id=_USER_ID, force=True)

    assert result is None
    svc._repo.delete_assignments.assert_called_once_with(_DEF_ID)
    svc._repo.delete.assert_called_once_with(mock_def)
    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_delete_archives_when_assignments_exist():
    svc = _make_service()
    mock_def = _make_mock_def()
    archived = _make_mock_def(is_archived=True)
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.count_assignments = AsyncMock(return_value=(2, 1))
    svc._repo.archive = AsyncMock(return_value=archived)

    with patch("app.services.annotation_definition_service.AnnotationDefinitionResponse.model_validate", return_value=MagicMock()):
        result = await svc.delete(_DEF_ID, user_id=_USER_ID)

    svc._repo.archive.assert_called_once_with(mock_def)


async def test_delete_hard_deletes_when_no_assignments():
    svc = _make_service()
    mock_def = _make_mock_def()
    svc._repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._repo.count_assignments = AsyncMock(return_value=(0, 0))
    svc._repo.delete = AsyncMock()

    result = await svc.delete(_DEF_ID, user_id=_USER_ID)

    assert result is None
    svc._repo.delete.assert_called_once_with(mock_def)
