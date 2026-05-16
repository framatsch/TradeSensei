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

"""Service layer for market index definition operations."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    MarketIndexDefinitionNotFoundError,
    MarketIndexDefinitionValidationError,
)
from app.models.market_index import MarketIndexDefinition
from app.repositories.market_index_repository import MarketIndexDefinitionRepository
from app.schemas.market_index import (
    MarketIndexDefinitionCreate,
    MarketIndexDefinitionResponse,
    MarketIndexDefinitionUpdate,
)
from app.services.cache_service import CacheService


class MarketIndexDefinitionService:
    """Business rules for market index definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MarketIndexDefinitionRepository(session)
        self._cache = CacheService()

    async def create_index(
        self,
        user_id: uuid.UUID,
        payload: MarketIndexDefinitionCreate,
    ) -> MarketIndexDefinitionResponse:
        existing = await self._repo.get_by_symbol_and_user(user_id, payload.symbol)
        if existing is not None:
            raise MarketIndexDefinitionValidationError("symbol already exists for this user")
        try:
            model = await self._repo.create(
                MarketIndexDefinition(
                    user_id=user_id,
                    symbol=payload.symbol,
                    name=payload.name,
                    tradingview_url=payload.tradingview_url,
                    is_active=payload.is_active,
                )
            )
            await self._session.commit()
            await self._cache.invalidate_user(user_id)
        except IntegrityError as exc:
            await self._session.rollback()
            raise MarketIndexDefinitionValidationError("symbol already exists for this user") from exc
        return MarketIndexDefinitionResponse.model_validate(model)

    async def list_indices(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> list[MarketIndexDefinitionResponse]:
        models = await self._repo.list_by_user(user_id=user_id, is_active=is_active)
        return [MarketIndexDefinitionResponse.model_validate(model) for model in models]

    async def update_index(
        self,
        user_id: uuid.UUID,
        index_id: uuid.UUID,
        payload: MarketIndexDefinitionUpdate,
    ) -> MarketIndexDefinitionResponse:
        model = await self._repo.get_by_id(index_id=index_id, user_id=user_id)
        if model is None:
            raise MarketIndexDefinitionNotFoundError("market index definition not found")
        try:
            updated = await self._repo.update(
                model=model,
                symbol=payload.symbol,
                name=payload.name,
                tradingview_url=payload.tradingview_url,
                is_active=payload.is_active,
            )
            await self._session.commit()
            await self._cache.invalidate_user(user_id)
        except IntegrityError as exc:
            await self._session.rollback()
            raise MarketIndexDefinitionValidationError("symbol already exists for this user") from exc
        return MarketIndexDefinitionResponse.model_validate(updated)

    async def delete_index(self, user_id: uuid.UUID, index_id: uuid.UUID) -> None:
        model = await self._repo.get_by_id(index_id=index_id, user_id=user_id)
        if model is None:
            raise MarketIndexDefinitionNotFoundError("market index definition not found")
        await self._repo.delete(model)
        await self._session.commit()
        await self._cache.invalidate_user(user_id)
