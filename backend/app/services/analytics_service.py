"""Service layer for analytics summary computation."""

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EQUITY_CURVE_MAX_POINTS, FX_ECB_FALLBACK_DAYS
from app.core.exceptions import (
    PlaybookNotFoundError,
    SavedDashboardViewNotFoundError,
    TaxonomyNotFoundError,
)
from app.models.saved_dashboard_view import SavedDashboardView
from app.repositories.analytics_repository import AnalyticsRepository, EquityRow
from app.repositories.fx_rate_repository import FxRateRepository
from app.repositories.playbook_repository import PlaybookRepository
from app.repositories.saved_dashboard_view_repository import (
    SavedDashboardViewRepository,
)
from app.repositories.taxonomy_repository import TaxonomyRepository
from app.schemas.analytics import (
    AnalyticsSummary,
    AnalyticsSummaryRequest,
    DashboardFilterConfig,
    DrawdownPoint,
    EquityCurvePoint,
    PerCurrencySummary,
)
from app.services.cache_service import CacheService

_ZERO = Decimal("0")


@dataclass(slots=True)
class _ComputedMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    gross_profit: Decimal
    gross_loss: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    expectancy: Decimal
    win_rate: Decimal
    profit_factor: Decimal | None
    sharpe_ratio: Decimal | None
    max_consecutive_wins: int
    max_consecutive_losses: int


class AnalyticsService:
    """Business rules and response assembly for analytics summary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AnalyticsRepository()
        self._views = SavedDashboardViewRepository(session)
        self._playbooks = PlaybookRepository(session)
        self._taxonomies = TaxonomyRepository(session)
        self._fx = FxRateRepository()
        self._cache = CacheService()

    async def _get_owned_view(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        view_id: uuid.UUID,
    ) -> SavedDashboardView:
        view = await self._views.get_by_id(view_id)
        if view is None or view.user_id != user_id or view.portfolio_id != portfolio_id:
            raise SavedDashboardViewNotFoundError("view not found")
        return view

    async def _resolve_filter_config(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        request: AnalyticsSummaryRequest,
    ) -> DashboardFilterConfig:
        if request.filter_config is not None:
            cfg = request.filter_config
        else:
            if request.view_id is None:
                raise ValueError("view_id must be provided if filter_config is null")
            view = await self._get_owned_view(
                portfolio_id=portfolio_id,
                user_id=user_id,
                view_id=request.view_id,
            )
            cfg = DashboardFilterConfig.model_validate(view.filter_config)

        if cfg.playbook_ids:
            missing: list[str] = []
            for playbook_id in cfg.playbook_ids:
                playbook = await self._playbooks.get_by_id(playbook_id, user_id)
                if playbook is None:
                    missing.append(str(playbook_id))
            if missing:
                raise PlaybookNotFoundError(f"invalid_playbook_ids: {missing}")

        if cfg.taxonomy_ids:
            taxonomies = await self._taxonomies.get_many_by_ids(cfg.taxonomy_ids, user_id)
            found = {item.id for item in taxonomies}
            missing = [str(taxonomy_id) for taxonomy_id in cfg.taxonomy_ids if taxonomy_id not in found]
            if missing:
                raise TaxonomyNotFoundError(f"invalid_taxonomy_ids: {missing}")

        return cfg

    @staticmethod
    def _compute_streaks(rows: list[EquityRow]) -> tuple[int, int]:
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        for row in rows:
            pnl = row["pnl"]
            if pnl > 0:
                current_wins += 1
                current_losses = 0
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
            else:
                current_losses = 0
                current_wins = 0
            max_wins = max(max_wins, current_wins)
            max_losses = max(max_losses, current_losses)
        return max_wins, max_losses

    @staticmethod
    def _compute_sharpe(rows: list[EquityRow]) -> Decimal | None:
        if len(rows) < 2:
            return None
        daily: dict[date, Decimal] = defaultdict(lambda: _ZERO)
        for row in rows:
            daily[row["closed_date"]] += row["pnl"]
        values = [float(value) for value in daily.values()]
        if len(values) < 2:
            return None
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        if variance <= 0:
            return None
        std_dev = math.sqrt(variance)
        if std_dev == 0:
            return None
        sharpe = (mean / std_dev) * math.sqrt(252)
        return Decimal(str(round(sharpe, 8)))

    def _compute_metrics(self, rows: list[EquityRow]) -> _ComputedMetrics:
        total = len(rows)
        wins = sum(1 for row in rows if row["pnl"] > 0)
        losses = sum(1 for row in rows if row["pnl"] < 0)
        gross_profit = sum((row["pnl"] for row in rows if row["pnl"] > 0), _ZERO)
        gross_loss = sum((row["pnl"] for row in rows if row["pnl"] < 0), _ZERO)
        avg_win = gross_profit / wins if wins > 0 else _ZERO
        avg_loss = gross_loss / losses if losses > 0 else _ZERO
        win_rate = (Decimal(wins) / Decimal(total)) if total > 0 else _ZERO
        loss_rate = (Decimal(losses) / Decimal(total)) if total > 0 else _ZERO
        expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)
        profit_factor = None
        if gross_loss < 0:
            profit_factor = gross_profit / abs(gross_loss)
        max_wins, max_losses = self._compute_streaks(rows)
        return _ComputedMetrics(
            total_trades=total,
            winning_trades=wins,
            losing_trades=losses,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=self._compute_sharpe(rows),
            max_consecutive_wins=max_wins,
            max_consecutive_losses=max_losses,
        )

    @staticmethod
    def _build_curves(
        rows: list[EquityRow],
        *,
        currency: str,
    ) -> tuple[list[EquityCurvePoint], list[DrawdownPoint], Decimal, Decimal]:
        equity = _ZERO
        peak = _ZERO
        max_drawdown = _ZERO
        max_drawdown_abs = _ZERO
        equity_curve: list[EquityCurvePoint] = []
        drawdown_curve: list[DrawdownPoint] = []

        for row in rows:
            equity += row["pnl"]
            if equity > peak:
                peak = equity

            drawdown_abs = equity - peak
            drawdown_pct = _ZERO if peak == 0 else drawdown_abs / peak

            if drawdown_pct < max_drawdown:
                max_drawdown = drawdown_pct
            if drawdown_abs < max_drawdown_abs:
                max_drawdown_abs = drawdown_abs

            equity_curve.append(
                EquityCurvePoint(
                    date=row["closed_date"],
                    equity=equity,
                    currency=currency,
                )
            )
            drawdown_curve.append(
                DrawdownPoint(
                    date=row["closed_date"],
                    drawdown_pct=drawdown_pct,
                    drawdown_abs=drawdown_abs,
                )
            )

        return equity_curve, drawdown_curve, max_drawdown, max_drawdown_abs

    @staticmethod
    def _downsample_rows(rows: list[EquityRow]) -> list[EquityRow]:
        if len(rows) <= EQUITY_CURVE_MAX_POINTS:
            return rows
        max_points = EQUITY_CURVE_MAX_POINTS
        step = len(rows) / max_points
        sampled: list[EquityRow] = []
        for idx in range(max_points):
            sampled.append(rows[int(idx * step)])
        return sampled

    async def _normalize_rows(
        self,
        *,
        rows: list[EquityRow],
        normalize_to: str,
    ) -> tuple[list[EquityRow], list[uuid.UUID]]:
        normalized: list[EquityRow] = []
        missing_ids: list[uuid.UUID] = []
        for row in rows:
            source = row["currency"]
            if source is None:
                missing_ids.append(row["trade_id"])
                continue
            if source == normalize_to:
                normalized.append(
                    EquityRow(
                        trade_id=row["trade_id"],
                        closed_date=row["closed_date"],
                        pnl=row["pnl"],
                        currency=normalize_to,
                    )
                )
                continue

            rate = await self._fx.get_by_date(
                self._session,
                row["closed_date"],
                source,
                normalize_to,
            )
            if rate is None:
                rate = await self._fx.get_nearest_within_window(
                    self._session,
                    row["closed_date"],
                    source,
                    normalize_to,
                    FX_ECB_FALLBACK_DAYS,
                )

            if rate is None:
                missing_ids.append(row["trade_id"])
                continue

            normalized.append(
                EquityRow(
                    trade_id=row["trade_id"],
                    closed_date=row["closed_date"],
                    pnl=(row["pnl"] * rate),
                    currency=normalize_to,
                )
            )

        return normalized, missing_ids

    async def get_summary(
        self,
        *,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        request: AnalyticsSummaryRequest,
    ) -> AnalyticsSummary:
        """Return analytics summary from inline filter config or saved view."""
        filter_config = await self._resolve_filter_config(
            portfolio_id=portfolio_id,
            user_id=user_id,
            request=request,
        )

        filter_payload = filter_config.model_dump(by_alias=True)
        cache_key = CacheService.analytics_key(
            portfolio_id=portfolio_id,
            user_id=user_id,
            filter_config=filter_payload,
        )
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return AnalyticsSummary.model_validate_json(cached)

        raw = await self._repo.compute_summary(
            portfolio_id=portfolio_id,
            user_id=user_id,
            filter_config=filter_config,
            session=self._session,
        )
        source_rows = raw["equity_rows"]
        avg_trade_duration = raw["avg_trade_duration_hours"]

        if filter_config.currency_mode == "NORMALIZED":
            if filter_config.normalize_to is None:
                raise ValueError("normalize_to is required when currency_mode is NORMALIZED")
            normalized_rows, missing_ids = await self._normalize_rows(
                rows=source_rows,
                normalize_to=filter_config.normalize_to,
            )
            sampled = self._downsample_rows(normalized_rows)
            metrics = self._compute_metrics(normalized_rows)
            equity_curve, drawdown_curve, max_dd, max_dd_abs = self._build_curves(
                sampled,
                currency=filter_config.normalize_to,
            )
            result = AnalyticsSummary(
                win_rate=metrics.win_rate,
                profit_factor=metrics.profit_factor,
                expectancy=metrics.expectancy,
                sharpe_ratio=metrics.sharpe_ratio,
                total_trades=metrics.total_trades,
                winning_trades=metrics.winning_trades,
                losing_trades=metrics.losing_trades,
                gross_profit=metrics.gross_profit,
                gross_loss=metrics.gross_loss,
                avg_win=metrics.avg_win,
                avg_loss=metrics.avg_loss,
                max_consecutive_wins=metrics.max_consecutive_wins,
                max_consecutive_losses=metrics.max_consecutive_losses,
                avg_trade_duration_hours=avg_trade_duration,
                equity_curve=equity_curve,
                drawdown_curve=drawdown_curve,
                max_drawdown=max_dd,
                max_drawdown_abs=max_dd_abs,
                currency=filter_config.normalize_to,
                multi_currency_warning=False,
                currencies=None,
                fx_rate_missing_trade_ids=missing_ids or None,
            )
        else:
            currencies = sorted({row["currency"] or "UNK" for row in source_rows})
            if len(currencies) <= 1:
                summary_currency = currencies[0] if currencies else "UNK"
                sampled = self._downsample_rows(source_rows)
                metrics = self._compute_metrics(source_rows)
                equity_curve, drawdown_curve, max_dd, max_dd_abs = self._build_curves(
                    sampled,
                    currency=summary_currency,
                )
                result = AnalyticsSummary(
                    win_rate=metrics.win_rate,
                    profit_factor=metrics.profit_factor,
                    expectancy=metrics.expectancy,
                    sharpe_ratio=metrics.sharpe_ratio,
                    total_trades=metrics.total_trades,
                    winning_trades=metrics.winning_trades,
                    losing_trades=metrics.losing_trades,
                    gross_profit=metrics.gross_profit,
                    gross_loss=metrics.gross_loss,
                    avg_win=metrics.avg_win,
                    avg_loss=metrics.avg_loss,
                    max_consecutive_wins=metrics.max_consecutive_wins,
                    max_consecutive_losses=metrics.max_consecutive_losses,
                    avg_trade_duration_hours=avg_trade_duration,
                    equity_curve=equity_curve,
                    drawdown_curve=drawdown_curve,
                    max_drawdown=max_dd,
                    max_drawdown_abs=max_dd_abs,
                    currency=summary_currency,
                    multi_currency_warning=False,
                    currencies=[
                        PerCurrencySummary(
                            currency=summary_currency,
                            total_trades=metrics.total_trades,
                            winning_trades=metrics.winning_trades,
                            losing_trades=metrics.losing_trades,
                            gross_profit=metrics.gross_profit,
                            gross_loss=metrics.gross_loss,
                            avg_win=metrics.avg_win,
                            avg_loss=metrics.avg_loss,
                            expectancy=metrics.expectancy,
                        )
                    ],
                    fx_rate_missing_trade_ids=None,
                )
            else:
                global_metrics = self._compute_metrics(source_rows)
                per_currency: list[PerCurrencySummary] = []
                for currency in currencies:
                    subset = [row for row in source_rows if (row["currency"] or "UNK") == currency]
                    metrics = self._compute_metrics(subset)
                    per_currency.append(
                        PerCurrencySummary(
                            currency=currency,
                            total_trades=metrics.total_trades,
                            winning_trades=metrics.winning_trades,
                            losing_trades=metrics.losing_trades,
                            gross_profit=metrics.gross_profit,
                            gross_loss=metrics.gross_loss,
                            avg_win=metrics.avg_win,
                            avg_loss=metrics.avg_loss,
                            expectancy=metrics.expectancy,
                        )
                    )

                result = AnalyticsSummary(
                    win_rate=global_metrics.win_rate,
                    profit_factor=global_metrics.profit_factor,
                    expectancy=None,
                    sharpe_ratio=None,
                    total_trades=global_metrics.total_trades,
                    winning_trades=global_metrics.winning_trades,
                    losing_trades=global_metrics.losing_trades,
                    gross_profit=None,
                    gross_loss=None,
                    avg_win=None,
                    avg_loss=None,
                    max_consecutive_wins=global_metrics.max_consecutive_wins,
                    max_consecutive_losses=global_metrics.max_consecutive_losses,
                    avg_trade_duration_hours=avg_trade_duration,
                    equity_curve=[],
                    drawdown_curve=[],
                    max_drawdown=_ZERO,
                    max_drawdown_abs=_ZERO,
                    currency=None,
                    multi_currency_warning=True,
                    currencies=per_currency,
                    fx_rate_missing_trade_ids=None,
                )

        await self._cache.set(cache_key, result.model_dump_json(), ttl=300)
        return result
