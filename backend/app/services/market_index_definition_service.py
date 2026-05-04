"""Service layer for market index definition operations."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="symbol already exists for this user",
            )
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="symbol already exists for this user",
            ) from exc
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="market index definition not found",
            )
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="symbol already exists for this user",
            ) from exc
        return MarketIndexDefinitionResponse.model_validate(updated)

    async def delete_index(self, user_id: uuid.UUID, index_id: uuid.UUID) -> None:
        model = await self._repo.get_by_id(index_id=index_id, user_id=user_id)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="market index definition not found",
            )
        await self._repo.delete(model)
        await self._session.commit()
        await self._cache.invalidate_user(user_id)
