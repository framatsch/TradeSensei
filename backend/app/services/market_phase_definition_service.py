"""Service layer for market phase definition operations."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_phase_definition_repository import (
    MarketPhaseDefinitionRepository,
)
from app.schemas.daily_checkin import (
    MarketPhaseDefinitionCreate,
    MarketPhaseDefinitionRead,
    MarketPhaseDefinitionUpdate,
)
from app.services.cache_service import CacheService


class MarketPhaseDefinitionService:
    """Business rules for market phase definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MarketPhaseDefinitionRepository(session)
        self._cache = CacheService()

    async def create_phase(
        self,
        user_id: uuid.UUID,
        payload: MarketPhaseDefinitionCreate,
    ) -> MarketPhaseDefinitionRead:
        """Create a new phase definition with uniqueness enforcement."""
        existing = await self._repo.get_by_name_and_user(user_id, payload.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="name already exists for this user",
            )

        try:
            model = await self._repo.create(
                user_id=user_id,
                name=payload.name,
                label=payload.label,
                color_hex=payload.color_hex,
            )
            await self._session.commit()
            await self._cache.invalidate_user(user_id)
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="name already exists for this user",
            ) from exc
        return MarketPhaseDefinitionRead.model_validate(model)

    async def list_phases(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> list[MarketPhaseDefinitionRead]:
        """List user phase definitions with optional activity filter."""
        models = await self._repo.list_by_user(user_id=user_id, is_active=is_active)
        return [MarketPhaseDefinitionRead.model_validate(model) for model in models]

    async def update_phase(
        self,
        user_id: uuid.UUID,
        phase_id: uuid.UUID,
        payload: MarketPhaseDefinitionUpdate,
    ) -> MarketPhaseDefinitionRead:
        """Update mutable phase-definition columns only."""
        model = await self._repo.get_by_id(definition_id=phase_id, user_id=user_id)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="market phase definition not found",
            )

        try:
            updated = await self._repo.update(
                model=model,
                label=payload.label,
                color_hex=payload.color_hex,
                is_active=payload.is_active,
            )
            await self._session.commit()
            await self._cache.invalidate_user(user_id)
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="name already exists for this user",
            ) from exc
        return MarketPhaseDefinitionRead.model_validate(updated)
