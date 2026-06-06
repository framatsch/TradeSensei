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

"""Unit tests for taxonomy service business rules."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import TaxonomyNotFoundError, TaxonomyValidationError
from app.schemas.taxonomy import TaxonomyCreate, TaxonomyUpdate
from app.services.taxonomy_service import TaxonomyService


def _taxonomy_obj(*, scope: str = "both", is_archived: bool = False) -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Setup",
        scope=scope,
        color_hex="#22cc88",
        description=None,
        icon_identifier=None,
        is_archived=is_archived,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def service(mock_session: AsyncMock) -> TaxonomyService:
    return TaxonomyService(mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_hard_delete_when_no_assignments(service: TaxonomyService) -> None:
    taxonomy = _taxonomy_obj()
    service._repo.get_by_id = AsyncMock(return_value=taxonomy)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(0, 0))  # type: ignore[method-assign]
    service._repo.delete = AsyncMock()  # type: ignore[method-assign]

    result = await service.delete(taxonomy.id)

    assert result is None
    service._repo.delete.assert_awaited_once_with(taxonomy)  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_soft_delete_when_assignments_exist(service: TaxonomyService) -> None:
    taxonomy = _taxonomy_obj()
    archived = _taxonomy_obj(scope="both", is_archived=True)
    archived.id = taxonomy.id
    service._repo.get_by_id = AsyncMock(return_value=taxonomy)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(1, 0))  # type: ignore[method-assign]
    service._repo.archive = AsyncMock(return_value=archived)  # type: ignore[method-assign]

    result = await service.delete(taxonomy.id)

    assert result is not None
    assert result.is_archived is True
    service._repo.archive.assert_awaited_once_with(taxonomy)  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_blocks_scope_narrowing_with_assignments(
    service: TaxonomyService,
) -> None:
    taxonomy = _taxonomy_obj(scope="both")
    service._repo.get_by_id = AsyncMock(return_value=taxonomy)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(0, 2))  # type: ignore[method-assign]

    with pytest.raises(TaxonomyValidationError, match="is currently in use"):
        await service.update(taxonomy.id, TaxonomyUpdate(scope="trades"))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_allows_scope_change_without_excluded_assignments(
    service: TaxonomyService,
) -> None:
    taxonomy = _taxonomy_obj(scope="both")
    updated = _taxonomy_obj(scope="trades")
    updated.id = taxonomy.id
    service._repo.get_by_id = AsyncMock(return_value=taxonomy)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(3, 0))  # type: ignore[method-assign]
    service._repo.update = AsyncMock(return_value=updated)  # type: ignore[method-assign]

    result = await service.update(taxonomy.id, TaxonomyUpdate(scope="trades"))

    assert result.scope == "trades"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_raises_not_found(service: TaxonomyService) -> None:
    service._repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

    with pytest.raises(TaxonomyNotFoundError):
        await service.delete(uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_duplicate_name_scope_raises_validation(
    service: TaxonomyService,
) -> None:
    from sqlalchemy.exc import IntegrityError

    service._repo.create = AsyncMock(  # type: ignore[method-assign]
        side_effect=IntegrityError("stmt", {}, Exception("dup"))
    )

    with pytest.raises(TaxonomyValidationError, match="already exists"):
        await service.create(
            TaxonomyCreate(name="Setup", scope="trades", color_hex="#22cc88")
        )
