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

"""Unit tests for TradeMetadataService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    MetadataAssignmentNotFoundError,
    MetadataAssignmentValidationError,
    TaxonomyNotFoundError,
    TradeNotFoundError,
)
from app.services.trade_metadata_service import TradeMetadataService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_TRADE_ID = uuid.uuid4()
_TAXONOMY_ID = uuid.uuid4()
_ANNOTATION_DEF_ID = uuid.uuid4()


def _make_service():
    svc = TradeMetadataService.__new__(TradeMetadataService)
    svc._session = AsyncMock()
    svc._session.begin_nested = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=None), __aexit__=AsyncMock(return_value=False)))
    svc._trade_repo = AsyncMock()
    svc._taxonomy_repo = AsyncMock()
    svc._annotation_definition_repo = AsyncMock()
    svc._trade_taxonomy_repo = AsyncMock()
    svc._trade_annotation_repo = AsyncMock()
    return svc


def _make_mock_trade():
    t = MagicMock()
    t.id = _TRADE_ID
    return t


def _make_mock_taxonomy(scope: str = "trades", is_archived: bool = False):
    tx = MagicMock()
    tx.id = _TAXONOMY_ID
    tx.scope = scope
    tx.is_archived = is_archived
    return tx


def _make_mock_annotation_def(scope: str = "trades", is_archived: bool = False, type_: str = "int"):
    d = MagicMock()
    d.id = _ANNOTATION_DEF_ID
    d.scope = scope
    d.is_archived = is_archived
    d.type = type_
    d.scale_labels = None
    return d


# ---------------------------------------------------------------------------
# _ensure_trade_exists
# ---------------------------------------------------------------------------


async def test_ensure_trade_exists_raises_when_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TradeNotFoundError):
        await svc._ensure_trade_exists(_TRADE_ID, _USER_ID)


async def test_ensure_trade_exists_passes_when_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    # Should not raise
    await svc._ensure_trade_exists(_TRADE_ID, _USER_ID)


# ---------------------------------------------------------------------------
# assign_taxonomy
# ---------------------------------------------------------------------------


async def test_assign_taxonomy_raises_trade_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TradeNotFoundError):
        await svc.assign_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)


async def test_assign_taxonomy_raises_taxonomy_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._taxonomy_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TaxonomyNotFoundError):
        await svc.assign_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)


async def test_assign_taxonomy_raises_when_archived():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._taxonomy_repo.get_by_id = AsyncMock(return_value=_make_mock_taxonomy(is_archived=True))

    with pytest.raises(MetadataAssignmentValidationError):
        await svc.assign_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)


async def test_assign_taxonomy_raises_when_incompatible_scope():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._taxonomy_repo.get_by_id = AsyncMock(return_value=_make_mock_taxonomy(scope="checkins"))

    with pytest.raises(MetadataAssignmentValidationError):
        await svc.assign_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)


async def test_assign_taxonomy_raises_on_duplicate():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._taxonomy_repo.get_by_id = AsyncMock(return_value=_make_mock_taxonomy())

    # Make begin_nested raise IntegrityError on __aexit__
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(side_effect=IntegrityError("dup", None, None))
    svc._session.begin_nested = MagicMock(return_value=cm)

    with pytest.raises(MetadataAssignmentValidationError):
        await svc.assign_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)


# ---------------------------------------------------------------------------
# remove_taxonomy
# ---------------------------------------------------------------------------


async def test_remove_taxonomy_raises_trade_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TradeNotFoundError):
        await svc.remove_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)


async def test_remove_taxonomy_raises_not_found_when_assignment_missing():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._trade_taxonomy_repo.remove = AsyncMock(return_value=False)

    with pytest.raises(MetadataAssignmentNotFoundError):
        await svc.remove_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)


async def test_remove_taxonomy_success():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._trade_taxonomy_repo.remove = AsyncMock(return_value=True)

    await svc.remove_taxonomy(_TRADE_ID, _TAXONOMY_ID, _USER_ID)

    svc._trade_taxonomy_repo.remove.assert_called_once_with(_TRADE_ID, _TAXONOMY_ID)


# ---------------------------------------------------------------------------
# assign_annotation
# ---------------------------------------------------------------------------


async def test_assign_annotation_raises_trade_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TradeNotFoundError):
        await svc.assign_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, 42, _USER_ID)


async def test_assign_annotation_raises_definition_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._annotation_definition_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(MetadataAssignmentValidationError):
        await svc.assign_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, 42, _USER_ID)


async def test_assign_annotation_raises_when_archived():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._annotation_definition_repo.get_by_id = AsyncMock(
        return_value=_make_mock_annotation_def(is_archived=True)
    )

    with pytest.raises(MetadataAssignmentValidationError):
        await svc.assign_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, 42, _USER_ID)


async def test_assign_annotation_raises_when_incompatible_scope():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._annotation_definition_repo.get_by_id = AsyncMock(
        return_value=_make_mock_annotation_def(scope="checkins")
    )

    with pytest.raises(MetadataAssignmentValidationError):
        await svc.assign_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, 42, _USER_ID)


# ---------------------------------------------------------------------------
# update_annotation
# ---------------------------------------------------------------------------


async def test_update_annotation_raises_trade_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TradeNotFoundError):
        await svc.update_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, 42, _USER_ID)


async def test_update_annotation_raises_definition_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._annotation_definition_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(MetadataAssignmentValidationError):
        await svc.update_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, 42, _USER_ID)


async def test_update_annotation_raises_not_found_when_assignment_missing():
    svc = _make_service()
    mock_def = _make_mock_annotation_def()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._annotation_definition_repo.get_by_id = AsyncMock(return_value=mock_def)
    svc._trade_annotation_repo.update = AsyncMock(return_value=None)

    with patch("app.services.trade_metadata_service.map_value_to_column", return_value={"value_int": 42}), pytest.raises(MetadataAssignmentNotFoundError):
        await svc.update_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, 42, _USER_ID)


# ---------------------------------------------------------------------------
# remove_annotation
# ---------------------------------------------------------------------------


async def test_remove_annotation_raises_trade_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(TradeNotFoundError):
        await svc.remove_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, _USER_ID)


async def test_remove_annotation_raises_not_found_when_assignment_missing():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._trade_annotation_repo.remove = AsyncMock(return_value=False)

    with pytest.raises(MetadataAssignmentNotFoundError):
        await svc.remove_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, _USER_ID)


async def test_remove_annotation_success():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=_make_mock_trade())
    svc._trade_annotation_repo.remove = AsyncMock(return_value=True)

    await svc.remove_annotation(_TRADE_ID, _ANNOTATION_DEF_ID, _USER_ID)

    svc._trade_annotation_repo.remove.assert_called_once_with(_TRADE_ID, _ANNOTATION_DEF_ID)


# ---------------------------------------------------------------------------
# _validate_annotation_assignment (pure logic)
# ---------------------------------------------------------------------------


async def test_validate_annotation_assignment_raises_when_archived():
    svc = _make_service()
    mock_def = _make_mock_annotation_def(is_archived=True)

    with pytest.raises(MetadataAssignmentValidationError):
        svc._validate_annotation_assignment(mock_def, 42)


async def test_validate_annotation_assignment_raises_when_scope_incompatible():
    svc = _make_service()
    mock_def = _make_mock_annotation_def(scope="checkins")

    with pytest.raises(MetadataAssignmentValidationError):
        svc._validate_annotation_assignment(mock_def, 42)
