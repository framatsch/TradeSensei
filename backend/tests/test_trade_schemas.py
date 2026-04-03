"""Unit tests for trade Pydantic schemas."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate, TradeRead, TradeUpdate


class TestTradeCreate:
    """Validation tests for :class:`TradeCreate`."""

    @pytest.mark.unit
    def test_valid_payload_accepted(self) -> None:
        """A fully valid payload should deserialise without error."""
        payload = TradeCreate(
            symbol="AAPL",
            direction=Direction.LONG,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            entry_price=Decimal("155.50"),
            opened_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
        )
        assert payload.symbol == "AAPL"
        assert payload.commission == Decimal("0")

    @pytest.mark.unit
    def test_naive_datetime_rejected(self) -> None:
        """A naive (no tzinfo) datetime should raise a ValidationError."""
        with pytest.raises(ValidationError, match="timezone-aware"):
            TradeCreate(
                symbol="AAPL",
                direction=Direction.LONG,
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("10"),
                entry_price=Decimal("150"),
                opened_at=datetime(2025, 1, 15, 10, 0),  # naive!
            )

    @pytest.mark.unit
    def test_symbol_max_length_enforced(self) -> None:
        """Symbol longer than 30 chars should raise a ValidationError."""
        with pytest.raises(ValidationError):
            TradeCreate(
                symbol="A" * 31,
                direction=Direction.LONG,
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("1"),
                entry_price=Decimal("1"),
                opened_at=datetime(2025, 1, 1, tzinfo=UTC),
            )

    @pytest.mark.unit
    def test_zero_quantity_rejected(self) -> None:
        """Quantity must be strictly positive."""
        with pytest.raises(ValidationError):
            TradeCreate(
                symbol="AAPL",
                direction=Direction.LONG,
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("0"),
                entry_price=Decimal("150"),
                opened_at=datetime(2025, 1, 1, tzinfo=UTC),
            )

    @pytest.mark.unit
    def test_negative_commission_rejected(self) -> None:
        """Commission must be >= 0."""
        with pytest.raises(ValidationError):
            TradeCreate(
                symbol="AAPL",
                direction=Direction.LONG,
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("10"),
                entry_price=Decimal("150"),
                opened_at=datetime(2025, 1, 1, tzinfo=UTC),
                commission=Decimal("-1"),
            )


class TestTradeUpdate:
    """Validation tests for :class:`TradeUpdate`."""

    @pytest.mark.unit
    def test_empty_payload_is_valid(self) -> None:
        """An entirely empty update payload should be accepted."""
        update = TradeUpdate()
        assert update.symbol is None
        assert update.direction is None

    @pytest.mark.unit
    def test_partial_update_only_sets_fields(self) -> None:
        """Only explicitly-set fields appear in model_dump(exclude_unset=True)."""
        update = TradeUpdate(symbol="TSLA")
        dumped = update.model_dump(exclude_unset=True)
        assert "symbol" in dumped
        assert "direction" not in dumped

    @pytest.mark.unit
    def test_naive_datetime_rejected(self) -> None:
        """A naive datetime in an update payload should raise a ValidationError."""
        with pytest.raises(ValidationError, match="timezone-aware"):
            TradeUpdate(opened_at=datetime(2025, 3, 1))  # naive


class TestTradeRead:
    """Serialisation tests for :class:`TradeRead`."""

    @pytest.mark.unit
    def test_from_attributes(self) -> None:
        """TradeRead should construct from an ORM-like object via from_attributes."""
        import uuid

        from app.models.trade import Trade

        trade = Trade()
        trade.id = uuid.uuid4()
        trade.symbol = "ES"
        trade.direction = Direction.SHORT
        trade.asset_class = AssetClass.FUTURE
        trade.quantity = Decimal("2")
        trade.entry_price = Decimal("5000")
        trade.exit_price = Decimal("4980")
        trade.stop_loss = None
        trade.take_profit = None
        trade.opened_at = datetime(2025, 6, 1, tzinfo=UTC)
        trade.closed_at = datetime(2025, 6, 2, tzinfo=UTC)
        trade.pnl = Decimal("1000")
        trade.commission = Decimal("4.20")
        trade.multiplier = 100
        trade.notes = "Good trade"
        trade.created_at = datetime(2025, 6, 1, tzinfo=UTC)
        trade.updated_at = datetime(2025, 6, 2, tzinfo=UTC)
        trade.screenshots = []
        trade.is_manually_edited = False
        trade.tags = []
        trade.trade_notes = []

        read = TradeRead.model_validate(trade)
        assert read.symbol == "ES"
        assert read.pnl == Decimal("1000")
