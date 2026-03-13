"""Unit tests for broker file parsers and ImportService.

All tests are pure unit tests — no database access (mocked).
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountNotFoundError, ImportParseError
from app.models.trade import AssetClass, Direction
from app.schemas.imports import ImportResult
from app.schemas.trade import TradeCreate
from app.services.import_service import ImportService
from app.utils.parsers.factory import BrokerType, get_parser
from app.utils.parsers.ibkr import IBKRParser, _map_asset_class, _parse_ibkr_datetime
from app.utils.parsers.schwab import SchwabParser, _parse_decimal, _parse_schwab_date

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_ibkr_csv(rows: list[str]) -> bytes:
    """Build a minimal IBKR Activity Statement CSV with a Trades section.

    Args:
        rows: Data row lines to append after the header.

    Returns:
        UTF-8 encoded CSV bytes.
    """
    header = (
        "Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,"
        "Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,"
        "Realized P&L,MTM P&L,Code\n"
    )
    content = header + "\n".join(rows)
    return content.encode("utf-8")


def _ibkr_row(
    symbol: str = "AAPL",
    asset: str = "Stocks",
    currency: str = "USD",
    dt: str = "2024-03-15, 09:30:00",
    quantity: str = "100",
    price: str = "150.00",
    comm: str = "-1.50",
    pnl: str = "0",
) -> str:
    """Build a single IBKR Trades data row string.

    The ``Date/Time`` field contains a comma (``"YYYY-MM-DD, HH:MM:SS"``),
    so it is double-quoted to prevent CSV splitting.

    Args:
        symbol: Ticker symbol.
        asset: Asset category string.
        currency: Currency code.
        dt: Date/time string in IBKR format (comma embedded).
        quantity: Position quantity (negative for short).
        price: Trade price.
        comm: Commission/fee (negative in IBKR exports).
        pnl: Realized P&L.

    Returns:
        A comma-separated row string with the datetime field quoted.
    """
    return (
        f"Trades,Data,Order,{asset},{currency},{symbol},"
        f'"{dt}",{quantity},{price},151.00,-15000.00,{comm},15001.50,{pnl},0.00,'
    )


def _make_schwab_csv(rows: list[str]) -> bytes:
    """Build a minimal Schwab trade history CSV.

    Args:
        rows: Data row lines to append after the header.

    Returns:
        UTF-8 encoded CSV bytes.
    """
    header = "Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount\n"
    content = header + "\n".join(rows)
    return content.encode("utf-8")


def _schwab_row(
    date: str = "03/15/2024",
    action: str = "Buy",
    symbol: str = "AAPL",
    quantity: str = "10",
    price: str = "$150.25",
    fees: str = "$1.50",
) -> str:
    """Build a single Schwab trade history data row string.

    Args:
        date: Date in MM/DD/YYYY format.
        action: Action type (Buy or Sell).
        symbol: Ticker symbol.
        quantity: Trade quantity.
        price: Trade price (dollar-prefixed).
        fees: Fees and commissions (dollar-prefixed).

    Returns:
        A comma-separated row string.
    """
    return f"{date},{action},{symbol},Description,{quantity},{price},{fees},-1500.00"


# ─── IBKRParser unit tests ────────────────────────────────────────────────────


class TestMapAssetClass:
    """Unit tests for the IBKR asset-class mapping helper."""

    @pytest.mark.unit
    def test_stocks_maps_to_equity(self) -> None:
        """'Stocks' should map to AssetClass.EQUITY."""
        assert _map_asset_class("Stocks") == AssetClass.EQUITY

    @pytest.mark.unit
    def test_options_maps_to_option(self) -> None:
        """'Options' should map to AssetClass.OPTION."""
        assert _map_asset_class("Options") == AssetClass.OPTION

    @pytest.mark.unit
    def test_forex_maps_to_forex(self) -> None:
        """'Forex' should map to AssetClass.FOREX."""
        assert _map_asset_class("Forex") == AssetClass.FOREX

    @pytest.mark.unit
    def test_futures_maps_to_future(self) -> None:
        """'Futures' should map to AssetClass.FUTURE."""
        assert _map_asset_class("Futures") == AssetClass.FUTURE

    @pytest.mark.unit
    def test_unknown_maps_to_equity_fallback(self) -> None:
        """Unknown category should fall back to AssetClass.EQUITY."""
        assert _map_asset_class("Bonds") == AssetClass.EQUITY

    @pytest.mark.unit
    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace in the raw value should be stripped."""
        assert _map_asset_class("  Stocks  ") == AssetClass.EQUITY


class TestParseIBKRDatetime:
    """Unit tests for the IBKR datetime parser helper."""

    @pytest.mark.unit
    def test_parses_valid_datetime(self) -> None:
        """A valid IBKR datetime string should produce a UTC-aware datetime."""
        result = _parse_ibkr_datetime("2024-03-15, 09:30:00")
        assert result == datetime(2024, 3, 15, 9, 30, 0, tzinfo=UTC)

    @pytest.mark.unit
    def test_result_is_utc(self) -> None:
        """Parsed datetime must carry UTC tzinfo."""
        result = _parse_ibkr_datetime("2024-01-01, 00:00:00")
        assert result.tzinfo is UTC

    @pytest.mark.unit
    def test_invalid_format_raises(self) -> None:
        """An invalid date string should raise ValueError."""
        with pytest.raises(ValueError):
            _parse_ibkr_datetime("not-a-date")


class TestIBKRParserParse:
    """Unit tests for IBKRParser.parse()."""

    @pytest.mark.unit
    def test_parses_single_buy_row(self) -> None:
        """A single buy row should produce one TradeCreate with LONG direction."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(quantity="100")])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert len(trades) == 1
        assert trades[0].symbol == "AAPL"
        assert trades[0].direction == Direction.LONG
        assert trades[0].quantity == Decimal("100")
        assert trades[0].asset_class == AssetClass.EQUITY

    @pytest.mark.unit
    def test_parses_single_sell_row(self) -> None:
        """A negative quantity row should produce a SHORT direction trade."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(quantity="-50")])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert len(trades) == 1
        assert trades[0].direction == Direction.SHORT
        assert trades[0].quantity == Decimal("50")

    @pytest.mark.unit
    def test_commission_is_absolute_value(self) -> None:
        """Commission should be stored as a positive Decimal."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(comm="-2.75")])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert trades[0].commission == Decimal("2.75")

    @pytest.mark.unit
    def test_zero_pnl_sets_closed_at_none(self) -> None:
        """A row with zero realized P&L should have closed_at=None (open trade)."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(pnl="0")])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert trades[0].closed_at is None
        assert trades[0].pnl is None

    @pytest.mark.unit
    def test_nonzero_pnl_sets_closed_at_and_pnl(self) -> None:
        """A row with nonzero P&L should set closed_at and pnl."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(pnl="500.00")])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert trades[0].closed_at is not None
        assert trades[0].pnl == Decimal("500.00")
        # closed_at must be strictly after opened_at.
        assert trades[0].closed_at > trades[0].opened_at  # type: ignore[operator]

    @pytest.mark.unit
    def test_missing_header_raises_import_parse_error(self) -> None:
        """A CSV without the Trades,Header row should raise ImportParseError."""
        csv_bytes = b"SomeOtherSection,Header,col1\nSomeOtherSection,Data,val1\n"
        parser = IBKRParser()
        with pytest.raises(ImportParseError, match="Could not locate"):
            parser.parse(csv_bytes, "activity.csv")

    @pytest.mark.unit
    def test_bad_row_is_skipped_with_warning(self) -> None:
        """A malformed data row should be skipped and a warning added."""
        bad_row = "Trades,Data,Order,Stocks,USD,AAPL,bad-date,100,150.00"
        csv_bytes = _make_ibkr_csv([bad_row])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert len(trades) == 0
        assert len(parser.warnings) == 1
        assert "IBKR row 1" in parser.warnings[0]

    @pytest.mark.unit
    def test_multiple_rows_parsed(self) -> None:
        """Multiple valid rows should all be parsed."""
        rows = [
            _ibkr_row(symbol="AAPL"),
            _ibkr_row(symbol="MSFT"),
            _ibkr_row(symbol="TSLA"),
        ]
        csv_bytes = _make_ibkr_csv(rows)
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert len(trades) == 3
        symbols = {t.symbol for t in trades}
        assert symbols == {"AAPL", "MSFT", "TSLA"}

    @pytest.mark.unit
    def test_invalid_utf8_raises_import_parse_error(self) -> None:
        """Non-UTF-8 bytes should raise ImportParseError."""
        parser = IBKRParser()
        with pytest.raises(ImportParseError, match="not valid UTF-8"):
            parser.parse(b"\xff\xfe invalid bytes", "activity.csv")

    @pytest.mark.unit
    def test_options_asset_class_mapped(self) -> None:
        """'Options' category rows should produce AssetClass.OPTION trades."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(asset="Options")])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert trades[0].asset_class == AssetClass.OPTION

    @pytest.mark.unit
    def test_non_order_rows_skipped(self) -> None:
        """SubTotal and Total rows should not be included in the output."""
        subtotal_row = "Trades,Data,SubTotal,Stocks,USD,,,,,,,,,,,"
        total_row = "Trades,Data,Total,,,,,,,,,,,,,,"
        valid_row = _ibkr_row(symbol="AAPL")
        csv_bytes = _make_ibkr_csv([subtotal_row, total_row, valid_row])
        parser = IBKRParser()
        trades = parser.parse(csv_bytes, "activity.csv")
        assert len(trades) == 1
        assert trades[0].symbol == "AAPL"


# ─── SchwabParser unit tests ──────────────────────────────────────────────────


class TestParseSchwabHelpers:
    """Unit tests for Schwab parser helper functions."""

    @pytest.mark.unit
    def test_parse_decimal_strips_dollar(self) -> None:
        """Dollar-prefixed strings should parse to correct Decimal."""
        assert _parse_decimal("$150.25") == Decimal("150.25")

    @pytest.mark.unit
    def test_parse_decimal_handles_comma(self) -> None:
        """Thousands-comma strings should parse correctly."""
        assert _parse_decimal("$1,234.56") == Decimal("1234.56")

    @pytest.mark.unit
    def test_parse_decimal_no_prefix(self) -> None:
        """Plain numeric strings should parse correctly."""
        assert _parse_decimal("99.99") == Decimal("99.99")

    @pytest.mark.unit
    def test_parse_schwab_date_utc_midnight(self) -> None:
        """Schwab date strings should produce UTC midnight datetimes."""
        result = _parse_schwab_date("03/15/2024")
        assert result == datetime(2024, 3, 15, 0, 0, 0, tzinfo=UTC)

    @pytest.mark.unit
    def test_parse_schwab_date_invalid_raises(self) -> None:
        """Invalid date strings should raise ValueError."""
        with pytest.raises(ValueError):
            _parse_schwab_date("2024-03-15")


class TestSchwabParserParse:
    """Unit tests for SchwabParser.parse()."""

    @pytest.mark.unit
    def test_parses_buy_row(self) -> None:
        """A 'Buy' row should produce a LONG trade."""
        csv_bytes = _make_schwab_csv([_schwab_row(action="Buy")])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 1
        assert trades[0].direction == Direction.LONG
        assert trades[0].symbol == "AAPL"
        assert trades[0].asset_class == AssetClass.EQUITY

    @pytest.mark.unit
    def test_parses_sell_row(self) -> None:
        """A 'Sell' row should produce a SHORT trade."""
        csv_bytes = _make_schwab_csv([_schwab_row(action="Sell")])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 1
        assert trades[0].direction == Direction.SHORT

    @pytest.mark.unit
    def test_non_buy_sell_rows_skipped(self) -> None:
        """Rows with actions other than Buy/Sell should be ignored."""
        dividend_row = "03/15/2024,Dividend,AAPL,Description,0,$0.00,$0.00,$0.52"
        csv_bytes = _make_schwab_csv([dividend_row, _schwab_row()])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 1

    @pytest.mark.unit
    def test_commission_stripped_of_dollar(self) -> None:
        """Dollar-prefixed fee should be parsed to a positive Decimal."""
        csv_bytes = _make_schwab_csv([_schwab_row(fees="$2.99")])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].commission == Decimal("2.99")

    @pytest.mark.unit
    def test_missing_fees_defaults_to_zero(self) -> None:
        """A row with no Fees & Comm value should default commission to zero."""
        row = "03/15/2024,Buy,AAPL,Description,10,$150.25,,$-1502.50"
        csv_bytes = _make_schwab_csv([row])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].commission == Decimal("0")

    @pytest.mark.unit
    def test_opened_at_is_utc_midnight(self) -> None:
        """Parsed opened_at should be a UTC midnight datetime."""
        csv_bytes = _make_schwab_csv([_schwab_row(date="06/01/2024")])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].opened_at == datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)

    @pytest.mark.unit
    def test_bad_row_is_skipped_with_warning(self) -> None:
        """A row with invalid price should be skipped with a warning."""
        bad_row = "03/15/2024,Buy,AAPL,Description,10,not-a-price,$1.50,-1502.50"
        csv_bytes = _make_schwab_csv([bad_row])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 0
        assert len(parser.warnings) == 1

    @pytest.mark.unit
    def test_empty_file_raises_import_parse_error(self) -> None:
        """An empty CSV file should raise ImportParseError."""
        parser = SchwabParser()
        with pytest.raises(ImportParseError, match="empty"):
            parser.parse(b"", "trade_history.csv")

    @pytest.mark.unit
    def test_missing_column_raises_import_parse_error(self) -> None:
        """A CSV missing required columns should raise ImportParseError."""
        csv_bytes = b"Date,Action,Symbol\n03/15/2024,Buy,AAPL\n"
        parser = SchwabParser()
        with pytest.raises(ImportParseError, match="missing required column"):
            parser.parse(csv_bytes, "trade_history.csv")

    @pytest.mark.unit
    def test_invalid_utf8_raises_import_parse_error(self) -> None:
        """Non-UTF-8 bytes should raise ImportParseError."""
        parser = SchwabParser()
        with pytest.raises(ImportParseError, match="not valid UTF-8"):
            parser.parse(b"\xff\xfe bad bytes", "trade_history.csv")

    @pytest.mark.unit
    def test_multiple_rows(self) -> None:
        """Multiple valid rows should all produce TradeCreate instances."""
        rows = [_schwab_row(symbol="AAPL"), _schwab_row(symbol="MSFT")]
        csv_bytes = _make_schwab_csv(rows)
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 2

    @pytest.mark.unit
    def test_closed_at_is_none(self) -> None:
        """Schwab trades are open positions; closed_at should be None."""
        csv_bytes = _make_schwab_csv([_schwab_row()])
        parser = SchwabParser()
        trades = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].closed_at is None


# ─── Factory unit tests ───────────────────────────────────────────────────────


class TestGetParser:
    """Unit tests for the parser factory."""

    @pytest.mark.unit
    def test_returns_ibkr_parser(self) -> None:
        """get_parser(IBKR) should return an IBKRParser instance."""
        parser = get_parser(BrokerType.IBKR)
        assert isinstance(parser, IBKRParser)

    @pytest.mark.unit
    def test_returns_schwab_parser(self) -> None:
        """get_parser(SCHWAB) should return a SchwabParser instance."""
        parser = get_parser(BrokerType.SCHWAB)
        assert isinstance(parser, SchwabParser)


# ─── ImportService unit tests ─────────────────────────────────────────────────


def _make_trade_create(**kwargs: object) -> TradeCreate:
    """Build a minimal :class:`TradeCreate` payload.

    Args:
        **kwargs: Field overrides.

    Returns:
        A fully-validated :class:`TradeCreate` instance.
    """
    now = datetime.now(tz=UTC)
    defaults: dict[str, object] = {
        "symbol": "AAPL",
        "direction": Direction.LONG,
        "asset_class": AssetClass.EQUITY,
        "quantity": Decimal("10"),
        "entry_price": Decimal("150.00"),
        "opened_at": now,
    }
    defaults.update(kwargs)
    return TradeCreate(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return a mock :class:`AsyncSession`."""
    return AsyncMock()


@pytest.fixture()
def import_service(mock_session: AsyncMock) -> ImportService:
    """Return an :class:`ImportService` wired to a mock session."""
    return ImportService(mock_session)


class TestImportService:
    """Unit tests for :class:`ImportService.import_file`."""

    @pytest.mark.unit
    async def test_raises_account_not_found_when_account_missing(
        self,
        import_service: ImportService,
    ) -> None:
        """import_file should raise AccountNotFoundError when account is missing."""
        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(AccountNotFoundError),
        ):
            await import_service.import_file(
                content=b"",
                filename="test.csv",
                broker=BrokerType.IBKR,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

    @pytest.mark.unit
    async def test_returns_import_result_on_success(
        self,
        import_service: ImportService,
    ) -> None:
        """import_file should return an ImportResult with correct counts."""
        fake_account = MagicMock()
        parsed_trades = [_make_trade_create(symbol="AAPL")]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = parsed_trades
        mock_parser.warnings = []

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        assert isinstance(result, ImportResult)
        assert result.trades_parsed == 1
        assert result.trades_created == 1
        assert result.trades_skipped == 0
        assert result.broker == "ibkr"
        assert result.filename == "activity.csv"

    @pytest.mark.unit
    async def test_failed_trade_create_counted_as_skipped(
        self,
        import_service: ImportService,
    ) -> None:
        """Trades that fail to persist should be counted as skipped with warnings."""
        fake_account = MagicMock()
        parsed_trades = [
            _make_trade_create(symbol="AAPL"),
            _make_trade_create(symbol="MSFT"),
        ]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = parsed_trades
        mock_parser.warnings = []

        call_count = 0

        async def create_side_effect(self_arg: object, trade: TradeCreate) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("DB error")
            return MagicMock()

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new=create_side_effect,
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        assert result.trades_created == 1
        assert result.trades_skipped == 1
        assert len(result.warnings) == 1

    @pytest.mark.unit
    async def test_parser_warnings_included_in_result(
        self,
        import_service: ImportService,
    ) -> None:
        """Warnings from the parser should be included in the ImportResult."""
        fake_account = MagicMock()

        mock_parser = MagicMock()
        mock_parser.parse.return_value = []
        mock_parser.warnings = ["IBKR row 3: skipped — bad data"]

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        assert result.warnings == ["IBKR row 3: skipped — bad data"]
        assert result.trades_parsed == 0
        assert result.trades_created == 0
        assert result.trades_skipped == 0

    @pytest.mark.unit
    async def test_account_id_stamped_on_trade(
        self,
        import_service: ImportService,
    ) -> None:
        """The account_id should be set on each trade before persisting."""
        fake_account = MagicMock()
        target_account_id = uuid.uuid4()
        parsed_trades = [_make_trade_create(symbol="AAPL")]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = parsed_trades
        mock_parser.warnings = []

        created_trades: list[TradeCreate] = []

        async def capture_create(self_arg: object, trade: TradeCreate) -> MagicMock:
            created_trades.append(trade)
            return MagicMock()

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new=capture_create,
            ),
        ):
            await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                account_id=target_account_id,
                user_id=uuid.uuid4(),
            )

        assert len(created_trades) == 1
        assert created_trades[0].account_id == target_account_id
