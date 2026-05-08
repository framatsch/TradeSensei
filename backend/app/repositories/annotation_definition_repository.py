"""Repository for annotation definition persistence and assignment counts."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation_definition import AnnotationDefinition
from app.models.checkin_annotation import CheckinAnnotation
from app.models.trade_annotation import TradeAnnotation
from app.schemas.annotation_definition import (
    AnnotationDefinitionCreate,
    AnnotationDefinitionUpdate,
)


class AnnotationDefinitionRepository:
    """Data-access operations for annotation definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: AnnotationDefinitionCreate) -> AnnotationDefinition:
        definition = AnnotationDefinition(**payload.model_dump())
        self._session.add(definition)
        await self._session.flush()
        await self._session.refresh(definition)
        return definition

    async def get_by_id(self, definition_id: uuid.UUID) -> AnnotationDefinition | None:
        result = await self._session.execute(
            select(AnnotationDefinition).where(AnnotationDefinition.id == definition_id)
        )
        return result.scalar_one_or_none()

    async def list(self, scope: str | None = None) -> list[AnnotationDefinition]:
        stmt = (
            select(AnnotationDefinition)
            .where(AnnotationDefinition.is_archived.is_(False))
            .order_by(AnnotationDefinition.name.asc())
        )
        if scope is not None:
            stmt = stmt.where(AnnotationDefinition.scope.in_([scope, "both"]))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        definition: AnnotationDefinition,
        payload: AnnotationDefinitionUpdate,
    ) -> AnnotationDefinition:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(definition, field, value)
        self._session.add(definition)
        await self._session.flush()
        await self._session.refresh(definition)
        return definition

    async def count_assignments(self, definition_id: uuid.UUID) -> tuple[int, int]:
        trade_result = await self._session.execute(
            select(func.count())
            .select_from(TradeAnnotation)
            .where(TradeAnnotation.annotation_definition_id == definition_id)
        )
        checkin_result = await self._session.execute(
            select(func.count())
            .select_from(CheckinAnnotation)
            .where(CheckinAnnotation.annotation_definition_id == definition_id)
        )
        return int(trade_result.scalar_one() or 0), int(checkin_result.scalar_one() or 0)

    async def delete(self, definition: AnnotationDefinition) -> None:
        await self._session.delete(definition)
        await self._session.flush()

    async def archive(self, definition: AnnotationDefinition) -> AnnotationDefinition:
        definition.is_archived = True
        self._session.add(definition)
        await self._session.flush()
        await self._session.refresh(definition)
        return definition
