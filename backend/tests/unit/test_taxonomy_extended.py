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

"""Unit tests for TaxonomyService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import TaxonomyNotFoundError, TaxonomyValidationError
from app.schemas.taxonomy import TaxonomyCreate, TaxonomyUpdate
from app.services.taxonomy_service import TaxonomyService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_TAX_ID = uuid.uuid4()


def _make_service():
    svc = TaxonomyService.__new__(TaxonomyService)
    svc._session = AsyncMock()
    svc._repo = AsyncMock()
    svc._cache = AsyncMock()
    return svc


def _make_mock_taxonomy(scope: str = "trades", is_archived: bool = False):
    t = MagicMock()
    t.id = _TAX_ID
    t.name = "My Taxonomy"
    t.scope = scope
    t.is_archived = is_archived
    t.color_hex = "#FFFFFF"
    t.created_at = MagicMock()
    t.updated_at = MagicMock()
    return t


def _make_create_payload():
    return TaxonomyCreate(name="Test Taxonomy", scope="trades", color_hex="#FFFFFF")


def _make_update_payload(**kwargs):
    return TaxonomyUpdate(**kwargs)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


async def test_create_success():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.create = AsyncMock(return_value=mock_tax)

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        await svc.create(_make_create_payload(), user_id=_USER_ID)

    svc._repo.create.assert_called_once()
    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_create_without_user_id_does_not_invalidate_cache():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.create = AsyncMock(return_value=mock_tax)

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        await svc.create(_make_create_payload(), user_id=None)

    svc._cache.invalidate_user.assert_not_called()


async def test_create_raises_on_integrity_error():
    svc = _make_service()
    svc._repo.create = AsyncMock(side_effect=IntegrityError("dup", None, None))

    with pytest.raises(TaxonomyValidationError):
        await svc.create(_make_create_payload(), user_id=_USER_ID)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


async def test_list_raises_for_invalid_scope():
    svc = _make_service()

    with pytest.raises(TaxonomyValidationError):
        await svc.list(_USER_ID, scope="invalid_scope_xyz")


async def test_list_show_archived():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.list_including_archived = AsyncMock(return_value=[mock_tax])

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        result = await svc.list(_USER_ID, show_archived=True)

    svc._repo.list_including_archived.assert_called_once()
    assert len(result) == 1


async def test_list_default_uses_usage_counts():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.list_with_usage_counts = AsyncMock(return_value=[(mock_tax, 3)])

    mock_response = MagicMock()
    mock_response.model_copy = MagicMock(return_value=MagicMock())
    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=mock_response):
        await svc.list(_USER_ID)

    svc._repo.list_with_usage_counts.assert_called_once()


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


async def test_get_success():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        await svc.get(_USER_ID, _TAX_ID)

    svc._repo.get_by_id.assert_called_once_with(user_id=_USER_ID, taxonomy_id=_TAX_ID)


async def test_get_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaxonomyNotFoundError):
        await svc.get(_USER_ID, _TAX_ID)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


async def test_update_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaxonomyNotFoundError):
        await svc.update(_TAX_ID, _make_update_payload(name="New"), user_id=_USER_ID)


async def test_update_raises_when_scope_narrowing_with_trade_assignments():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy(scope="trades,checkins")
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.count_assignments = AsyncMock(return_value=(5, 0, 0))  # trade_count=5

    with pytest.raises(TaxonomyValidationError):
        await svc.update(_TAX_ID, _make_update_payload(scope="checkins"), user_id=_USER_ID)


async def test_update_raises_when_scope_narrowing_with_checkin_assignments():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy(scope="trades,checkins")
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.count_assignments = AsyncMock(return_value=(0, 3, 0))  # checkin_count=3

    with pytest.raises(TaxonomyValidationError):
        await svc.update(_TAX_ID, _make_update_payload(scope="trades"), user_id=_USER_ID)


async def test_update_success():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    updated = _make_mock_taxonomy()
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.update = AsyncMock(return_value=updated)

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        await svc.update(_TAX_ID, _make_update_payload(name="New Name"), user_id=_USER_ID)

    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_update_raises_on_integrity_error():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.update = AsyncMock(side_effect=IntegrityError("dup", None, None))

    with pytest.raises(TaxonomyValidationError):
        await svc.update(_TAX_ID, _make_update_payload(name="New Name"), user_id=_USER_ID)


# ---------------------------------------------------------------------------
# get_assignment_counts
# ---------------------------------------------------------------------------


async def test_get_assignment_counts_success():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.count_assignments = AsyncMock(return_value=(2, 3, 1))

    result = await svc.get_assignment_counts(_TAX_ID, _USER_ID)

    assert result["trade_count"] == 2
    assert result["checkin_count"] == 3
    assert result["playbook_count"] == 1
    assert result["total_count"] == 6


async def test_get_assignment_counts_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaxonomyNotFoundError):
        await svc.get_assignment_counts(_TAX_ID, _USER_ID)


# ---------------------------------------------------------------------------
# archive / unarchive
# ---------------------------------------------------------------------------


async def test_archive_success():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    archived = _make_mock_taxonomy(is_archived=True)
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.archive = AsyncMock(return_value=archived)

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        await svc.archive(_TAX_ID, _USER_ID)

    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_archive_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaxonomyNotFoundError):
        await svc.archive(_TAX_ID, _USER_ID)


async def test_unarchive_success():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy(is_archived=True)
    unarchived = _make_mock_taxonomy(is_archived=False)
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.unarchive = AsyncMock(return_value=unarchived)

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        await svc.unarchive(_TAX_ID, _USER_ID)

    svc._cache.invalidate_user.assert_called_once_with(_USER_ID)


async def test_unarchive_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaxonomyNotFoundError):
        await svc.unarchive(_TAX_ID, _USER_ID)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


async def test_delete_raises_not_found():
    svc = _make_service()
    svc._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaxonomyNotFoundError):
        await svc.delete(_TAX_ID, user_id=_USER_ID)


async def test_delete_force_clears_assignments():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.delete_assignments = AsyncMock()
    svc._repo.delete = AsyncMock()

    result = await svc.delete(_TAX_ID, user_id=_USER_ID, force=True)

    assert result is None
    svc._repo.delete_assignments.assert_called_once_with(_TAX_ID)
    svc._repo.delete.assert_called_once_with(mock_tax)


async def test_delete_archives_when_assignments_exist():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    archived = _make_mock_taxonomy(is_archived=True)
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.count_assignments = AsyncMock(return_value=(2, 1, 0))
    svc._repo.archive = AsyncMock(return_value=archived)

    with patch("app.services.taxonomy_service.TaxonomyResponse.model_validate", return_value=MagicMock()):
        await svc.delete(_TAX_ID, user_id=_USER_ID)

    svc._repo.archive.assert_called_once_with(mock_tax)


async def test_delete_hard_deletes_when_no_assignments():
    svc = _make_service()
    mock_tax = _make_mock_taxonomy()
    svc._repo.get_by_id = AsyncMock(return_value=mock_tax)
    svc._repo.count_assignments = AsyncMock(return_value=(0, 0, 0))
    svc._repo.delete = AsyncMock()

    result = await svc.delete(_TAX_ID, user_id=_USER_ID)

    assert result is None
    svc._repo.delete.assert_called_once_with(mock_tax)
