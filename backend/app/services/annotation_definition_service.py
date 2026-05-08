"""Service layer for annotation definition management."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnnotationDefinitionNotFoundError,
    AnnotationDefinitionValidationError,
)
from app.repositories.annotation_definition_repository import (
    AnnotationDefinitionRepository,
)
from app.schemas.annotation_definition import (
    AnnotationDefinitionCreate,
    AnnotationDefinitionResponse,
    AnnotationDefinitionUpdate,
)


class AnnotationDefinitionService:
    """Business rules for annotation definition CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AnnotationDefinitionRepository(session)

    async def create(
        self,
        payload: AnnotationDefinitionCreate,
    ) -> AnnotationDefinitionResponse:
        try:
            item = await self._repo.create(payload)
        except IntegrityError as exc:
            raise AnnotationDefinitionValidationError(
                "annotation definition with this name and scope already exists"
            ) from exc
        return AnnotationDefinitionResponse.model_validate(item)

    async def list(self, scope: str | None = None) -> list[AnnotationDefinitionResponse]:
        items = await self._repo.list(scope=scope)
        return [AnnotationDefinitionResponse.model_validate(item) for item in items]

    async def get(self, definition_id: uuid.UUID) -> AnnotationDefinitionResponse:
        item = await self._repo.get_by_id(definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")
        return AnnotationDefinitionResponse.model_validate(item)

    async def update(
        self,
        definition_id: uuid.UUID,
        payload: AnnotationDefinitionUpdate,
    ) -> AnnotationDefinitionResponse:
        item = await self._repo.get_by_id(definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")

        if payload.type is not None and payload.type != item.type:
            raise AnnotationDefinitionValidationError("annotation type cannot be changed")

        current_scope = item.scope
        new_scope = payload.scope
        if new_scope is not None and new_scope != current_scope and current_scope == "both":
            trade_count, checkin_count = await self._repo.count_assignments(definition_id)
            narrowing_to_trades = new_scope == "trades" and checkin_count > 0
            narrowing_to_checkins = new_scope == "checkins" and trade_count > 0
            if narrowing_to_trades or narrowing_to_checkins:
                raise AnnotationDefinitionValidationError(
                    "scope narrowing is not permitted while assignments exist"
                )

        try:
            updated = await self._repo.update(item, payload)
        except IntegrityError as exc:
            raise AnnotationDefinitionValidationError(
                "annotation definition with this name and scope already exists"
            ) from exc
        return AnnotationDefinitionResponse.model_validate(updated)

    async def delete(
        self,
        definition_id: uuid.UUID,
    ) -> AnnotationDefinitionResponse | None:
        item = await self._repo.get_by_id(definition_id)
        if item is None:
            raise AnnotationDefinitionNotFoundError("annotation definition not found")

        trade_count, checkin_count = await self._repo.count_assignments(definition_id)
        if trade_count + checkin_count == 0:
            await self._repo.delete(item)
            return None

        archived = await self._repo.archive(item)
        return AnnotationDefinitionResponse.model_validate(archived)
