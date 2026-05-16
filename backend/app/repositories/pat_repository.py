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

"""Repository for personal access token persistence."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pat import PersonalAccessToken


class PersonalAccessTokenRepository:
    """Data access for personal access token records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        token_hash: str,
        expires_at: datetime | None,
    ) -> PersonalAccessToken:
        token = PersonalAccessToken(
            user_id=user_id,
            name=name,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def list_for_user(self, user_id: uuid.UUID) -> list[PersonalAccessToken]:
        result = await self._session.execute(
            select(PersonalAccessToken).where(PersonalAccessToken.user_id == user_id).order_by(PersonalAccessToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id_for_user(
        self,
        token_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PersonalAccessToken | None:
        result = await self._session.execute(
            select(PersonalAccessToken).where(
                PersonalAccessToken.id == token_id,
                PersonalAccessToken.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_hash_with_owner(
        self,
        token_hash: str,
    ) -> PersonalAccessToken | None:
        result = await self._session.execute(
            select(PersonalAccessToken).options(selectinload(PersonalAccessToken.owner)).where(PersonalAccessToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(
        self,
        token: PersonalAccessToken,
        *,
        used_at: datetime,
    ) -> None:
        token.last_used_at = used_at
        self._session.add(token)
        await self._session.flush()

    async def revoke(self, token: PersonalAccessToken) -> PersonalAccessToken:
        token.is_revoked = True
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token
