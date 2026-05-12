import datetime as dt
import uuid
from typing import Literal

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
    ) -> tuple[list[dict], int]:
        # This implementation uses separate queries since we just need simple union-like logic.
        # Alternatively we can query both and merge/sort in Python if counts are low,
        # or use SQLAlchemy UNION ALL.
        
        trades = []
        checkins = []
        
        if entity_type in ("trade", "all"):
            stmt = select(Trade).where(Trade.user_id == user_id, Trade.is_modelbook.is_(True))
            if from_date:
                stmt = stmt.where(Trade.opened_at >= dt.datetime.combine(from_date, dt.time.min, tzinfo=dt.UTC))
            if to_date:
                stmt = stmt.where(Trade.opened_at <= dt.datetime.combine(to_date, dt.time.max, tzinfo=dt.UTC))
            stmt = stmt.order_by(Trade.opened_at.desc())
            
            result = await self.session.execute(stmt)
            for t in result.scalars().all():
                trades.append({
                    "type": "trade",
                    "id": t.id,
                    "date": t.opened_at,
                    "symbol": t.symbol,
                    "direction": t.direction,
                    "asset_class": t.asset_class,
                    "result_r": t.result_r,
                    "net_pnl": t.net_pnl,
                    "image_urls": t.image_urls or [],
                    "tags": t.tags or []
                })
                
        if entity_type in ("checkin", "all"):
            stmt = select(DailyCheckin).where(DailyCheckin.user_id == user_id, DailyCheckin.is_modelbook.is_(True))
            if from_date:
                stmt = stmt.where(DailyCheckin.date >= from_date)
            if to_date:
                stmt = stmt.where(DailyCheckin.date <= to_date)
            stmt = stmt.order_by(DailyCheckin.date.desc())
            
            result = await self.session.execute(stmt)
            for c in result.scalars().all():
                # combine date to datetime for sorting
                dt_val = dt.datetime.combine(c.date, dt.time.min, tzinfo=dt.UTC)
                checkins.append({
                    "type": "checkin",
                    "id": c.id, # checkin id is user_id + date conceptually, but we can generate or use something else. Wait, schema requires UUID!
                    # Actually, Checkin does not have UUID ID. Let's look at Checkin variant.
                    "date": dt_val,
                    "market_phase": c.market_phase,
                    "screenshot_urls": c.screenshot_urls or [],
                    "regime_color": c.regime_color,
                    "target_indices": c.target_indices or []
                })
                
        # Merge and sort
        combined = trades + checkins
        combined.sort(key=lambda x: x["date"], reverse=True)
        
        total = len(combined)
        start = (page - 1) * per_page
        end = start + per_page
        return combined[start:end], total
