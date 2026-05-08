"""Repository for trade taxonomy assignment persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_taxonomy import TradeTaxonomy


class TradeTaxonomyRepository:
    """Data-access operations for trade taxonomy assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(self, trade_id: uuid.UUID, taxonomy_id: uuid.UUID) -> TradeTaxonomy:
        assignment = TradeTaxonomy(trade_id=trade_id, taxonomy_id=taxonomy_id)
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def remove(self, trade_id: uuid.UUID, taxonomy_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(TradeTaxonomy).where(
                TradeTaxonomy.trade_id == trade_id,
                TradeTaxonomy.taxonomy_id == taxonomy_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return False
        await self._session.delete(assignment)
        await self._session.flush()
        return True

    async def list_for_trade(self, trade_id: uuid.UUID) -> list[TradeTaxonomy]:
        result = await self._session.execute(
            select(TradeTaxonomy).where(TradeTaxonomy.trade_id == trade_id)
        )
        return list(result.scalars().all())
