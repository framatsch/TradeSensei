"""Service layer for daily check-in operations."""

import re
import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    DailyCheckinAlreadyExistsError,
    DailyCheckinNotFoundError,
    DailyCheckinValidationError,
)
from app.repositories.daily_checkin_repository import DailyCheckinRepository
from app.repositories.market_index_repository import MarketIndexDefinitionRepository
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
        self._index_repo = MarketIndexDefinitionRepository(session)
        self._cache = CacheService()
        self._market_phase_pattern = re.compile(r"^[a-z0-9_]{1,50}$")

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
            raise DailyCheckinValidationError("target_index_ids contains unknown ids")

    async def _validate_market_phase(
        self,
        user_id: uuid.UUID,
        market_phase: str | None,
    ) -> None:
        """Validate market phase value shape."""
        _ = user_id
        if market_phase is not None and not market_phase.strip():
            raise DailyCheckinValidationError("unknown market_phase")
        if market_phase is not None and not self._market_phase_pattern.fullmatch(market_phase):
            raise DailyCheckinValidationError("unknown market_phase")

    async def _validate_custom_metrics(
        self,
        user_id: uuid.UUID,
        metrics: dict[str, int | bool] | None,
    ) -> None:
        """Validate custom metrics payload shape."""
        _ = user_id
        if metrics is None:
            return

        errors: list[str] = []
        for key, value in metrics.items():
            if not key or not isinstance(key, str):
                errors.append("custom_metrics key: invalid")
            if not isinstance(value, (int, bool)):
                errors.append(f"custom_metrics.{key}: expected integer or boolean")

        if errors:
            raise DailyCheckinValidationError(errors)

    def _validate_screenshot_urls(self, screenshot_urls: list[str] | None) -> None:
        """Validate screenshot URLs against configured storage public URL."""
        if screenshot_urls is None:
            return

        if not screenshot_urls:
            return

        storage_public_url = settings.storage_public_url
        if not storage_public_url:
            raise DailyCheckinValidationError("screenshot_urls is not available: object storage is not configured")

        allowed_prefix = storage_public_url.rstrip("/") + "/"
        for url in screenshot_urls:
            if not url.startswith(allowed_prefix):
                raise DailyCheckinValidationError("screenshot_url must use configured storage domain")

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
            raise DailyCheckinAlreadyExistsError("daily check-in already exists for this date") from exc
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
            raise DailyCheckinNotFoundError("daily check-in not found")
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
            raise DailyCheckinNotFoundError("daily check-in not found")

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
            raise DailyCheckinNotFoundError("daily check-in not found")
        await self._session.commit()
        await self._cache.invalidate_user(user_id)

    async def update_modelbook_flag(self, user_id: uuid.UUID, checkin_date: date, is_modelbook: bool) -> DailyCheckinRead:
        checkin = await self._repo.update_modelbook_flag(user_id, checkin_date, is_modelbook)
        if not checkin:
            raise DailyCheckinNotFoundError("daily check-in not found")
        return DailyCheckinRead.model_validate(checkin)
