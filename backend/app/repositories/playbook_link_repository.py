"""Repository for playbook external link persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook_link import PlaybookLink


class PlaybookLinkRepository:
    """Data-access operations for playbook external links."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
        label: str,
        url: str,
    ) -> PlaybookLink:
        link = PlaybookLink(
            playbook_id=playbook_id,
            user_id=user_id,
            label=label,
            url=url,
        )
        self._session.add(link)
        await self._session.flush()
        await self._session.refresh(link)
        return link

    async def list_for_playbook(self, playbook_id: uuid.UUID) -> list[PlaybookLink]:
        result = await self._session.execute(select(PlaybookLink).where(PlaybookLink.playbook_id == playbook_id).order_by(PlaybookLink.created_at.asc()))
        return list(result.scalars().all())

    async def get(self, link_id: uuid.UUID, playbook_id: uuid.UUID) -> PlaybookLink | None:
        result = await self._session.execute(
            select(PlaybookLink).where(
                PlaybookLink.id == link_id,
                PlaybookLink.playbook_id == playbook_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, link: PlaybookLink) -> None:
        await self._session.delete(link)
        await self._session.flush()
