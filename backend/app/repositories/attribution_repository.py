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

"""Repository for attribution analytics grouped by market phase."""

import uuid
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import Date, and_, case, cast, func, inspect, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import Spec5NotDeployedError
from app.models.account import Account
from app.models.daily_checkin import DailyCheckin
from app.models.trade import Trade
from app.models.trade_taxonomy import TradeTaxonomy
from app.schemas.analytics import DashboardFilterConfig


class PhaseAggregateRow(TypedDict):
    """Aggregated metrics for one market phase bucket."""

    market_phase: str
    trade_count: int
    winning_trades: int
    losing_trades: int
    gross_profit: Decimal
    gross_loss: Decimal
    avg_pnl: Decimal
    total_pnl: Decimal
    currency: str | None


class AttributionRepository:
    """SQL repository for market-phase attribution computations."""

    _table_checked: bool = False

    async def _ensure_daily_checkins_table(self, session: AsyncSession) -> None:
        """Raise if the daily_checkins table is unavailable."""
        if self._table_checked:
            return
        try:
            exists = await session.run_sync(lambda sync_session: inspect(sync_session.get_bind()).has_table("daily_checkins"))
        except ProgrammingError as exc:
            raise Spec5NotDeployedError("daily_checkins table not available") from exc
        if not exists:
            raise Spec5NotDeployedError("daily_checkins table not available")
        self._table_checked = True

    @staticmethod
    def _trade_predicates(
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        filter_config: DashboardFilterConfig,
    ) -> list[ColumnElement[bool]]:
        predicates: list[ColumnElement[bool]] = [
            Trade.user_id == user_id,
            Trade.account_id == Account.id,
            Account.portfolio_id == portfolio_id,
        ]

        if filter_config.status == "closed":
            predicates.append(Trade.closed_at.is_not(None))
            predicates.append(Trade.pnl.is_not(None))
        elif filter_config.status == "open":
            predicates.append(Trade.closed_at.is_(None))

        if filter_config.date_from is not None:
            predicates.append(cast(Trade.closed_at, Date) >= filter_config.date_from)
        if filter_config.date_to is not None:
            predicates.append(cast(Trade.closed_at, Date) <= filter_config.date_to)
        if filter_config.direction is not None:
            predicates.append(Trade.direction == filter_config.direction)
        if filter_config.account_ids:
            predicates.append(Trade.account_id.in_(filter_config.account_ids))
        if filter_config.playbook_ids:
            predicates.append(Trade.playbook_id.in_(filter_config.playbook_ids))

        return predicates

    async def compute_market_phase_correlation(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        filter_config: DashboardFilterConfig,
        session: AsyncSession,
    ) -> list[PhaseAggregateRow]:
        """Compute grouped attribution rows with one SQL GROUP BY query."""
        await self._ensure_daily_checkins_table(session)

        predicates = self._trade_predicates(
            portfolio_id=portfolio_id,
            user_id=user_id,
            filter_config=filter_config,
        )
        if filter_config.taxonomy_ids:
            taxonomy_subquery = (
                select(TradeTaxonomy.trade_id)
                .where(TradeTaxonomy.taxonomy_id.in_(filter_config.taxonomy_ids))
                .group_by(TradeTaxonomy.trade_id)
                .having(func.count(func.distinct(TradeTaxonomy.taxonomy_id)) == len(filter_config.taxonomy_ids))
            )
            predicates.append(Trade.id.in_(taxonomy_subquery))

        stmt = (
            select(
                DailyCheckin.market_phase.label("market_phase"),
                func.count(Trade.id).label("trade_count"),
                func.sum(case((Trade.pnl > 0, 1), else_=0)).label("winning_trades"),
                func.sum(case((Trade.pnl < 0, 1), else_=0)).label("losing_trades"),
                func.coalesce(
                    func.sum(case((Trade.pnl > 0, Trade.pnl), else_=0)),
                    0,
                ).label("gross_profit"),
                func.coalesce(
                    func.sum(case((Trade.pnl < 0, Trade.pnl), else_=0)),
                    0,
                ).label("gross_loss"),
                func.coalesce(func.avg(Trade.pnl), 0).label("avg_pnl"),
                func.coalesce(func.sum(Trade.pnl), 0).label("total_pnl"),
                func.min(Trade.currency).label("currency"),
            )
            .select_from(Trade)
            .join(Account, Account.id == Trade.account_id)
            .join(
                DailyCheckin,
                and_(
                    DailyCheckin.user_id == user_id,
                    DailyCheckin.date == cast(Trade.closed_at, Date),
                ),
            )
            .where(and_(*predicates))
            .where(DailyCheckin.market_phase.is_not(None))
            .group_by(DailyCheckin.market_phase)
            .order_by(DailyCheckin.market_phase.asc())
        )
        rows = (await session.execute(stmt)).all()
        return [
            PhaseAggregateRow(
                market_phase=str(row.market_phase),
                trade_count=int(row.trade_count or 0),
                winning_trades=int(row.winning_trades or 0),
                losing_trades=int(row.losing_trades or 0),
                gross_profit=Decimal(str(row.gross_profit or 0)),
                gross_loss=Decimal(str(row.gross_loss or 0)),
                avg_pnl=Decimal(str(row.avg_pnl or 0)),
                total_pnl=Decimal(str(row.total_pnl or 0)),
                currency=row.currency,
            )
            for row in rows
        ]

    async def compute_unmatched_counts(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        filter_config: DashboardFilterConfig,
        session: AsyncSession,
    ) -> tuple[int, int]:
        """Return unmatched and phase-unset trade counts for attribution response."""
        await self._ensure_daily_checkins_table(session)
        predicates = self._trade_predicates(
            portfolio_id=portfolio_id,
            user_id=user_id,
            filter_config=filter_config,
        )
        if filter_config.taxonomy_ids:
            taxonomy_subquery = (
                select(TradeTaxonomy.trade_id)
                .where(TradeTaxonomy.taxonomy_id.in_(filter_config.taxonomy_ids))
                .group_by(TradeTaxonomy.trade_id)
                .having(func.count(func.distinct(TradeTaxonomy.taxonomy_id)) == len(filter_config.taxonomy_ids))
            )
            predicates.append(Trade.id.in_(taxonomy_subquery))

        base = (
            select(
                Trade.id.label("trade_id"),
                DailyCheckin.id.label("checkin_id"),
                DailyCheckin.market_phase.label("market_phase"),
            )
            .select_from(Trade)
            .join(Account, Account.id == Trade.account_id)
            .outerjoin(
                DailyCheckin,
                and_(
                    DailyCheckin.user_id == user_id,
                    DailyCheckin.date == cast(Trade.closed_at, Date),
                ),
            )
            .where(and_(*predicates))
        ).subquery()

        counts_stmt = select(
            func.sum(case((base.c.checkin_id.is_(None), 1), else_=0)),
            func.sum(
                case(
                    (
                        and_(
                            base.c.checkin_id.is_not(None),
                            base.c.market_phase.is_(None),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
        )
        unmatched, phase_unset = (await session.execute(counts_stmt)).one()
        return int(unmatched or 0), int(phase_unset or 0)
