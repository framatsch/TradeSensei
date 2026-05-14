"""Repository for check-in annotation assignment persistence."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin_annotation import CheckinAnnotation


class CheckinAnnotationRepository:
    """Data-access operations for check-in annotation assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(
        self,
        checkin_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        typed_values: dict[str, Any],
    ) -> CheckinAnnotation:
        assignment = CheckinAnnotation(
            checkin_id=checkin_id,
            annotation_definition_id=annotation_definition_id,
            **typed_values,
        )
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def update(
        self,
        checkin_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        typed_values: dict[str, Any],
    ) -> CheckinAnnotation | None:
        result = await self._session.execute(
            select(CheckinAnnotation).where(
                CheckinAnnotation.checkin_id == checkin_id,
                CheckinAnnotation.annotation_definition_id == annotation_definition_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return None
        assignment.value_int = typed_values["value_int"]
        assignment.value_float = typed_values["value_float"]
        assignment.value_bool = typed_values["value_bool"]
        assignment.value_string = typed_values["value_string"]
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def remove(self, checkin_id: uuid.UUID, annotation_definition_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(CheckinAnnotation).where(
                CheckinAnnotation.checkin_id == checkin_id,
                CheckinAnnotation.annotation_definition_id == annotation_definition_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return False
        await self._session.delete(assignment)
        await self._session.flush()
        return True

    async def list_for_checkin(self, checkin_id: uuid.UUID) -> list[CheckinAnnotation]:
        result = await self._session.execute(select(CheckinAnnotation).where(CheckinAnnotation.checkin_id == checkin_id))
        return list(result.scalars().all())
