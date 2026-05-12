"""Repository for check-in taxonomy assignment persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checkin_taxonomy import CheckinTaxonomy


class CheckinTaxonomyRepository:
    """Data-access operations for check-in taxonomy assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(self, checkin_id: uuid.UUID, taxonomy_id: uuid.UUID) -> CheckinTaxonomy:
        assignment = CheckinTaxonomy(checkin_id=checkin_id, taxonomy_id=taxonomy_id)
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def remove(self, checkin_id: uuid.UUID, taxonomy_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(CheckinTaxonomy).where(
                CheckinTaxonomy.checkin_id == checkin_id,
                CheckinTaxonomy.taxonomy_id == taxonomy_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return False
        await self._session.delete(assignment)
        await self._session.flush()
        return True

    async def list_for_checkin(self, checkin_id: uuid.UUID) -> list[CheckinTaxonomy]:
        result = await self._session.execute(select(CheckinTaxonomy).where(CheckinTaxonomy.checkin_id == checkin_id))
        return list(result.scalars().all())
