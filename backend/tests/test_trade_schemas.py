"""Unit tests for trade Pydantic schemas."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    EXECUTION_ORIGIN_MANUAL,
)
from app.models.trade import AssetClass, Direction
from app.schemas.execution import (
    LogicalExecutionCreate,
    LogicalExecutionRead,
    LogicalExecutionUpdate,
)
from app.schemas.trade import MergeTradesRequest, TradeCreate, TradeRead, TradeUpdate


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


class TestLogicalExecutionCreate:
    """Validation tests for :class:`LogicalExecutionCreate`."""

    @pytest.mark.unit
    def test_valid_payload_accepted(self) -> None:
        """A fully valid LogicalExecutionCreate payload should deserialise without error."""
        payload = LogicalExecutionCreate(
            direction=Direction.LONG,
            quantity=Decimal("100"),
            price=Decimal("150.50"),
            commission=Decimal("2.25"),
            executed_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
        )
        assert payload.direction == Direction.LONG
        assert payload.quantity == Decimal("100")
        assert payload.commission == Decimal("2.25")

    @pytest.mark.unit
    def test_zero_quantity_rejected(self) -> None:
        """Quantity must be > 0."""
        with pytest.raises(ValidationError):
            LogicalExecutionCreate(
                direction=Direction.SHORT,
                quantity=Decimal("0"),
                price=Decimal("100"),
                executed_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
            )

    @pytest.mark.unit
    def test_negative_price_rejected(self) -> None:
        """Price must be >= 0."""
        with pytest.raises(ValidationError):
            LogicalExecutionCreate(
                direction=Direction.LONG,
                quantity=Decimal("10"),
                price=Decimal("-1"),
                executed_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
            )

    @pytest.mark.unit
    def test_naive_datetime_rejected(self) -> None:
        """A naive datetime should raise a ValidationError."""
        with pytest.raises(ValidationError, match="timezone-aware"):
            LogicalExecutionCreate(
                direction=Direction.LONG,
                quantity=Decimal("10"),
                price=Decimal("150"),
                executed_at=datetime(2025, 1, 15, 10, 0),  # naive!
            )

    @pytest.mark.unit
    def test_commission_defaults_to_zero(self) -> None:
        """Commission should default to 0."""
        payload = LogicalExecutionCreate(
            direction=Direction.LONG,
            quantity=Decimal("50"),
            price=Decimal("200"),
            executed_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
        )
        assert payload.commission == Decimal("0.0")


class TestLogicalExecutionUpdate:
    """Validation tests for :class:`LogicalExecutionUpdate`."""

    @pytest.mark.unit
    def test_empty_payload_is_valid(self) -> None:
        """An entirely empty update payload should be accepted."""
        update = LogicalExecutionUpdate()
        assert update.direction is None
        assert update.quantity is None
        assert update.price is None

    @pytest.mark.unit
    def test_partial_update_only_sets_fields(self) -> None:
        """Only explicitly-set fields appear in model_dump(exclude_unset=True)."""
        update = LogicalExecutionUpdate(price=Decimal("160.00"))
        dumped = update.model_dump(exclude_unset=True)
        assert "price" in dumped
        assert "quantity" not in dumped
        assert "direction" not in dumped

    @pytest.mark.unit
    def test_zero_quantity_rejected(self) -> None:
        """Quantity must be > 0 when provided."""
        with pytest.raises(ValidationError):
            LogicalExecutionUpdate(quantity=Decimal("0"))

    @pytest.mark.unit
    def test_negative_price_rejected(self) -> None:
        """Price must be >= 0 when provided."""
        with pytest.raises(ValidationError):
            LogicalExecutionUpdate(price=Decimal("-10"))


class TestLogicalExecutionRead:
    """Serialisation tests for :class:`LogicalExecutionRead`."""

    @pytest.mark.unit
    def test_from_attributes(self) -> None:
        """LogicalExecutionRead should construct from an ORM instance via from_attributes."""
        import uuid

        from app.models.logical_execution import LogicalExecution

        exec_id = uuid.uuid4()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()
        trade_id = uuid.uuid4()

        execution = LogicalExecution()
        execution.id = exec_id  # type: ignore[assignment]
        execution.user_id = user_id  # type: ignore[assignment]
        execution.account_id = account_id  # type: ignore[assignment]
        execution.trade_id = trade_id  # type: ignore[assignment]
        execution.symbol = "AAPL"  # type: ignore[assignment]
        execution.direction = Direction.LONG  # type: ignore[assignment]
        execution.asset_class = AssetClass.EQUITY  # type: ignore[assignment]
        execution.quantity = Decimal("100")  # type: ignore[assignment]
        execution.price = Decimal("150.50")  # type: ignore[assignment]
        execution.commission = Decimal("2.50")  # type: ignore[assignment]
        execution.executed_at = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)  # type: ignore[assignment]
        execution.origin = EXECUTION_ORIGIN_MANUAL  # type: ignore[assignment]
        execution.deleted = False  # type: ignore[assignment]
        execution.user_modified = False  # type: ignore[assignment]
        execution.parent_id = None  # type: ignore[assignment]
        execution.multiplier = 1  # type: ignore[assignment]
        execution.currency = "USD"  # type: ignore[assignment]
        execution.created_at = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)  # type: ignore[assignment]
        execution.updated_at = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)  # type: ignore[assignment]

        read = LogicalExecutionRead.model_validate(execution)
        assert read.id == exec_id
        assert read.symbol == "AAPL"
        assert read.quantity == Decimal("100")
        assert read.origin == EXECUTION_ORIGIN_MANUAL


class TestMergeTradesRequest:
    """Validation tests for :class:`MergeTradesRequest`."""

    @pytest.mark.unit
    def test_valid_payload_two_trades(self) -> None:
        """A valid payload with 2 trades should deserialise without error."""
        trade_ids = [uuid.uuid4(), uuid.uuid4()]
        payload = MergeTradesRequest(trade_ids=trade_ids)
        assert len(payload.trade_ids) == 2
        assert payload.trade_ids == trade_ids

    @pytest.mark.unit
    def test_valid_payload_max_trades(self) -> None:
        """A valid payload with 10 trades should be accepted."""
        trade_ids = [uuid.uuid4() for _ in range(10)]
        payload = MergeTradesRequest(trade_ids=trade_ids)
        assert len(payload.trade_ids) == 10

    @pytest.mark.unit
    def test_less_than_two_trades_rejected(self) -> None:
        """A payload with < 2 trades should raise a ValidationError."""
        with pytest.raises(ValidationError, match="at least 2"):
            MergeTradesRequest(trade_ids=[uuid.uuid4()])

    @pytest.mark.unit
    def test_more_than_ten_trades_rejected(self) -> None:
        """A payload with > 10 trades should raise a ValidationError."""
        trade_ids = [uuid.uuid4() for _ in range(11)]
        with pytest.raises(ValidationError, match="at most 10"):
            MergeTradesRequest(trade_ids=trade_ids)

    @pytest.mark.unit
    def test_empty_list_rejected(self) -> None:
        """An empty trade_ids list should raise a ValidationError."""
        with pytest.raises(ValidationError):
            MergeTradesRequest(trade_ids=[])


class TestLogicalExecutionReadFieldCompleteness:
    """Verify that LogicalExecutionRead includes all required fields with correct types."""

    @pytest.mark.unit
    def test_all_fields_present_in_schema(self) -> None:
        """LogicalExecutionRead must include all 19 fields with correct types.

        Required fields:
        - id: UUID
        - user_id: UUID
        - account_id: UUID | None
        - symbol: str
        - conid: str | None
        - asset_class: AssetClass
        - direction: Direction
        - quantity: Decimal
        - price: Decimal
        - commission: Decimal
        - executed_at: datetime
        - pnl: Decimal | None
        - pnl_eur: Decimal | None
        - multiplier: int
        - currency: str | None
        - origin: str (imported | manual | merged | split)
        - deleted: bool
        - user_modified: bool
        - parent_id: UUID | None
        - trade_id: UUID | None
        - created_at: datetime
        - updated_at: datetime
        """
        from app.models.logical_execution import LogicalExecution

        exec_id = uuid.uuid4()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        now = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)

        execution = LogicalExecution()
        execution.id = exec_id  # type: ignore[assignment]
        execution.user_id = user_id  # type: ignore[assignment]
        execution.account_id = account_id  # type: ignore[assignment]
        execution.trade_id = trade_id  # type: ignore[assignment]
        execution.symbol = "AAPL"  # type: ignore[assignment]
        execution.conid = "123456789"  # type: ignore[assignment]
        execution.direction = Direction.LONG  # type: ignore[assignment]
        execution.asset_class = AssetClass.EQUITY  # type: ignore[assignment]
        execution.quantity = Decimal("100")  # type: ignore[assignment]
        execution.price = Decimal("150.50")  # type: ignore[assignment]
        execution.commission = Decimal("2.50")  # type: ignore[assignment]
        execution.executed_at = now  # type: ignore[assignment]
        execution.pnl = Decimal("500.00")  # type: ignore[assignment]
        execution.pnl_eur = Decimal("450.00")  # type: ignore[assignment]
        execution.multiplier = 1  # type: ignore[assignment]
        execution.currency = "USD"  # type: ignore[assignment]
        execution.origin = EXECUTION_ORIGIN_MANUAL  # type: ignore[assignment]
        execution.deleted = False  # type: ignore[assignment]
        execution.user_modified = False  # type: ignore[assignment]
        execution.parent_id = None  # type: ignore[assignment]
        execution.created_at = now  # type: ignore[assignment]
        execution.updated_at = now  # type: ignore[assignment]

        read = LogicalExecutionRead.model_validate(execution)

        # Verify all fields are present and have correct types
        assert isinstance(read.id, uuid.UUID)
        assert read.id == exec_id
        assert isinstance(read.user_id, uuid.UUID)
        assert read.user_id == user_id
        assert isinstance(read.account_id, uuid.UUID)
        assert read.account_id == account_id
        assert isinstance(read.symbol, str)
        assert read.symbol == "AAPL"
        assert isinstance(read.conid, str)
        assert read.conid == "123456789"
        assert read.asset_class == AssetClass.EQUITY
        assert read.direction == Direction.LONG
        assert isinstance(read.quantity, Decimal)
        assert read.quantity == Decimal("100")
        assert isinstance(read.price, Decimal)
        assert read.price == Decimal("150.50")
        assert isinstance(read.commission, Decimal)
        assert read.commission == Decimal("2.50")
        assert isinstance(read.executed_at, datetime)
        assert read.executed_at == now
        assert isinstance(read.pnl, Decimal)
        assert read.pnl == Decimal("500.00")
        assert isinstance(read.pnl_eur, Decimal)
        assert read.pnl_eur == Decimal("450.00")
        assert isinstance(read.multiplier, int)
        assert read.multiplier == 1
        assert isinstance(read.currency, str)
        assert read.currency == "USD"
        assert read.origin == EXECUTION_ORIGIN_MANUAL
        assert read.deleted is False
        assert read.user_modified is False
        assert read.parent_id is None
        assert isinstance(read.trade_id, uuid.UUID)
        assert read.trade_id == trade_id
        assert isinstance(read.created_at, datetime)
        assert read.created_at == now
        assert isinstance(read.updated_at, datetime)
        assert read.updated_at == now

    @pytest.mark.unit
    def test_optional_fields_can_be_none(self) -> None:
        """Optional fields (account_id, conid, pnl, pnl_eur, currency, trade_id) can be None."""
        from app.models.logical_execution import LogicalExecution

        exec_id = uuid.uuid4()
        user_id = uuid.uuid4()
        now = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)

        execution = LogicalExecution()
        execution.id = exec_id  # type: ignore[assignment]
        execution.user_id = user_id  # type: ignore[assignment]
        execution.account_id = None  # type: ignore[assignment]
        execution.trade_id = None  # type: ignore[assignment]
        execution.symbol = "AAPL"  # type: ignore[assignment]
        execution.conid = None  # type: ignore[assignment]
        execution.direction = Direction.SHORT  # type: ignore[assignment]
        execution.asset_class = AssetClass.EQUITY  # type: ignore[assignment]
        execution.quantity = Decimal("50")  # type: ignore[assignment]
        execution.price = Decimal("100.00")  # type: ignore[assignment]
        execution.commission = Decimal("0")  # type: ignore[assignment]
        execution.executed_at = now  # type: ignore[assignment]
        execution.pnl = None  # type: ignore[assignment]
        execution.pnl_eur = None  # type: ignore[assignment]
        execution.multiplier = 1  # type: ignore[assignment]
        execution.currency = None  # type: ignore[assignment]
        execution.origin = EXECUTION_ORIGIN_IMPORTED  # type: ignore[assignment]
        execution.deleted = False  # type: ignore[assignment]
        execution.user_modified = False  # type: ignore[assignment]
        execution.parent_id = None  # type: ignore[assignment]
        execution.created_at = now  # type: ignore[assignment]
        execution.updated_at = now  # type: ignore[assignment]

        read = LogicalExecutionRead.model_validate(execution)

        # Verify optional fields can be None
        assert read.account_id is None
        assert read.conid is None
        assert read.pnl is None
        assert read.pnl_eur is None
        assert read.currency is None
        assert read.trade_id is None
