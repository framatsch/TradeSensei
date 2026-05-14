"""Repository for trade annotation assignment persistence."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_annotation import TradeAnnotation


class TradeAnnotationRepository:
    """Data-access operations for trade annotation assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(
        self,
        trade_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        typed_values: dict[str, Any],
    ) -> TradeAnnotation:
        assignment = TradeAnnotation(
            trade_id=trade_id,
            annotation_definition_id=annotation_definition_id,
            **typed_values,
        )
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def update(
        self,
        trade_id: uuid.UUID,
        annotation_definition_id: uuid.UUID,
        typed_values: dict[str, Any],
    ) -> TradeAnnotation | None:
        result = await self._session.execute(
            select(TradeAnnotation).where(
                TradeAnnotation.trade_id == trade_id,
                TradeAnnotation.annotation_definition_id == annotation_definition_id,
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

    async def remove(self, trade_id: uuid.UUID, annotation_definition_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(TradeAnnotation).where(
                TradeAnnotation.trade_id == trade_id,
                TradeAnnotation.annotation_definition_id == annotation_definition_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return False
        await self._session.delete(assignment)
        await self._session.flush()
        return True

    async def list_for_trade(self, trade_id: uuid.UUID) -> list[TradeAnnotation]:
        result = await self._session.execute(select(TradeAnnotation).where(TradeAnnotation.trade_id == trade_id))
        return list(result.scalars().all())
