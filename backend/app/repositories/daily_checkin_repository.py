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

"""Repository for daily check-in persistence."""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import and_, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.checkin_annotation import CheckinAnnotation
from app.models.checkin_taxonomy import CheckinTaxonomy
from app.models.daily_checkin import DailyCheckin
from app.models.market_index import MarketIndexDefinition
from app.repositories._annotation_filter import apply_annotation_filters
from app.schemas.annotation_filter import AnnotationFilterItem
from app.schemas.daily_checkin import DailyCheckinCreate, DailyCheckinUpdate


class DailyCheckinRepository:
    """Data-access operations for daily check-ins."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_by_id_with_target_indices(
        self,
        checkin_id: uuid.UUID,
    ) -> DailyCheckin:
        """Fetch a check-in with target indices eagerly loaded."""
        result = await self._session.execute(select(DailyCheckin).where(DailyCheckin.id == checkin_id).options(selectinload(DailyCheckin.target_indices)))
        return result.scalar_one()

    async def get_by_id_and_user(
        self,
        checkin_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DailyCheckin | None:
        """Fetch a check-in by id and user with metadata relationships loaded."""
        result = await self._session.execute(
            select(DailyCheckin)
            .where(
                DailyCheckin.id == checkin_id,
                DailyCheckin.user_id == user_id,
            )
            .options(
                selectinload(DailyCheckin.target_indices),
                selectinload(DailyCheckin.taxonomy_assignments).selectinload(CheckinTaxonomy.taxonomy),
                selectinload(DailyCheckin.annotation_assignments).selectinload(CheckinAnnotation.annotation_definition),
            )
        )
        return result.scalar_one_or_none()

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
        return await self._get_by_id_with_target_indices(model.id)

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
            .options(
                selectinload(DailyCheckin.target_indices),
                selectinload(DailyCheckin.taxonomy_assignments).selectinload(CheckinTaxonomy.taxonomy),
                selectinload(DailyCheckin.annotation_assignments).selectinload(CheckinAnnotation.annotation_definition),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
        target_indices: list[uuid.UUID] | None = None,
        taxonomy_ids: list[uuid.UUID] | None = None,
        annotation_filters: list[AnnotationFilterItem] | None = None,
        has_media: bool | None = None,
        cursor: date | None = None,
        offset: int | None = None,
        limit: int = 30,
    ) -> tuple[Sequence[DailyCheckin], date | None, int]:
        """Cursor-paginated check-ins ordered by date descending."""
        clamped_limit = max(1, min(limit, 90))
        base_stmt = select(DailyCheckin).where(DailyCheckin.user_id == user_id).options(selectinload(DailyCheckin.target_indices), selectinload(DailyCheckin.taxonomy_assignments).selectinload(CheckinTaxonomy.taxonomy), selectinload(DailyCheckin.annotation_assignments).selectinload(CheckinAnnotation.annotation_definition))
        if from_date is not None:
            base_stmt = base_stmt.where(DailyCheckin.date >= from_date)
        if to_date is not None:
            base_stmt = base_stmt.where(DailyCheckin.date <= to_date)
        if target_indices is not None and len(target_indices) > 0:
            from app.models.market_index import checkin_market_indices
            base_stmt = base_stmt.join(checkin_market_indices).where(checkin_market_indices.c.index_id.in_(target_indices))
        if taxonomy_ids is not None and len(taxonomy_ids) > 0:
            base_stmt = base_stmt.join(
                CheckinTaxonomy,
                # Use OR semantics for REST API (consistent with trade list)
                and_(CheckinTaxonomy.checkin_id == DailyCheckin.id, CheckinTaxonomy.taxonomy_id.in_(taxonomy_ids)),
            )
        if annotation_filters:
            base_stmt = apply_annotation_filters(
                base_stmt,
                CheckinAnnotation,
                CheckinAnnotation.checkin_id,
                DailyCheckin.id,
                user_id,
                annotation_filters,
            )
        if has_media is True:
            base_stmt = base_stmt.where(func.cardinality(DailyCheckin.screenshot_urls) > 0)
        elif has_media is False:
            base_stmt = base_stmt.where(func.cardinality(DailyCheckin.screenshot_urls) == 0)

        page_stmt = base_stmt
        if cursor is not None:
            page_stmt = page_stmt.where(DailyCheckin.date < cursor)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total = int(count_result.scalar_one() or 0)

        page_stmt = page_stmt.order_by(DailyCheckin.date.desc())
        
        if offset is not None:
            page_stmt = page_stmt.offset(offset)
            
        page_stmt = page_stmt.limit(clamped_limit + 1)
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
            update_data["news_links"] = [str(link) for link in update_data["news_links"]]
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
        return await self._get_by_id_with_target_indices(model.id)

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
