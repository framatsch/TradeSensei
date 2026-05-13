"""Repository for playbook image attachment persistence."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playbook_attachment import PlaybookAttachment


class PlaybookAttachmentRepository:
    """Data-access operations for playbook image attachments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        storage_url: str,
        content_type: str,
    ) -> PlaybookAttachment:
        attachment = PlaybookAttachment(
            playbook_id=playbook_id,
            user_id=user_id,
            filename=filename,
            storage_url=storage_url,
            content_type=content_type,
        )
        self._session.add(attachment)
        await self._session.flush()
        await self._session.refresh(attachment)
        return attachment

    async def list_for_playbook(self, playbook_id: uuid.UUID) -> list[PlaybookAttachment]:
        result = await self._session.execute(
            select(PlaybookAttachment).where(PlaybookAttachment.playbook_id == playbook_id).order_by(PlaybookAttachment.created_at.asc())
        )
        return list(result.scalars().all())

    async def get(self, attachment_id: uuid.UUID, playbook_id: uuid.UUID) -> PlaybookAttachment | None:
        result = await self._session.execute(
            select(PlaybookAttachment).where(
                PlaybookAttachment.id == attachment_id,
                PlaybookAttachment.playbook_id == playbook_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, attachment: PlaybookAttachment) -> None:
        await self._session.delete(attachment)
        await self._session.flush()
