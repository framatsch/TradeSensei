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

"""Repository for querying metadata correlation data."""

import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import Date, String, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.account import Account
from app.models.annotation_definition import AnnotationDefinition
from app.models.checkin_annotation import CheckinAnnotation
from app.models.checkin_taxonomy import CheckinTaxonomy
from app.models.daily_checkin import DailyCheckin
from app.models.portfolio import Portfolio
from app.models.taxonomy import Taxonomy
from app.models.trade import Trade
from app.models.trade_annotation import TradeAnnotation
from app.models.trade_taxonomy import TradeTaxonomy
from app.schemas.analytics import AxisType


class MetadataCorrelationRepository:
    """Repository for finding correlations between annotations and taxonomies."""

    def _build_axis_join(
        self,
        axis_type: AxisType,
        axis_id: uuid.UUID,
        stmt: Any,
        is_x_axis: bool,
    ) -> tuple[Any, Any, Any]:
        """Build the join clauses and selection expressions for an axis."""
        prefix = "x" if is_x_axis else "y"

        if axis_type == "checkin_annotation":
            ca_alias = aliased(CheckinAnnotation, name=f"{prefix}_ca")
            ad_alias = aliased(AnnotationDefinition, name=f"{prefix}_ad")
            stmt = stmt.join(
                ca_alias,
                and_(
                    ca_alias.checkin_id == DailyCheckin.id,
                    ca_alias.annotation_definition_id == axis_id,
                ),
            ).join(
                ad_alias,
                ad_alias.id == ca_alias.annotation_definition_id,
            )
            val_expr = func.coalesce(
                cast(ca_alias.value_float, String),
                cast(ca_alias.value_int, String),
                cast(ca_alias.value_bool, String),
                ca_alias.value_string,
            ).label(f"{prefix}_value")
            label_expr = val_expr.label(f"{prefix}_label")  # Labels match raw values for annotations
            return stmt, val_expr, label_expr

        elif axis_type == "trade_annotation":
            ta_alias = aliased(TradeAnnotation, name=f"{prefix}_ta")
            ad_alias = aliased(AnnotationDefinition, name=f"{prefix}_ad")
            stmt = stmt.join(
                ta_alias,
                and_(
                    ta_alias.trade_id == Trade.id,
                    ta_alias.annotation_definition_id == axis_id,
                ),
            ).join(
                ad_alias,
                ad_alias.id == ta_alias.annotation_definition_id,
            )
            val_expr = func.coalesce(
                cast(ta_alias.value_float, String),
                cast(ta_alias.value_int, String),
                cast(ta_alias.value_bool, String),
                ta_alias.value_string,
            ).label(f"{prefix}_value")
            label_expr = val_expr.label(f"{prefix}_label")
            return stmt, val_expr, label_expr

        elif axis_type == "checkin_taxonomy":
            ct_alias = aliased(CheckinTaxonomy, name=f"{prefix}_ct")
            tax_alias = aliased(Taxonomy, name=f"{prefix}_tax")
            stmt = stmt.join(
                ct_alias,
                and_(
                    ct_alias.checkin_id == DailyCheckin.id,
                    ct_alias.taxonomy_id == axis_id,
                ),
            ).join(
                tax_alias,
                tax_alias.id == ct_alias.taxonomy_id,
            )
            val_expr = tax_alias.name.label(f"{prefix}_value")
            label_expr = tax_alias.name.label(f"{prefix}_label")
            return stmt, val_expr, label_expr

        elif axis_type == "trade_taxonomy":
            tt_alias = aliased(TradeTaxonomy, name=f"{prefix}_tt")
            tax_alias = aliased(Taxonomy, name=f"{prefix}_tax")
            stmt = stmt.join(
                tt_alias,
                and_(
                    tt_alias.trade_id == Trade.id,
                    tt_alias.taxonomy_id == axis_id,
                ),
            ).join(
                tax_alias,
                tax_alias.id == tt_alias.taxonomy_id,
            )
            val_expr = tax_alias.name.label(f"{prefix}_value")
            label_expr = tax_alias.name.label(f"{prefix}_label")
            return stmt, val_expr, label_expr

        raise ValueError(f"Unknown axis type: {axis_type}")

    async def get_correlated_pairs(
        self,
        session: AsyncSession,
        portfolio_id: uuid.UUID,
        x_axis_type: AxisType,
        x_axis_id: uuid.UUID,
        y_axis_type: AxisType,
        y_axis_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        account_ids: list[uuid.UUID] | None = None,
        base_asset: str | None = None,
    ) -> list[Mapping[str, Any]]:
        """Fetch joined trade and checkin data for correlation."""
        # Start with Trades joined with Accounts and Portfolios and DailyCheckins
        stmt = (
            select(
                cast(Trade.closed_at, Date).label("date"),
                Trade.id.label("trade_id"),
                Trade.symbol.label("trade_symbol"),
                Trade.pnl.label("trade_pnl"),
            )
            .join(Account, Account.id == Trade.account_id)
            .join(Portfolio, Portfolio.id == Account.portfolio_id)
            .join(
                DailyCheckin,
                and_(
                    DailyCheckin.user_id == Portfolio.user_id,
                    DailyCheckin.date == cast(Trade.closed_at, Date),
                ),
            )
            .where(
                Account.portfolio_id == portfolio_id,
                Trade.closed_at.is_not(None),
                Trade.pnl.is_not(None),
            )
        )

        if date_from:
            stmt = stmt.where(cast(Trade.closed_at, Date) >= date_from)
        if date_to:
            stmt = stmt.where(cast(Trade.closed_at, Date) <= date_to)
        if account_ids:
            stmt = stmt.where(Trade.account_id.in_(account_ids))
        if base_asset:
            stmt = stmt.where(Trade.symbol.ilike(f"%{base_asset}%"))

        # Add X axis joins and columns
        stmt, x_val_expr, x_lbl_expr = self._build_axis_join(x_axis_type, x_axis_id, stmt, is_x_axis=True)
        # Add Y axis joins and columns
        stmt, y_val_expr, y_lbl_expr = self._build_axis_join(y_axis_type, y_axis_id, stmt, is_x_axis=False)

        # Add the resolved values to the SELECT clause
        stmt = stmt.add_columns(x_val_expr, x_lbl_expr, y_val_expr, y_lbl_expr)

        result = await session.execute(stmt)
        # Using dict instead of _mapping to satisfy typing
        return [dict(row._mapping) for row in result.all()]

    async def get_filtered_trades_aggregate(
        self,
        session: AsyncSession,
        portfolio_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        account_ids: list[uuid.UUID] | None = None,
        base_asset: str | None = None,
    ) -> Mapping[str, Any]:
        """Helper to get total trades, win rate, and max drawdown for the filtered trades."""
        stmt = (
            select(
                func.count(Trade.id).label("total_trades_count"),
                func.sum(case((Trade.pnl > 0, 1), else_=0)).label("winning_trades"),
                # For drawdown, since it's hard to compute max drawdown over arbitrary filtered rows purely in SQL without window functions,
                # we'll approximate or use an existing method if available.
                # We'll fetch the necessary pieces, but a true max_drawdown calculation usually needs a running sum.
                # To keep it simple based on the task description, we'll return the sums and handle logic later or
                # use a simpler approach (like fetching raw eq curves).
                # Wait, the task says "returns `total_trades_count`, `win_rate`, and `max_drawdown_pct` from `trades` table".
            )
            .join(Account, Account.id == Trade.account_id)
            .where(
                Account.portfolio_id == portfolio_id,
                Trade.closed_at.is_not(None),
                Trade.pnl.is_not(None),
            )
        )

        if date_from:
            stmt = stmt.where(cast(Trade.closed_at, Date) >= date_from)
        if date_to:
            stmt = stmt.where(cast(Trade.closed_at, Date) <= date_to)
        if account_ids:
            stmt = stmt.where(Trade.account_id.in_(account_ids))
        if base_asset:
            stmt = stmt.where(Trade.symbol.ilike(f"%{base_asset}%"))

        result = await session.execute(stmt)
        row = result.first()

        if not row or row.total_trades_count == 0:
            return {"total_trades_count": 0, "win_rate": 0, "max_drawdown_pct": 0}

        win_rate = row.winning_trades / row.total_trades_count

        # Proper max drawdown needs full equity curve. The service can compute it if we fetch rows,
        # but the task specifically asks this helper to "return total_trades_count, win_rate, and max_drawdown_pct".
        # Let's fetch the PnL sequence to compute max drawdown in Python since SQL max drawdown is complex.

        dd_stmt = (
            select(Trade.pnl)
            .join(Account, Account.id == Trade.account_id)
            .where(
                Account.portfolio_id == portfolio_id,
                Trade.closed_at.is_not(None),
                Trade.pnl.is_not(None),
            )
            .order_by(Trade.closed_at.asc())
        )

        if date_from:
            dd_stmt = dd_stmt.where(cast(Trade.closed_at, Date) >= date_from)
        if date_to:
            dd_stmt = dd_stmt.where(cast(Trade.closed_at, Date) <= date_to)
        if account_ids:
            dd_stmt = dd_stmt.where(Trade.account_id.in_(account_ids))
        if base_asset:
            dd_stmt = dd_stmt.where(Trade.symbol.ilike(f"%{base_asset}%"))

        dd_result = await session.execute(dd_stmt)
        pnls = [r[0] for r in dd_result.all()]

        max_drawdown_pct = 0.0
        peak = 0.0
        equity = 0.0

        for pnl in pnls:
            equity += float(pnl)
            if equity > peak:
                peak = equity
            if peak > 0:
                dd = (peak - equity) / peak
                if dd > max_drawdown_pct:
                    max_drawdown_pct = dd

        return {
            "total_trades_count": row.total_trades_count,
            "win_rate": win_rate,
            "max_drawdown_pct": max_drawdown_pct,
        }
