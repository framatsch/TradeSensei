"""Unit tests for MetricsService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.models.trade import AssetClass, Direction, Trade
from app.schemas.metrics import MetricsSummary
from app.services.metrics_service import MetricsService

# ─── Helpers ──────────────────────────────────────────────────────────────────

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
_PORTFOLIO_ID = uuid.uuid4()


def _make_trade_orm(
    pnl: Decimal | None = None,
    closed_at: datetime | None = None,
    opened_at: datetime | None = None,
) -> Trade:
    """Build a minimal :class:`Trade` ORM instance for testing.

    Args:
        pnl: Realised PnL. ``None`` means open trade.
        closed_at: Close timestamp. Defaults to ``_NOW`` when pnl is set.
        opened_at: Open timestamp. Defaults to ``_NOW - 1 hour``.

    Returns:
        A :class:`Trade` instance with all required fields set.
    """
    if opened_at is None:
        opened_at = _NOW - timedelta(hours=1)
    if closed_at is None and pnl is not None:
        closed_at = _NOW
    trade = Trade()
    trade.id = uuid.uuid4()  # type: ignore[assignment]
    trade.symbol = "AAPL"  # type: ignore[assignment]
    trade.direction = Direction.LONG  # type: ignore[assignment]
    trade.asset_class = AssetClass.EQUITY  # type: ignore[assignment]
    trade.quantity = Decimal("10")  # type: ignore[assignment]
    trade.entry_price = Decimal("100")  # type: ignore[assignment]
    trade.exit_price = Decimal("110") if pnl is not None else None  # type: ignore[assignment]
    trade.stop_loss = None  # type: ignore[assignment]
    trade.take_profit = None  # type: ignore[assignment]
    trade.opened_at = opened_at  # type: ignore[assignment]
    trade.closed_at = closed_at  # type: ignore[assignment]
    trade.pnl = pnl  # type: ignore[assignment]
    trade.commission = Decimal("0")  # type: ignore[assignment]
    trade.multiplier = 1  # type: ignore[assignment]
    trade.notes = None  # type: ignore[assignment]
    trade.created_at = opened_at  # type: ignore[assignment]
    trade.updated_at = opened_at  # type: ignore[assignment]
    trade.image_urls = []  # type: ignore[assignment]
    trade.is_manually_edited = False  # type: ignore[assignment]
    trade.tags = []  # type: ignore[assignment]
    trade.trade_notes = []  # type: ignore[assignment]
    return trade


@pytest.fixture()
def service(mock_session: AsyncMock) -> MetricsService:
    """Return a :class:`MetricsService` wired to a mock session."""
    return MetricsService(mock_session)


# ─── get_summary ──────────────────────────────────────────────────────────────


class TestGetSummary:
    """Unit tests for :meth:`MetricsService.get_summary`."""

    @pytest.mark.unit
    async def test_returns_metrics_summary_for_trades(
        self, service: MetricsService
    ) -> None:
        """get_summary should return a MetricsSummary when trades exist."""
        trades = [
            _make_trade_orm(pnl=Decimal("100")),
            _make_trade_orm(pnl=Decimal("-50")),
            _make_trade_orm(pnl=Decimal("200")),
        ]
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=trades,
        ):
            result = await service.get_summary(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert isinstance(result, MetricsSummary)
        assert result.metrics.total_trades == 3
        assert result.metrics.winning_trades == 2
        assert result.metrics.losing_trades == 1

    @pytest.mark.unit
    async def test_returns_empty_summary_when_no_trades(
        self, service: MetricsService
    ) -> None:
        """get_summary should return a zero-value MetricsSummary for no trades."""
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_summary(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result.metrics.total_trades == 0
        assert result.metrics.win_rate == Decimal("0")
        assert result.max_drawdown == Decimal("0")
        assert result.equity_curve == []
        assert result.drawdown_curve == []

    @pytest.mark.unit
    async def test_equity_curve_uses_starting_capital(
        self, service: MetricsService
    ) -> None:
        """Equity curve should start from starting_capital, not zero."""
        trades = [_make_trade_orm(pnl=Decimal("500"))]
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=trades,
        ):
            result = await service.get_summary(
                user_id=uuid.uuid4(),
                portfolio_id=_PORTFOLIO_ID,
                starting_capital=Decimal("10000"),
            )

        assert result.equity_curve[0].equity == Decimal("10500")

    @pytest.mark.unit
    async def test_equity_curve_capped_at_max_points(
        self, service: MetricsService
    ) -> None:
        """Equity curve must be capped at EQUITY_CURVE_MAX_POINTS entries."""
        from app.core.constants import EQUITY_CURVE_MAX_POINTS

        # Create more trades than the cap.
        n = EQUITY_CURVE_MAX_POINTS + 50
        base_dt = _NOW - timedelta(hours=n)
        trades = [
            _make_trade_orm(
                pnl=Decimal("1"),
                opened_at=base_dt + timedelta(hours=i),
                closed_at=base_dt + timedelta(hours=i, minutes=30),
            )
            for i in range(n)
        ]
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=trades,
        ):
            result = await service.get_summary(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result.equity_curve) == EQUITY_CURVE_MAX_POINTS
        assert len(result.drawdown_curve) == EQUITY_CURVE_MAX_POINTS

    @pytest.mark.unit
    async def test_passes_filters_to_repository(self, service: MetricsService) -> None:
        """get_summary should forward account_id, from_dt, and to_dt to the repo."""
        from_dt = _NOW - timedelta(days=30)
        to_dt = _NOW
        account_id = uuid.uuid4()

        mock_repo_method = AsyncMock(return_value=[])
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new=mock_repo_method,
        ):
            await service.get_summary(
                user_id=uuid.uuid4(),
                portfolio_id=_PORTFOLIO_ID,
                account_id=account_id,
                from_dt=from_dt,
                to_dt=to_dt,
            )

        mock_repo_method.assert_awaited_once()
        call_kwargs = mock_repo_method.call_args.kwargs
        assert call_kwargs["account_id"] == account_id
        assert call_kwargs["from_dt"] == from_dt
        assert call_kwargs["to_dt"] == to_dt


# ─── get_equity_curve ─────────────────────────────────────────────────────────


class TestGetEquityCurve:
    """Unit tests for :meth:`MetricsService.get_equity_curve`."""

    @pytest.mark.unit
    async def test_returns_equity_curve_points(self, service: MetricsService) -> None:
        """get_equity_curve should return ordered EquityCurvePoints."""
        from app.schemas.metrics import EquityCurvePoint

        trades = [
            _make_trade_orm(pnl=Decimal("100")),
            _make_trade_orm(
                pnl=Decimal("50"),
                closed_at=_NOW + timedelta(hours=1),
            ),
        ]
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=trades,
        ):
            result = await service.get_equity_curve(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result) == 2
        assert all(isinstance(p, EquityCurvePoint) for p in result)

    @pytest.mark.unit
    async def test_returns_empty_list_for_no_trades(
        self, service: MetricsService
    ) -> None:
        """get_equity_curve should return an empty list when no trades exist."""
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_equity_curve(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result == []


# ─── get_drawdown_curve ───────────────────────────────────────────────────────


class TestGetDrawdownCurve:
    """Unit tests for :meth:`MetricsService.get_drawdown_curve`."""

    @pytest.mark.unit
    async def test_returns_drawdown_points(self, service: MetricsService) -> None:
        """get_drawdown_curve should return DrawdownPoint instances."""
        from app.schemas.metrics import DrawdownPoint

        trades = [
            _make_trade_orm(pnl=Decimal("100")),
            _make_trade_orm(pnl=Decimal("-30"), closed_at=_NOW + timedelta(hours=1)),
        ]
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=trades,
        ):
            result = await service.get_drawdown_curve(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert len(result) == 2
        assert all(isinstance(p, DrawdownPoint) for p in result)

    @pytest.mark.unit
    async def test_returns_empty_list_for_no_trades(
        self, service: MetricsService
    ) -> None:
        """get_drawdown_curve should return an empty list when no trades exist."""
        with patch(
            "app.services.metrics_service.MetricsRepository.get_closed_trades_for_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_drawdown_curve(
                user_id=uuid.uuid4(), portfolio_id=_PORTFOLIO_ID
            )

        assert result == []
