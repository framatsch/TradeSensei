"""Service layer for daily check-in operations."""

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.daily_checkin import FieldTypeEnum
from app.repositories.checkin_field_definition_repository import (
    CheckinFieldDefinitionRepository,
)
from app.repositories.daily_checkin_repository import DailyCheckinRepository
from app.repositories.market_index_repository import MarketIndexDefinitionRepository
from app.repositories.market_phase_definition_repository import (
    MarketPhaseDefinitionRepository,
)
from app.schemas.daily_checkin import (
    DailyCheckinCreate,
    DailyCheckinListResponse,
    DailyCheckinRead,
    DailyCheckinUpdate,
)
from app.services.cache_service import CacheService


class DailyCheckinService:
    """Business rules for daily check-ins."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = DailyCheckinRepository(session)
        self._field_repo = CheckinFieldDefinitionRepository(session)
        self._phase_repo = MarketPhaseDefinitionRepository(session)
        self._index_repo = MarketIndexDefinitionRepository(session)
        self._cache = CacheService()

    async def _validate_target_indices(
        self,
        user_id: uuid.UUID,
        target_index_ids: list[uuid.UUID] | None,
    ) -> None:
        """Validate that all target indices belong to the user."""
        if target_index_ids is None:
            return
        if not target_index_ids:
            return
        unique_ids = list(dict.fromkeys(target_index_ids))
        found = await self._index_repo.get_by_ids_for_user(user_id, unique_ids)
        if len(found) != len(unique_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="target_index_ids contains unknown ids",
            )

    async def _validate_market_phase(
        self,
        user_id: uuid.UUID,
        market_phase: str | None,
    ) -> None:
        """Validate market phase name against active user definitions."""
        if market_phase is None:
            return
        active = await self._phase_repo.list_by_user(user_id=user_id, is_active=True)
        active_names = {item.name for item in active}
        if market_phase not in active_names:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"unknown market_phase: {market_phase}",
            )

    async def _validate_custom_metrics(
        self,
        user_id: uuid.UUID,
        metrics: dict[str, int | bool] | None,
    ) -> None:
        """Validate custom metric keys and value types against active fields."""
        if metrics is None:
            return

        active_fields = await self._field_repo.list_by_user(
            user_id=user_id,
            is_active=True,
        )
        field_type_map = {item.field_name: item.field_type for item in active_fields}

        errors: list[str] = []
        for key, value in metrics.items():
            declared = field_type_map.get(key)
            if declared is None:
                errors.append(f"custom_metrics.{key}: unknown field")
                continue

            if declared == FieldTypeEnum.INTEGER:
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"custom_metrics.{key}: expected integer")
            elif declared == FieldTypeEnum.BOOLEAN and not isinstance(value, bool):
                errors.append(f"custom_metrics.{key}: expected boolean")

        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=errors,
            )

    def _validate_screenshot_urls(self, screenshot_urls: list[str] | None) -> None:
        """Validate screenshot URLs against configured storage public URL."""
        if screenshot_urls is None:
            return

        if not screenshot_urls:
            return

        storage_public_url = settings.storage_public_url
        if not storage_public_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "screenshot_urls is not available: object storage is not configured"
                ),
            )

        allowed_prefix = storage_public_url.rstrip("/") + "/"
        for url in screenshot_urls:
            if not url.startswith(allowed_prefix):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="screenshot_url must use configured storage domain",
                )

    async def create_checkin(
        self,
        user_id: uuid.UUID,
        payload: DailyCheckinCreate,
    ) -> DailyCheckinRead:
        """Create a new daily check-in with all validations."""
        await self._validate_market_phase(user_id, payload.market_phase)
        await self._validate_target_indices(user_id, payload.target_index_ids)
        await self._validate_custom_metrics(user_id, payload.custom_metrics)
        self._validate_screenshot_urls(payload.screenshot_urls)

        try:
            model = await self._repo.create(user_id=user_id, data=payload)
            await self._session.commit()
            await self._cache.invalidate_user(user_id)
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="daily check-in already exists for this date",
            ) from exc
        return DailyCheckinRead.model_validate(model)

    async def get_checkin(
        self,
        user_id: uuid.UUID,
        checkin_date: date,
    ) -> DailyCheckinRead:
        """Get one daily check-in by date for the user."""
        model = await self._repo.get_by_date_and_user(
            user_id=user_id,
            checkin_date=checkin_date,
        )
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="daily check-in not found",
            )
        return DailyCheckinRead.model_validate(model)

    async def list_checkins(
        self,
        user_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
        market_phase: str | None = None,
        cursor: date | None = None,
        limit: int = 30,
    ) -> DailyCheckinListResponse:
        """List daily check-ins with date-cursor pagination."""
        items, next_cursor, total = await self._repo.list_by_user(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            market_phase=market_phase,
            cursor=cursor,
            limit=limit,
        )
        return DailyCheckinListResponse(
            items=[DailyCheckinRead.model_validate(item) for item in items],
            next_cursor=next_cursor,
            total=total,
        )

    async def update_checkin(
        self,
        user_id: uuid.UUID,
        checkin_date: date,
        payload: DailyCheckinUpdate,
    ) -> DailyCheckinRead:
        """Patch an existing daily check-in."""
        model = await self._repo.get_by_date_and_user(
            user_id=user_id,
            checkin_date=checkin_date,
        )
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="daily check-in not found",
            )

        if "market_phase" in payload.model_fields_set:
            await self._validate_market_phase(user_id, payload.market_phase)
        if "custom_metrics" in payload.model_fields_set:
            await self._validate_custom_metrics(user_id, payload.custom_metrics)
        if "target_index_ids" in payload.model_fields_set:
            await self._validate_target_indices(user_id, payload.target_index_ids)
        if "screenshot_urls" in payload.model_fields_set:
            self._validate_screenshot_urls(payload.screenshot_urls)

        updated = await self._repo.update(model=model, data=payload)
        await self._session.commit()
        await self._cache.invalidate_user(user_id)
        return DailyCheckinRead.model_validate(updated)

    async def delete_checkin(self, user_id: uuid.UUID, checkin_date: date) -> None:
        """Delete a check-in by date for the user."""
        deleted = await self._repo.delete(user_id=user_id, checkin_date=checkin_date)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="daily check-in not found",
            )
        await self._session.commit()
        await self._cache.invalidate_user(user_id)
