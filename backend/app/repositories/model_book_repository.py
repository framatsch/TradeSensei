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

import datetime as dt
import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_checkin import DailyCheckin
from app.models.trade import Trade


class ModelBookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_entries(
        self,
        user_id: uuid.UUID,
        entity_type: Literal["trade", "checkin", "all"],
        from_date: dt.date | None,
        to_date: dt.date | None,
        page: int,
        per_page: int,
    ) -> tuple[list[dict[str, Any]], int]:
        # This implementation uses separate queries since we just need simple union-like logic.
        # Alternatively we can query both and merge/sort in Python if counts are low,
        # or use SQLAlchemy UNION ALL.

        trades: list[dict[str, Any]] = []
        checkins: list[dict[str, Any]] = []

        if entity_type in ("trade", "all"):
            stmt_trade = select(Trade).where(Trade.user_id == user_id, Trade.is_modelbook.is_(True))
            if from_date:
                stmt_trade = stmt_trade.where(Trade.opened_at >= dt.datetime.combine(from_date, dt.time.min, tzinfo=dt.UTC))
            if to_date:
                stmt_trade = stmt_trade.where(Trade.opened_at <= dt.datetime.combine(to_date, dt.time.max, tzinfo=dt.UTC))
            stmt_trade = stmt_trade.order_by(Trade.opened_at.desc())

            trade_result = await self.session.execute(stmt_trade)
            for t in trade_result.scalars().all():
                tags = [assignment.taxonomy.name for assignment in t.taxonomy_assignments if assignment.taxonomy is not None]
                trades.append(
                    {
                        "type": "trade",
                        "id": t.id,
                        "date": t.opened_at,
                        "symbol": t.symbol,
                        "direction": t.direction,
                        "asset_class": t.asset_class,
                        "result_r": None,
                        "net_pnl": t.net_pnl,
                        "image_urls": t.image_urls or [],
                        "tags": tags,
                    }
                )

        if entity_type in ("checkin", "all"):
            stmt_checkin = select(DailyCheckin).where(DailyCheckin.user_id == user_id, DailyCheckin.is_modelbook.is_(True))
            if from_date:
                stmt_checkin = stmt_checkin.where(DailyCheckin.date >= from_date)
            if to_date:
                stmt_checkin = stmt_checkin.where(DailyCheckin.date <= to_date)
            stmt_checkin = stmt_checkin.order_by(DailyCheckin.date.desc())

            checkin_result = await self.session.execute(stmt_checkin)
            for c in checkin_result.scalars().all():
                # combine date to datetime for sorting
                dt_val = dt.datetime.combine(c.date, dt.time.min, tzinfo=dt.UTC)
                checkins.append(
                    {
                        "type": "checkin",
                        "id": c.id,
                        "date": dt_val,
                        "market_phase": c.market_phase,
                        "screenshot_urls": c.screenshot_urls or [],
                        "regime_color": None,
                        "target_indices": c.target_indices or [],
                    }
                )

        # Merge and sort
        combined = trades + checkins
        combined.sort(key=lambda x: x["date"], reverse=True)

        total = len(combined)
        start = (page - 1) * per_page
        end = start + per_page
        return combined[start:end], total
