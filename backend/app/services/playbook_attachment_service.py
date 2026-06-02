# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Service layer for playbook image attachments."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConfigurationError,
    PlaybookAttachmentNotFoundError,
    PlaybookNotFoundError,
    UnsupportedContentTypeError,
)
from app.repositories.playbook_attachment_repository import PlaybookAttachmentRepository
from app.repositories.playbook_repository import PlaybookRepository
from app.schemas.playbook_attachment import (
    PlaybookImageRegisterRequest,
    PlaybookImageResponse,
    PlaybookImageUploadUrlResponse,
)
from app.services.storage_service import StorageService

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


class PlaybookAttachmentService:
    """Business rules for managing playbook image attachments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._playbook_repo = PlaybookRepository(session)
        self._attachment_repo = PlaybookAttachmentRepository(session)
        self._storage = StorageService()

    async def _ensure_playbook_exists(self, playbook_id: uuid.UUID, user_id: uuid.UUID) -> None:
        playbook = await self._playbook_repo.get_by_id(playbook_id=playbook_id, user_id=user_id)
        if playbook is None:
            raise PlaybookNotFoundError("playbook not found")

    async def generate_upload_url(
        self,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        content_type: str,
    ) -> PlaybookImageUploadUrlResponse:
        await self._ensure_playbook_exists(playbook_id, user_id)
        if content_type not in _ALLOWED_IMAGE_TYPES:
            raise UnsupportedContentTypeError("only image content types are accepted (png, jpeg, webp, gif)")
        if not settings.storage_backend:
            raise ConfigurationError("object storage is not configured")
        upload_url, key = self._storage.generate_playbook_upload_url(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
        )
        return PlaybookImageUploadUrlResponse(upload_url=upload_url, key=key)

    async def register(
        self,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: PlaybookImageRegisterRequest,
    ) -> PlaybookImageResponse:
        await self._ensure_playbook_exists(playbook_id, user_id)
        storage_url_str = payload.storage_url
        try:
            bucket, _ = self._storage.parse_storage_ref(storage_url_str)
        except ValueError as exc:
            raise UnsupportedContentTypeError("storage_url must use '{bucket}/{key}' format") from exc
        if settings.storage_bucket and bucket != settings.storage_bucket:
            raise UnsupportedContentTypeError(
                f"storage_url must reference the configured storage bucket '{settings.storage_bucket}'"
            )
        if payload.content_type not in _ALLOWED_IMAGE_TYPES:
            raise UnsupportedContentTypeError("only image content types are accepted")
        attachment = await self._attachment_repo.create(
            playbook_id=playbook_id,
            user_id=user_id,
            filename=payload.filename,
            storage_url=storage_url_str,
            content_type=payload.content_type,
        )
        return PlaybookImageResponse.model_validate(attachment, context={"storage_service": self._storage})

    async def list(self, playbook_id: uuid.UUID, user_id: uuid.UUID) -> list[PlaybookImageResponse]:
        await self._ensure_playbook_exists(playbook_id, user_id)
        attachments = await self._attachment_repo.list_for_playbook(playbook_id)
        return [PlaybookImageResponse.model_validate(a, context={"storage_service": self._storage}) for a in attachments]

    async def delete(
        self,
        playbook_id: uuid.UUID,
        attachment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_playbook_exists(playbook_id, user_id)
        attachment = await self._attachment_repo.get(attachment_id=attachment_id, playbook_id=playbook_id)
        if attachment is None:
            raise PlaybookAttachmentNotFoundError("attachment not found")
        await self._attachment_repo.delete(attachment)
