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

"""Service layer for playbook external links."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PlaybookLinkNotFoundError, PlaybookNotFoundError
from app.repositories.playbook_link_repository import PlaybookLinkRepository
from app.repositories.playbook_repository import PlaybookRepository
from app.schemas.playbook_link import PlaybookLinkCreate, PlaybookLinkResponse


class PlaybookLinkService:
    """Business rules for managing playbook external links."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._playbook_repo = PlaybookRepository(session)
        self._link_repo = PlaybookLinkRepository(session)

    async def _ensure_playbook_exists(self, playbook_id: uuid.UUID, user_id: uuid.UUID) -> None:
        playbook = await self._playbook_repo.get_by_id(playbook_id=playbook_id, user_id=user_id)
        if playbook is None:
            raise PlaybookNotFoundError("playbook not found")

    async def create(
        self,
        playbook_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: PlaybookLinkCreate,
    ) -> PlaybookLinkResponse:
        await self._ensure_playbook_exists(playbook_id, user_id)
        url_str = str(payload.url)
        link = await self._link_repo.create(
            playbook_id=playbook_id,
            user_id=user_id,
            label=payload.label,
            url=url_str,
        )
        return PlaybookLinkResponse.model_validate(link)

    async def list(self, playbook_id: uuid.UUID, user_id: uuid.UUID) -> list[PlaybookLinkResponse]:
        await self._ensure_playbook_exists(playbook_id, user_id)
        links = await self._link_repo.list_for_playbook(playbook_id)
        return [PlaybookLinkResponse.model_validate(lnk) for lnk in links]

    async def delete(
        self,
        playbook_id: uuid.UUID,
        link_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._ensure_playbook_exists(playbook_id, user_id)
        link = await self._link_repo.get(link_id=link_id, playbook_id=playbook_id)
        if link is None:
            raise PlaybookLinkNotFoundError("link not found")
        await self._link_repo.delete(link)
