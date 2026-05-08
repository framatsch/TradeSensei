"""Unit tests for annotation definition service business rules."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    AnnotationDefinitionNotFoundError,
    AnnotationDefinitionValidationError,
)
from app.schemas.annotation_definition import (
    AnnotationDefinitionCreate,
    AnnotationDefinitionUpdate,
)
from app.services.annotation_definition_service import AnnotationDefinitionService


def _definition_obj(*, scope: str = "both", type_value: str = "int", is_archived: bool = False) -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Confidence",
        type=type_value,
        scope=scope,
        description=None,
        scale_labels={"min": 1, "max": 10},
        icon_identifier=None,
        is_archived=is_archived,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def service(mock_session: AsyncMock) -> AnnotationDefinitionService:
    return AnnotationDefinitionService(mock_session)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_hard_delete_when_no_assignments(
    service: AnnotationDefinitionService,
) -> None:
    definition = _definition_obj()
    service._repo.get_by_id = AsyncMock(return_value=definition)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(0, 0))  # type: ignore[method-assign]
    service._repo.delete = AsyncMock()  # type: ignore[method-assign]

    result = await service.delete(definition.id)

    assert result is None
    service._repo.delete.assert_awaited_once_with(definition)  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_soft_delete_when_assignments_exist(
    service: AnnotationDefinitionService,
) -> None:
    definition = _definition_obj()
    archived = _definition_obj(is_archived=True)
    archived.id = definition.id
    service._repo.get_by_id = AsyncMock(return_value=definition)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(0, 2))  # type: ignore[method-assign]
    service._repo.archive = AsyncMock(return_value=archived)  # type: ignore[method-assign]

    result = await service.delete(definition.id)

    assert result is not None
    assert result.is_archived is True
    service._repo.archive.assert_awaited_once_with(definition)  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_blocks_type_change(
    service: AnnotationDefinitionService,
) -> None:
    definition = _definition_obj(type_value="int")
    service._repo.get_by_id = AsyncMock(return_value=definition)  # type: ignore[method-assign]

    with pytest.raises(AnnotationDefinitionValidationError, match="type cannot be changed"):
        await service.update(definition.id, AnnotationDefinitionUpdate(type="float"))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_blocks_scope_narrowing_with_assignments(
    service: AnnotationDefinitionService,
) -> None:
    definition = _definition_obj(scope="both")
    service._repo.get_by_id = AsyncMock(return_value=definition)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(2, 0))  # type: ignore[method-assign]

    with pytest.raises(AnnotationDefinitionValidationError, match="scope narrowing"):
        await service.update(definition.id, AnnotationDefinitionUpdate(scope="checkins"))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_allows_scope_change_without_excluded_assignments(
    service: AnnotationDefinitionService,
) -> None:
    definition = _definition_obj(scope="both")
    updated = _definition_obj(scope="trades")
    updated.id = definition.id
    service._repo.get_by_id = AsyncMock(return_value=definition)  # type: ignore[method-assign]
    service._repo.count_assignments = AsyncMock(return_value=(1, 0))  # type: ignore[method-assign]
    service._repo.update = AsyncMock(return_value=updated)  # type: ignore[method-assign]

    result = await service.update(definition.id, AnnotationDefinitionUpdate(scope="trades"))

    assert result.scope == "trades"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_raises_not_found(service: AnnotationDefinitionService) -> None:
    service._repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

    with pytest.raises(AnnotationDefinitionNotFoundError):
        await service.delete(uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_duplicate_name_scope_raises_validation(
    service: AnnotationDefinitionService,
) -> None:
    from sqlalchemy.exc import IntegrityError

    service._repo.create = AsyncMock(  # type: ignore[method-assign]
        side_effect=IntegrityError("stmt", {}, Exception("dup"))
    )

    with pytest.raises(AnnotationDefinitionValidationError, match="already exists"):
        await service.create(
            AnnotationDefinitionCreate(name="Confidence", type="int", scope="trades")
        )
