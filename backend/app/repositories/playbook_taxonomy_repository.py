"""Repository for playbook taxonomy assignment persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook_taxonomy import PlaybookTaxonomy


class PlaybookTaxonomyRepository:
    """Data-access operations for playbook taxonomy assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assign(self, playbook_id: uuid.UUID, taxonomy_id: uuid.UUID) -> PlaybookTaxonomy:
        assignment = PlaybookTaxonomy(playbook_id=playbook_id, taxonomy_id=taxonomy_id)
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def remove(self, playbook_id: uuid.UUID, taxonomy_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(PlaybookTaxonomy).where(
                PlaybookTaxonomy.playbook_id == playbook_id,
                PlaybookTaxonomy.taxonomy_id == taxonomy_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return False
        await self._session.delete(assignment)
        await self._session.flush()
        return True

    async def list_for_playbook(self, playbook_id: uuid.UUID) -> list[PlaybookTaxonomy]:
        result = await self._session.execute(
            select(PlaybookTaxonomy).where(PlaybookTaxonomy.playbook_id == playbook_id)
        )
        return list(result.scalars().all())

    async def exists(self, playbook_id: uuid.UUID, taxonomy_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(PlaybookTaxonomy).where(
                PlaybookTaxonomy.playbook_id == playbook_id,
                PlaybookTaxonomy.taxonomy_id == taxonomy_id,
            )
        )
        return result.scalar_one_or_none() is not None
