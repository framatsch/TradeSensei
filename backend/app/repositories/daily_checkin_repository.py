"""Repository for daily check-in persistence."""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.daily_checkin import DailyCheckin
from app.models.market_index import MarketIndexDefinition
from app.schemas.daily_checkin import DailyCheckinCreate, DailyCheckinUpdate


class DailyCheckinRepository:
    """Data-access operations for daily check-ins."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        data: DailyCheckinCreate,
    ) -> DailyCheckin:
        """Create and flush a daily check-in."""
        model = DailyCheckin(
            user_id=user_id,
            date=data.date,
            market_phase=data.market_phase,
            notes=data.notes,
            news_links=[str(link) for link in data.news_links],
            screenshot_urls=data.screenshot_urls,
            custom_metrics=data.custom_metrics,
        )
        if data.target_index_ids:
            result = await self._session.execute(
                select(MarketIndexDefinition).where(
                    MarketIndexDefinition.user_id == user_id,
                    MarketIndexDefinition.id.in_(data.target_index_ids),
                )
            )
            model.target_indices = list(result.scalars().all())
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_date_and_user(
        self,
        user_id: uuid.UUID,
        checkin_date: date,
    ) -> DailyCheckin | None:
        """Fetch one check-in by unique (user_id, date)."""
        result = await self._session.execute(
            select(DailyCheckin)
            .where(
                DailyCheckin.user_id == user_id,
                DailyCheckin.date == checkin_date,
            )
            .options(selectinload(DailyCheckin.target_indices))
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
        market_phase: str | None = None,
        cursor: date | None = None,
        limit: int = 30,
    ) -> tuple[Sequence[DailyCheckin], date | None, int]:
        """Cursor-paginated check-ins ordered by date descending."""
        clamped_limit = max(1, min(limit, 90))
        base_stmt = (
            select(DailyCheckin)
            .where(DailyCheckin.user_id == user_id)
            .options(selectinload(DailyCheckin.target_indices))
        )
        if from_date is not None:
            base_stmt = base_stmt.where(DailyCheckin.date >= from_date)
        if to_date is not None:
            base_stmt = base_stmt.where(DailyCheckin.date <= to_date)
        if market_phase is not None:
            base_stmt = base_stmt.where(DailyCheckin.market_phase == market_phase)

        page_stmt = base_stmt
        if cursor is not None:
            page_stmt = page_stmt.where(DailyCheckin.date < cursor)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total = int(count_result.scalar_one() or 0)

        page_stmt = page_stmt.order_by(DailyCheckin.date.desc()).limit(
            clamped_limit + 1
        )
        page_result = await self._session.execute(page_stmt)
        rows = list(page_result.scalars().all())

        has_more = len(rows) > clamped_limit
        items = rows[:clamped_limit]
        next_cursor = items[-1].date if has_more and items else None
        return items, next_cursor, total

    async def update(
        self,
        model: DailyCheckin,
        data: DailyCheckinUpdate,
    ) -> DailyCheckin:
        """Apply partial updates to a check-in."""
        update_data = data.model_dump(exclude_unset=True)
        if "news_links" in update_data and update_data["news_links"] is not None:
            update_data["news_links"] = [
                str(link) for link in update_data["news_links"]
            ]
        target_index_ids = update_data.pop("target_index_ids", None)
        for field, value in update_data.items():
            setattr(model, field, value)
        if target_index_ids is not None:
            if target_index_ids:
                result = await self._session.execute(
                    select(MarketIndexDefinition).where(
                        MarketIndexDefinition.user_id == model.user_id,
                        MarketIndexDefinition.id.in_(target_index_ids),
                    )
                )
                model.target_indices = list(result.scalars().all())
            else:
                model.target_indices = []
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def delete(self, user_id: uuid.UUID, checkin_date: date) -> bool:
        """Delete a check-in by date for a user."""
        result = await self._session.execute(
            delete(DailyCheckin)
            .where(
                DailyCheckin.user_id == user_id,
                DailyCheckin.date == checkin_date,
            )
            .returning(DailyCheckin.id)
        )
        deleted = result.scalar_one_or_none()
        await self._session.flush()
        return deleted is not None
