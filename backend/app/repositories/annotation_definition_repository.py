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


from typing import Any
from sqlalchemy.dialects.postgresql import insert as pg_insert

class AnnotationDefinitionRepository:
    """Data-access operations for annotation definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def seed_defaults(self, user_id: uuid.UUID) -> None:
        """Insert default annotation definitions if they do not exist."""
        defaults: list[dict[str, Any]] = [
            {
                "name": "Conviction",
                "type": "int",
                "scope": "both",
                "description": "Pre-trade conviction level",
                "scale_labels": {"min": 1, "max": 5},
            },
            {
                "name": "R-Multiple",
                "type": "float",
                "scope": "trades",
                "description": "Return per unit of risk",
                "scale_labels": None,
            },
        ]
        stmt = pg_insert(AnnotationDefinition).values(
            [
                {
                    "user_id": user_id,
                    "name": row["name"],
                    "type": row["type"],
                    "scope": row["scope"],
                    "description": row["description"],
                    "scale_labels": row["scale_labels"],
                    "is_archived": False,
                }
                for row in defaults
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_annotation_definitions_user_name_scope",
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def create(self, user_id: uuid.UUID, payload: AnnotationDefinitionCreate) -> AnnotationDefinition:
        definition = AnnotationDefinition(user_id=user_id, **payload.model_dump())
        self._session.add(definition)
        await self._session.flush()
        await self._session.refresh(definition)
        return definition

    async def get_by_id(self, user_id: uuid.UUID, definition_id: uuid.UUID) -> AnnotationDefinition | None:
        result = await self._session.execute(
            select(AnnotationDefinition).where(AnnotationDefinition.user_id == user_id, AnnotationDefinition.id == definition_id)
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: uuid.UUID, scope: str | None = None) -> list[AnnotationDefinition]:
        stmt = (
            select(AnnotationDefinition)
            .where(AnnotationDefinition.user_id == user_id, AnnotationDefinition.is_archived.is_(False))
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
