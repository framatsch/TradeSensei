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

import contextlib
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation_definition import AnnotationDefinition
from app.repositories.metadata_correlation_repository import MetadataCorrelationRepository
from app.schemas.analytics import (
    AxisType,
    MetadataCorrelationDataPoint,
    MetadataCorrelationKPIs,
    MetadataCorrelationResponse,
)
from app.utils.scope_utils import scope_contains


class MetadataCorrelationService:
    """Service for metadata correlation analytics."""

    def __init__(self) -> None:
        self.repository = MetadataCorrelationRepository()

    async def _get_axis_meta(self, session: AsyncSession, axis_type: AxisType, axis_id: uuid.UUID) -> tuple[str, str]:
        """Return (data_type, name) and perform scope validation."""
        if "taxonomy" in axis_type:
            # We assume taxonomy exists since it's a UUID, name could be fetched if needed,
            # but usually frontend provides the ID. For name, we can fetch it.
            from sqlalchemy import select

            from app.models.taxonomy import Taxonomy

            result = await session.execute(select(Taxonomy).where(Taxonomy.id == axis_id))
            tax = result.scalar_one_or_none()
            if not tax:
                raise HTTPException(status_code=404, detail=f"Taxonomy {axis_id} not found")

            # Validate scope for taxonomies too
            if axis_type == "checkin_taxonomy" and not scope_contains(tax.scope, "checkins"):
                raise HTTPException(status_code=422, detail=f"Taxonomy {axis_id} scope mismatch")
            if axis_type == "trade_taxonomy" and not scope_contains(tax.scope, "trades"):
                raise HTTPException(status_code=422, detail=f"Taxonomy {axis_id} scope mismatch")

            return "taxonomy", tax.name

        # Annotation definition
        from sqlalchemy import select

        ad_result = await session.execute(select(AnnotationDefinition).where(AnnotationDefinition.id == axis_id))
        ad = ad_result.scalar_one_or_none()
        if not ad:
            raise HTTPException(status_code=404, detail=f"AnnotationDefinition {axis_id} not found")

        # Validate scope
        if axis_type == "checkin_annotation" and not scope_contains(ad.scope, "checkins"):
            raise HTTPException(status_code=422, detail=f"Annotation {axis_id} scope mismatch")
        if axis_type == "trade_annotation" and not scope_contains(ad.scope, "trades"):
            raise HTTPException(status_code=422, detail=f"Annotation {axis_id} scope mismatch")

        data_type_raw = str(ad.type).lower()
        if data_type_raw in ("int", "float"):
            data_type = "number"
        elif data_type_raw == "bool":
            data_type = "boolean"
        else:
            data_type = "string"

        return data_type, ad.name

    async def get_correlation(
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
    ) -> MetadataCorrelationResponse:
        """Get correlation analytics."""
        if x_axis_id == y_axis_id and x_axis_type == y_axis_type:
            raise HTTPException(status_code=422, detail="X and Y axes must differ")

        x_data_type, x_name = await self._get_axis_meta(session, x_axis_type, x_axis_id)
        y_data_type, y_name = await self._get_axis_meta(session, y_axis_type, y_axis_id)

        pairs = await self.repository.get_correlated_pairs(
            session=session,
            portfolio_id=portfolio_id,
            x_axis_type=x_axis_type,
            x_axis_id=x_axis_id,
            y_axis_type=y_axis_type,
            y_axis_id=y_axis_id,
            date_from=date_from,
            date_to=date_to,
            account_ids=account_ids,
            base_asset=base_asset,
        )

        agg = await self.repository.get_filtered_trades_aggregate(
            session=session,
            portfolio_id=portfolio_id,
            date_from=date_from,
            date_to=date_to,
            account_ids=account_ids,
            base_asset=base_asset,
        )

        data_points = []
        for p in pairs:
            # Safely cast numeric strings back to float if appropriate
            xv = p["x_value"]
            if x_data_type == "number" and xv is not None:
                with contextlib.suppress(ValueError):
                    xv = float(xv)

            yv = p["y_value"]
            if y_data_type == "number" and yv is not None:
                with contextlib.suppress(ValueError):
                    yv = float(yv)

            data_points.append(
                MetadataCorrelationDataPoint(
                    date=p["date"],
                    trade_id=p["trade_id"],
                    trade_symbol=p["trade_symbol"],
                    trade_pnl=p["trade_pnl"],
                    x_value=xv,
                    x_label=p["x_label"],
                    y_value=yv,
                    y_label=p["y_label"],
                )
            )

        kpis = MetadataCorrelationKPIs(
            win_rate=agg["win_rate"],
            max_drawdown_pct=agg["max_drawdown_pct"],
            matched_count=len(data_points),
            total_trades_count=agg["total_trades_count"],
        )

        return MetadataCorrelationResponse(
            kpis=kpis,
            data_points=data_points,
            x_axis_data_type=x_data_type,
            y_axis_data_type=y_data_type,
            x_axis_name=x_name,
            y_axis_name=y_name,
        )
