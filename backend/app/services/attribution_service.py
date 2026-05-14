"""Service layer for market-phase attribution analytics."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Spec5NotDeployedError
from app.repositories.attribution_repository import AttributionRepository
from app.schemas.analytics import (
    AttributionResponse,
    DashboardFilterConfig,
    MarketPhaseCorrelation,
)
from app.services.cache_service import CacheService


class AttributionService:
    """Business logic and enrichment for attribution response payloads."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AttributionRepository()
        self._cache = CacheService()

    async def get_market_phase_correlation(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        filter_config: DashboardFilterConfig,
    ) -> AttributionResponse:
        """Return market-phase attribution response for one portfolio."""
        filter_payload = filter_config.model_dump(by_alias=True)
        cache_key = CacheService.attribution_key(
            portfolio_id=portfolio_id,
            user_id=user_id,
            filter_config=filter_payload,
        )
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return AttributionResponse.model_validate_json(cached)

        try:
            rows = await self._repo.compute_market_phase_correlation(
                portfolio_id=portfolio_id,
                user_id=user_id,
                filter_config=filter_config,
                session=self._session,
            )
            (
                unmatched_count,
                phase_unset_count,
            ) = await self._repo.compute_unmatched_counts(
                portfolio_id=portfolio_id,
                user_id=user_id,
                filter_config=filter_config,
                session=self._session,
            )
        except Spec5NotDeployedError as exc:
            # Re-raise the exception to be handled by the route or middleware
            raise exc

        buckets: list[MarketPhaseCorrelation] = []
        currencies = set()
        for row in rows:
            phase = row["market_phase"]
            label = phase
            color_hex = None
            losing = row["losing_trades"]
            trade_count = row["trade_count"]
            win_rate = Decimal(row["winning_trades"]) / Decimal(trade_count) if trade_count > 0 else Decimal("0")
            profit_factor = None
            if row["gross_loss"] < 0:
                profit_factor = row["gross_profit"] / abs(row["gross_loss"])

            currency = row["currency"] or "UNK"
            currencies.add(currency)
            _ = losing
            buckets.append(
                MarketPhaseCorrelation(
                    market_phase=phase,
                    label=label,
                    color_hex=color_hex,
                    trade_count=trade_count,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    avg_pnl=row["avg_pnl"],
                    total_pnl=row["total_pnl"],
                    currency=currency,
                )
            )

        result = AttributionResponse(
            buckets=buckets,
            unmatched_trade_count=unmatched_count,
            phase_unset_trade_count=phase_unset_count,
            currency=(next(iter(currencies)) if len(currencies) == 1 else None),
        )
        await self._cache.set(cache_key, result.model_dump_json(), ttl=900)
        return result

    async def invalidate_user_cache(self, user_id: uuid.UUID) -> None:
        """Invalidate all attribution-related cache for a user."""
        await self._cache.invalidate_user(user_id)
