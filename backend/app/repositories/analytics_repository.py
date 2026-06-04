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

"""Repository for set-based analytics aggregation queries."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import Date, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.account import Account
from app.models.trade import Trade
from app.models.trade_taxonomy import TradeTaxonomy
from app.schemas.analytics import DashboardFilterConfig


class EquityRow(TypedDict):
    """Raw equity input row returned from SQL."""

    trade_id: uuid.UUID
    closed_date: date
    pnl: Decimal
    currency: str | None


class RawAggregates(TypedDict):
    """Aggregate data needed for AnalyticsService response assembly."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    gross_profit: Decimal
    gross_loss: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    avg_trade_duration_hours: Decimal | None
    equity_rows: list[EquityRow]


class AnalyticsRepository:
    """SQL-only analytics repository for summary computations."""

    @staticmethod
    def _base_predicates(
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
        if filter_config.symbols:
            symbol_conditions = [Trade.symbol.ilike(f"{sym}%") for sym in filter_config.symbols]
            predicates.append(or_(*symbol_conditions))
        if filter_config.excluded_symbols:
            for sym in filter_config.excluded_symbols:
                predicates.append(Trade.symbol.not_ilike(f"{sym}%"))
        if filter_config.asset_classes:
            predicates.append(Trade.asset_class.in_(filter_config.asset_classes))

        return predicates

    async def compute_summary(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        filter_config: DashboardFilterConfig,
        session: AsyncSession,
    ) -> RawAggregates:
        """Compute scalar aggregates and equity rows using SQL queries only."""
        predicates = self._base_predicates(portfolio_id, user_id, filter_config)

        if filter_config.taxonomy_ids:
            taxonomy_subquery = (
                select(TradeTaxonomy.trade_id)
                .where(TradeTaxonomy.taxonomy_id.in_(filter_config.taxonomy_ids))
                .group_by(TradeTaxonomy.trade_id)
                .having(func.count(func.distinct(TradeTaxonomy.taxonomy_id)) == len(filter_config.taxonomy_ids))
            )
            predicates.append(Trade.id.in_(taxonomy_subquery))

        eff_pnl = func.coalesce(Trade.net_pnl, Trade.pnl)
        aggregate_stmt = (
            select(
                func.count(Trade.id).label("total_trades"),
                func.sum(case((eff_pnl > 0, 1), else_=0)).label("winning_trades"),
                func.sum(case((eff_pnl < 0, 1), else_=0)).label("losing_trades"),
                func.coalesce(
                    func.sum(case((eff_pnl > 0, eff_pnl), else_=0)),
                    0,
                ).label("gross_profit"),
                func.coalesce(
                    func.sum(case((eff_pnl < 0, eff_pnl), else_=0)),
                    0,
                ).label("gross_loss"),
                func.avg(case((eff_pnl > 0, eff_pnl), else_=None)).label("avg_win"),
                func.avg(case((eff_pnl < 0, eff_pnl), else_=None)).label("avg_loss"),
                func.avg(func.extract("epoch", Trade.closed_at - Trade.opened_at) / 3600).label("avg_trade_duration_hours"),
            )
            .select_from(Trade)
            .join(Account, Account.id == Trade.account_id)
            .where(and_(*predicates))
        )
        aggregate_row = (await session.execute(aggregate_stmt)).one()

        equity_stmt = (
            select(
                Trade.id.label("trade_id"),
                cast(Trade.closed_at, Date).label("closed_date"),
                func.coalesce(Trade.net_pnl, Trade.pnl).label("pnl"),
                Trade.currency.label("currency"),
            )
            .select_from(Trade)
            .join(Account, Account.id == Trade.account_id)
            .where(and_(*predicates))
            .order_by(Trade.closed_at.asc(), Trade.id.asc())
        )
        equity_rows = [
            EquityRow(
                trade_id=row.trade_id,
                closed_date=row.closed_date,
                pnl=Decimal(str(row.pnl)) if row.pnl is not None else Decimal("0"),
                currency=row.currency,
            )
            for row in (await session.execute(equity_stmt)).all()
        ]

        return RawAggregates(
            total_trades=int(aggregate_row.total_trades or 0),
            winning_trades=int(aggregate_row.winning_trades or 0),
            losing_trades=int(aggregate_row.losing_trades or 0),
            gross_profit=Decimal(str(aggregate_row.gross_profit or 0)),
            gross_loss=Decimal(str(aggregate_row.gross_loss or 0)),
            avg_win=Decimal(str(aggregate_row.avg_win or 0)),
            avg_loss=Decimal(str(aggregate_row.avg_loss or 0)),
            avg_trade_duration_hours=(Decimal(str(aggregate_row.avg_trade_duration_hours)) if aggregate_row.avg_trade_duration_hours is not None else None),
            equity_rows=equity_rows,
        )
