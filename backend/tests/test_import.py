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
from app.utils.parsers.ibkr import (
    IBKRParser,
    _extract_eur_usd_rate,
    _map_asset_class,
    _parse_ibkr_datetime,
)
from app.utils.parsers.schwab import SchwabParser, _parse_decimal, _parse_schwab_date

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_ibkr_csv(
    rows: list[str],
    forex_balances_rows: list[str] | None = None,
) -> bytes:
    """Build a minimal IBKR Activity Statement CSV with a Trades section.

    Args:
        rows: Data row lines to append after the Trades header.
        forex_balances_rows: Optional extra rows for the Forex Balances section.

    Returns:
        UTF-8 encoded CSV bytes.
    """
    header = (
        "Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,"
        "Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,"
        "Realized P&L,MTM P&L,Code\n"
    )
    content = header + "\n".join(rows)
    if forex_balances_rows:
        content += "\n" + "\n".join(forex_balances_rows)
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
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Stocks", AssetClass.EQUITY),
            ("Options", AssetClass.OPTION),
            ("Forex", AssetClass.FOREX),
            ("Futures", AssetClass.FUTURE),
            ("Bonds", AssetClass.EQUITY),  # unknown → fallback
            ("  Stocks  ", AssetClass.EQUITY),  # whitespace stripped
        ],
    )
    def test_map_asset_class(self, raw: str, expected: AssetClass) -> None:
        """Each raw category string should map to the expected AssetClass."""
        assert _map_asset_class(raw) == expected


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
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
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
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        assert len(trades) == 1
        assert trades[0].direction == Direction.SHORT
        assert trades[0].quantity == Decimal("50")

    @pytest.mark.unit
    def test_commission_is_absolute_value(self) -> None:
        """Commission should be stored as a positive Decimal."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(comm="-2.75")])
        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        assert trades[0].commission == Decimal("2.75")

    @pytest.mark.unit
    def test_zero_pnl_sets_closed_at_none(self) -> None:
        """A row with zero realized P&L should have closed_at=None (open trade)."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(pnl="0")])
        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        assert trades[0].closed_at is None
        assert trades[0].pnl is None

    @pytest.mark.unit
    def test_nonzero_pnl_sets_closed_at_and_pnl(self) -> None:
        """A row with nonzero P&L should set closed_at and pnl."""
        csv_bytes = _make_ibkr_csv([_ibkr_row(pnl="500.00")])
        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
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
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
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
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
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
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        assert trades[0].asset_class == AssetClass.OPTION

    @pytest.mark.unit
    def test_non_order_rows_skipped(self) -> None:
        """SubTotal and Total rows should not be included in the output."""
        subtotal_row = "Trades,Data,SubTotal,Stocks,USD,,,,,,,,,,,"
        total_row = "Trades,Data,Total,,,,,,,,,,,,,,"
        valid_row = _ibkr_row(symbol="AAPL")
        csv_bytes = _make_ibkr_csv([subtotal_row, total_row, valid_row])
        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        assert len(trades) == 1
        assert trades[0].symbol == "AAPL"


# ─── SchwabParser unit tests ──────────────────────────────────────────────────


class TestParseSchwabHelpers:
    """Unit tests for Schwab parser helper functions."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("$150.25", Decimal("150.25")),  # dollar prefix
            ("$1,234.56", Decimal("1234.56")),  # thousands comma
            ("99.99", Decimal("99.99")),  # no prefix
        ],
    )
    def test_parse_decimal(self, raw: str, expected: Decimal) -> None:
        """_parse_decimal should strip currency symbols and commas."""
        assert _parse_decimal(raw) == expected

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
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 1
        assert trades[0].direction == Direction.LONG
        assert trades[0].symbol == "AAPL"
        assert trades[0].asset_class == AssetClass.EQUITY

    @pytest.mark.unit
    def test_parses_sell_row(self) -> None:
        """A 'Sell' row should produce a SHORT trade."""
        csv_bytes = _make_schwab_csv([_schwab_row(action="Sell")])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 1
        assert trades[0].direction == Direction.SHORT

    @pytest.mark.unit
    def test_non_buy_sell_rows_skipped(self) -> None:
        """Rows with actions other than Buy/Sell should be ignored."""
        dividend_row = "03/15/2024,Dividend,AAPL,Description,0,$0.00,$0.00,$0.52"
        csv_bytes = _make_schwab_csv([dividend_row, _schwab_row()])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 1

    @pytest.mark.unit
    def test_commission_stripped_of_dollar(self) -> None:
        """Dollar-prefixed fee should be parsed to a positive Decimal."""
        csv_bytes = _make_schwab_csv([_schwab_row(fees="$2.99")])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].commission == Decimal("2.99")

    @pytest.mark.unit
    def test_missing_fees_defaults_to_zero(self) -> None:
        """A row with no Fees & Comm value should default commission to zero."""
        row = "03/15/2024,Buy,AAPL,Description,10,$150.25,,$-1502.50"
        csv_bytes = _make_schwab_csv([row])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].commission == Decimal("0")

    @pytest.mark.unit
    def test_opened_at_is_utc_midnight(self) -> None:
        """Parsed opened_at should be a UTC midnight datetime."""
        csv_bytes = _make_schwab_csv([_schwab_row(date="06/01/2024")])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].opened_at == datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)

    @pytest.mark.unit
    def test_bad_row_is_skipped_with_warning(self) -> None:
        """A row with invalid price should be skipped with a warning."""
        bad_row = "03/15/2024,Buy,AAPL,Description,10,not-a-price,$1.50,-1502.50"
        csv_bytes = _make_schwab_csv([bad_row])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
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
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 2

    @pytest.mark.unit
    def test_closed_at_is_none(self) -> None:
        """Schwab trades are open positions; closed_at should be None."""
        csv_bytes = _make_schwab_csv([_schwab_row()])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
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
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
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
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

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
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
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
        mock_parser.parse.return_value = ([], [])
        mock_parser.warnings = ["IBKR row 3: skipped — bad data"]
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
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
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

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
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
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


# ─── IBKRParser EUR/USD rate extraction ───────────────────────────────────────


def _forex_balances_row(pair: str = "EUR.USD", rate: str = "0.9200") -> str:
    """Build a Forex Balances data row for the IBKR CSV.

    The format used by IBKR is roughly:
    ``Forex Balances,Data,<acct>,<desc>,<pair>,<qty>,<price>,<rate>,...``

    Args:
        pair: Currency pair identifier (e.g. ``"EUR.USD"``).
        rate: Rate value string.

    Returns:
        A comma-separated row string.
    """
    # Columns: [0]=section, [1]=Data, [2]=acct, [3]=desc, [4]=pair, [5]=qty, [6]=price, [7]=rate
    return f"Forex Balances,Data,U123,EUR Base,{pair},1000,1.0,{rate},900.00"


class TestExtractEurUsdRate:
    """Unit tests for the _extract_eur_usd_rate helper."""

    @pytest.mark.unit
    def test_extracts_rate_when_present(self) -> None:
        """Returns Decimal rate when EUR.USD row is present."""
        rows_raw = "Forex Balances,Data,U123,EUR Base,EUR.USD,1000,1.0,0.9200,900.00"
        import csv
        import io

        rows = list(csv.reader(io.StringIO(rows_raw)))
        result = _extract_eur_usd_rate(rows)
        assert result == Decimal("0.9200")

    @pytest.mark.unit
    def test_returns_none_when_no_forex_balances(self) -> None:
        """Returns None when no Forex Balances section exists."""
        import csv
        import io

        rows = list(csv.reader(io.StringIO("Trades,Header,foo,bar,baz\n")))
        result = _extract_eur_usd_rate(rows)
        assert result is None

    @pytest.mark.unit
    def test_returns_none_when_pair_is_not_eur_usd(self) -> None:
        """Returns None when Forex Balances row is for a different pair."""
        rows_raw = "Forex Balances,Data,U123,GBP Base,GBP.USD,500,1.0,0.7800,390.00"
        import csv
        import io

        rows = list(csv.reader(io.StringIO(rows_raw)))
        result = _extract_eur_usd_rate(rows)
        assert result is None

    @pytest.mark.unit
    def test_returns_none_on_invalid_rate_value(self) -> None:
        """Returns None gracefully when the rate field is not numeric."""
        rows_raw = "Forex Balances,Data,U123,EUR Base,EUR.USD,1000,1.0,N/A,900.00"
        import csv
        import io

        rows = list(csv.reader(io.StringIO(rows_raw)))
        result = _extract_eur_usd_rate(rows)
        assert result is None


class TestIBKRParserEnrichPnlEur:
    """Unit tests for IBKRParser.enrich_pnl_eur()."""

    @pytest.mark.asyncio
    async def test_pnl_eur_set_from_csv_rate(self) -> None:
        """pnl_eur is computed from the CSV EUR.USD rate for closed trades."""
        forex_row = _forex_balances_row(rate="0.9200")
        trade_row = _ibkr_row(pnl="1000.00", dt="2024-03-15, 09:30:00")
        csv_bytes = _make_ibkr_csv([trade_row], forex_balances_rows=[forex_row])

        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        mock_session = AsyncMock()

        await parser.enrich_pnl_eur(trades, mock_session)

        assert trades[0].pnl_eur == Decimal("1000.00") * Decimal("0.9200")
        assert trades[0].currency == "USD"

    @pytest.mark.asyncio
    async def test_currency_set_on_open_trade_with_csv_rate(self) -> None:
        """currency='USD' is set even for open trades (pnl=None)."""
        forex_row = _forex_balances_row(rate="0.9200")
        trade_row = _ibkr_row(pnl="0")  # pnl=0 → open trade
        csv_bytes = _make_ibkr_csv([trade_row], forex_balances_rows=[forex_row])

        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        mock_session = AsyncMock()

        await parser.enrich_pnl_eur(trades, mock_session)

        assert trades[0].pnl_eur is None  # no pnl, so no pnl_eur
        assert trades[0].currency == "USD"

    @pytest.mark.asyncio
    async def test_fallback_to_bundesbank_when_no_csv_rate(self) -> None:
        """Falls back to FxRateService when no EUR.USD row is in the CSV."""
        trade_row = _ibkr_row(pnl="500.00", dt="2024-03-15, 09:30:00")
        csv_bytes = _make_ibkr_csv([trade_row])  # no forex_balances_rows

        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        mock_session = AsyncMock()

        mock_fx = AsyncMock()
        mock_fx.get_usd_to_eur = AsyncMock(return_value=Decimal("0.9100"))

        with patch(
            "app.services.fx_rate_service.FxRateService",
            return_value=mock_fx,
        ):
            await parser.enrich_pnl_eur(trades, mock_session)

        assert trades[0].pnl_eur == Decimal("500.00") * Decimal("0.9100")
        mock_fx.get_usd_to_eur.assert_called_once()

    @pytest.mark.asyncio
    async def test_pnl_eur_null_when_fallback_also_fails(self) -> None:
        """pnl_eur stays None and a warning is added when API is unavailable."""
        trade_row = _ibkr_row(pnl="500.00")
        csv_bytes = _make_ibkr_csv([trade_row])

        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        mock_session = AsyncMock()

        mock_fx = AsyncMock()
        mock_fx.get_usd_to_eur = AsyncMock(return_value=None)

        with patch(
            "app.services.fx_rate_service.FxRateService",
            return_value=mock_fx,
        ):
            await parser.enrich_pnl_eur(trades, mock_session)

        assert trades[0].pnl_eur is None
        assert any("unavailable" in w for w in parser.warnings)

    @pytest.mark.asyncio
    async def test_multi_day_warning_emitted(self) -> None:
        """A warning is added when trades span multiple calendar days."""
        forex_row = _forex_balances_row(rate="0.9200")
        row_day1 = _ibkr_row(pnl="100.00", dt="2024-03-15, 09:30:00")
        row_day2 = _ibkr_row(pnl="200.00", dt="2024-03-18, 10:00:00", symbol="MSFT")
        csv_bytes = _make_ibkr_csv(
            [row_day1, row_day2],
            forex_balances_rows=[forex_row],
        )

        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        mock_session = AsyncMock()

        await parser.enrich_pnl_eur(trades, mock_session)

        assert any("multiple trading days" in w for w in parser.warnings)

    @pytest.mark.asyncio
    async def test_no_multi_day_warning_for_single_day(self) -> None:
        """No multi-day warning when all trades share the same date."""
        forex_row = _forex_balances_row(rate="0.9200")
        row1 = _ibkr_row(pnl="100.00", dt="2024-03-15, 09:30:00")
        row2 = _ibkr_row(pnl="200.00", dt="2024-03-15, 11:00:00", symbol="MSFT")
        csv_bytes = _make_ibkr_csv(
            [row1, row2],
            forex_balances_rows=[forex_row],
        )

        parser = IBKRParser()
        trades, cash_txs = parser.parse(csv_bytes, "activity.csv")
        mock_session = AsyncMock()

        await parser.enrich_pnl_eur(trades, mock_session)

        assert not any("multiple trading days" in w for w in parser.warnings)


# ─── SchwabParser EUR/USD enrichment ──────────────────────────────────────────


class TestSchwabParserCurrencyField:
    """Tests that SchwabParser.parse() sets currency='USD' on each trade."""

    @pytest.mark.unit
    def test_currency_is_usd(self) -> None:
        """Every parsed Schwab trade should have currency='USD'."""
        csv_bytes = _make_schwab_csv([_schwab_row()])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert trades[0].currency == "USD"


class TestSchwabParserEnrichPnlEur:
    """Unit tests for SchwabParser.enrich_pnl_eur()."""

    @pytest.mark.asyncio
    async def test_pnl_eur_set_when_rate_available(self) -> None:
        """pnl_eur is set for a closed trade when FxRateService returns a rate."""
        # Build a Schwab trade with pnl set manually (Schwab parser leaves pnl=None,
        # so we craft a TradeCreate directly to test the enrichment logic).
        now = datetime(2024, 3, 15, 0, 0, 0, tzinfo=UTC)
        trade = TradeCreate(
            symbol="AAPL",
            direction=Direction.LONG,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("10"),
            entry_price=Decimal("150.00"),
            opened_at=now,
            pnl=Decimal("500.00"),
            currency="USD",
        )
        trades = [trade]

        mock_session = AsyncMock()
        mock_fx = AsyncMock()
        mock_fx.get_usd_to_eur = AsyncMock(return_value=Decimal("0.9150"))

        parser = SchwabParser()

        with patch(
            "app.services.fx_rate_service.FxRateService",
            return_value=mock_fx,
        ):
            await parser.enrich_pnl_eur(trades, mock_session)

        assert trades[0].pnl_eur == Decimal("500.00") * Decimal("0.9150")

    @pytest.mark.asyncio
    async def test_pnl_eur_null_when_rate_unavailable(self) -> None:
        """pnl_eur stays None and a warning is added when rate is unavailable."""
        now = datetime(2024, 3, 15, 0, 0, 0, tzinfo=UTC)
        trade = TradeCreate(
            symbol="AAPL",
            direction=Direction.LONG,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("10"),
            entry_price=Decimal("150.00"),
            opened_at=now,
            pnl=Decimal("300.00"),
            currency="USD",
        )
        trades = [trade]

        mock_session = AsyncMock()
        mock_fx = AsyncMock()
        mock_fx.get_usd_to_eur = AsyncMock(return_value=None)

        parser = SchwabParser()

        with patch(
            "app.services.fx_rate_service.FxRateService",
            return_value=mock_fx,
        ):
            await parser.enrich_pnl_eur(trades, mock_session)

        assert trades[0].pnl_eur is None
        assert any("unavailable" in w for w in parser.warnings)

    @pytest.mark.asyncio
    async def test_open_trade_not_enriched(self) -> None:
        """Trades without pnl (open positions) should not trigger an FX lookup."""
        csv_bytes = _make_schwab_csv([_schwab_row()])  # pnl=None (open)
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")

        mock_session = AsyncMock()
        mock_fx = AsyncMock()
        mock_fx.get_usd_to_eur = AsyncMock(return_value=Decimal("0.9200"))

        with patch(
            "app.services.fx_rate_service.FxRateService",
            return_value=mock_fx,
        ):
            await parser.enrich_pnl_eur(trades, mock_session)

        mock_fx.get_usd_to_eur.assert_not_called()
        assert trades[0].pnl_eur is None

    @pytest.mark.asyncio
    async def test_per_date_rate_lookup(self) -> None:
        """Each unique trade date results in exactly one FxRateService call."""
        day1 = datetime(2024, 3, 15, 0, 0, 0, tzinfo=UTC)
        day2 = datetime(2024, 3, 18, 0, 0, 0, tzinfo=UTC)

        def _make_t(opened_at: datetime) -> TradeCreate:
            return TradeCreate(
                symbol="AAPL",
                direction=Direction.LONG,
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("10"),
                entry_price=Decimal("150.00"),
                opened_at=opened_at,
                pnl=Decimal("100.00"),
                currency="USD",
            )

        trades = [_make_t(day1), _make_t(day1), _make_t(day2)]

        mock_session = AsyncMock()
        mock_fx = AsyncMock()
        mock_fx.get_usd_to_eur = AsyncMock(return_value=Decimal("0.92"))

        parser = SchwabParser()

        with patch(
            "app.services.fx_rate_service.FxRateService",
            return_value=mock_fx,
        ):
            await parser.enrich_pnl_eur(trades, mock_session)

        # Two unique dates → two calls.
        assert mock_fx.get_usd_to_eur.call_count == 2


class TestSchwabCashTransactionParsing:
    @pytest.mark.unit
    def test_parses_dividend_row(self) -> None:
        """A Dividend row should produce a DIVIDEND CashTransactionCreateRequest."""
        from app.models.cash_transaction import CashTransactionType

        dividend_row = "03/15/2024,Dividend,AAPL,Apple Div,0,$0.00,$0.00,$0.52"
        csv_bytes = _make_schwab_csv([dividend_row])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 0
        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.DIVIDEND
        assert cash_txs[0].amount == Decimal("0.52")
        assert cash_txs[0].symbol == "AAPL"

    @pytest.mark.unit
    def test_parses_tax_withholding_row(self) -> None:
        """A Tax Withholding row should produce a WITHHOLDING_TAX CashTransactionCreateRequest."""
        from app.models.cash_transaction import CashTransactionType

        tax_row = "03/15/2024,Tax Withholding,,,0,$0.00,$0.00,$-0.15"
        csv_bytes = _make_schwab_csv([tax_row])
        parser = SchwabParser()
        trades, cash_txs = parser.parse(csv_bytes, "trade_history.csv")
        assert len(trades) == 0
        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.WITHHOLDING_TAX
        assert cash_txs[0].amount == Decimal("-0.15")


# ─── IBKRXMLParser cash transaction tests ─────────────────────────────────────


def _make_ibkr_xml(trades_xml: str = "", cash_txs_xml: str = "") -> bytes:
    """Build a minimal IBKR Flex Query XML document.

    Args:
        trades_xml: Inner XML string containing ``<Trade>`` elements.
        cash_txs_xml: Inner XML string containing ``<CashTransaction>`` elements.

    Returns:
        UTF-8 encoded XML bytes.
    """
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<FlexQueryResponse>"
        "<FlexStatements>"
        "<FlexStatement>"
        "<Trades>"
        f"{trades_xml}"
        "</Trades>"
        "<CashTransactions>"
        f"{cash_txs_xml}"
        "</CashTransactions>"
        "</FlexStatement>"
        "</FlexStatements>"
        "</FlexQueryResponse>"
    )
    return xml.encode("utf-8")


class TestIBKRXMLParserCashTransactions:
    """Unit tests for IBKRXMLParser cash transaction and CASH trade handling."""

    @pytest.mark.unit
    def test_parses_dividend_cash_transaction(self) -> None:
        """A <CashTransaction type='Dividends'> element should produce a DIVIDEND record."""
        from app.models.cash_transaction import CashTransactionType
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        cash_tx_xml = (
            '<CashTransaction reportDate="20240315" dateTime="20240315;093000" '
            'amount="52.00" currency="USD" type="Dividends" symbol="AAPL" '
            'description="AAPL Dividend" />'
        )
        xml_bytes = _make_ibkr_xml(cash_txs_xml=cash_tx_xml)
        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 0
        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.DIVIDEND
        assert cash_txs[0].amount == Decimal("52.00")
        assert cash_txs[0].currency == "USD"
        assert cash_txs[0].symbol == "AAPL"

    @pytest.mark.unit
    def test_parses_withholding_tax_cash_transaction(self) -> None:
        """A <CashTransaction type='Withholding Tax'> element should produce a WITHHOLDING_TAX record."""
        from app.models.cash_transaction import CashTransactionType
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        cash_tx_xml = (
            '<CashTransaction reportDate="20240315" dateTime="20240315;093000" '
            'amount="-5.20" currency="USD" type="Withholding Tax" symbol="AAPL" '
            'description="AAPL WHT" />'
        )
        xml_bytes = _make_ibkr_xml(cash_txs_xml=cash_tx_xml)
        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml_bytes, "flex.xml")

        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.WITHHOLDING_TAX
        assert cash_txs[0].amount == Decimal("-5.20")

    @pytest.mark.unit
    def test_cash_trade_filtered_out_as_trade(self) -> None:
        """A <Trade assetCategory='CASH'> must NOT appear in the trades list."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        # A currency-conversion trade (EUR.USD) with a commission
        trade_xml = (
            '<Trade assetCategory="CASH" symbol="EUR.USD" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="1000" tradePrice="1.08" '
            'commission="-2.00" currency="USD" fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=trade_xml)
        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 0, "CASH assetCategory must not produce a Trade record"

    @pytest.mark.unit
    def test_cash_trade_commission_extracted_as_fee(self) -> None:
        """A <Trade assetCategory='CASH'> with commission should produce a FEE cash transaction."""
        from app.models.cash_transaction import CashTransactionType
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        trade_xml = (
            '<Trade assetCategory="CASH" symbol="EUR.USD" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="1000" tradePrice="1.08" '
            'commission="-2.00" currency="USD" fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=trade_xml)
        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml_bytes, "flex.xml")

        assert len(cash_txs) == 1
        assert cash_txs[0].type == CashTransactionType.FEE
        assert cash_txs[0].amount == Decimal("-2.00")
        assert cash_txs[0].currency == "USD"

    @pytest.mark.unit
    def test_cash_trade_zero_commission_skipped(self) -> None:
        """A <Trade assetCategory='CASH'> with zero commission should produce no cash transaction."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        trade_xml = (
            '<Trade assetCategory="CASH" symbol="EUR.USD" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="1000" tradePrice="1.08" '
            'commission="0" currency="USD" fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=trade_xml)
        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 0
        assert len(cash_txs) == 0

    @pytest.mark.unit
    def test_normal_trade_still_parsed_alongside_cash_trade(self) -> None:
        """Filtering CASH trades must not affect normal STK trades."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        normal_trade = (
            '<Trade assetCategory="STK" symbol="AAPL" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="10" tradePrice="150.00" '
            'commission="-1.50" currency="USD" fifoPnlRealized="0" />'
        )
        cash_trade = (
            '<Trade assetCategory="CASH" symbol="EUR.USD" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="1000" tradePrice="1.08" '
            'commission="-2.00" currency="USD" fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=normal_trade + cash_trade)
        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 1
        assert trades[0].symbol == "AAPL"
        assert len(cash_txs) == 1
        assert cash_txs[0].description is not None
        assert "EUR.USD" in cash_txs[0].description

    @pytest.mark.unit
    def test_cash_transaction_missing_amount_skipped(self) -> None:
        """A <CashTransaction> with no amount attribute should be skipped with a warning."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        cash_tx_xml = (
            '<CashTransaction reportDate="20240315" dateTime="20240315;093000" '
            'currency="USD" type="Dividends" symbol="AAPL" />'
        )
        xml_bytes = _make_ibkr_xml(cash_txs_xml=cash_tx_xml)
        parser = IBKRXMLParser()
        trades, cash_txs = parser.parse(xml_bytes, "flex.xml")

        assert len(cash_txs) == 0
        assert len(parser.warnings) == 1
        assert "missing amount" in parser.warnings[0]


# ─── Corporate action stub ─────────────────────────────────────────────────────


from dataclasses import dataclass  # noqa: E402
from datetime import date  # noqa: E402


@dataclass
class _CaSplitStub:
    """Minimal stub that satisfies the :class:`CorporateActionLike` protocol.

    Used in unit tests so that we do not need a real DB-backed
    :class:`~app.models.corporate_action.CorporateAction` instance.

    Attributes:
        symbol: Ticker symbol the corporate action applies to.
        date: Calendar date on which the split took effect.
        ratio: Split ratio (after / before shares).
        old_conid: Broker contract ID before the split.
        new_conid: Broker contract ID after the split.
    """

    symbol: str
    date: date
    ratio: Decimal
    old_conid: str | None
    new_conid: str | None


# ─── TestImportWithSplit ───────────────────────────────────────────────────────


class TestImportWithSplit:
    """Unit tests for split-adjusted FIFO aggregation and ImportService skip logic."""

    # ── aggregate_executions_fifo: 1:20 reverse split scenario ────────────────

    @pytest.mark.unit
    def test_reverse_split_adjusts_open_lot_and_produces_one_completed_trade(
        self,
    ) -> None:
        """A 1:20 reverse split should adjust the open lot and close correctly.

        Scenario (OTLK):
        1. Buy 1 000 shares  →  open lot
        2. 1:20 reverse split (ratio = 0.05) on 2023-05-01
           → lot becomes 50 shares at 20× the original entry price
        3. Sell 50 shares (with realised pnl) → 1 completed round-trip trade
        """
        from app.utils.parsers.aggregator import aggregate_executions_fifo

        buy_time = datetime(2023, 4, 1, 9, 30, tzinfo=UTC)
        sell_time = datetime(2023, 6, 1, 9, 30, tzinfo=UTC)

        buy_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.00"),
            opened_at=buy_time,
            broker_conid="357194941",
        )
        sell_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("20.00"),
            opened_at=sell_time,
            pnl=Decimal("500.00"),
            broker_conid="690184975",
        )

        split = _CaSplitStub(
            symbol="OTLK",
            date=date(2023, 5, 1),
            ratio=Decimal("0.05"),
            old_conid="357194941",
            new_conid="690184975",
        )

        result = aggregate_executions_fifo(
            [buy_exec, sell_exec],
            corporate_actions=[split],
        )

        # Exactly one completed trade (the reversed-split lot closed by the sell)
        completed = [t for t in result if t.closed_at is not None]
        assert len(completed) == 1, (
            f"Expected exactly 1 completed trade, got {len(completed)}: "
            f"{[str(t) for t in result]}"
        )
        trade = completed[0]
        # After 1:20 split the 1 000-share lot becomes 50 shares
        assert trade.quantity == Decimal("50")
        assert trade.symbol == "OTLK"

    @pytest.mark.unit
    def test_reverse_split_adjusts_entry_price_by_inverse_ratio(self) -> None:
        """After a 1:20 reverse split the entry price must be divided by the ratio.

        Original entry price: $1.00.
        Ratio = 0.05  → adjusted entry price = $1.00 / 0.05 = $20.00.
        """
        from app.utils.parsers.aggregator import aggregate_executions_fifo

        buy_time = datetime(2023, 4, 1, 9, 30, tzinfo=UTC)
        sell_time = datetime(2023, 6, 1, 9, 30, tzinfo=UTC)

        buy_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.00"),
            opened_at=buy_time,
            broker_conid="357194941",
        )
        sell_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("20.00"),
            opened_at=sell_time,
            pnl=Decimal("0"),
            broker_conid="690184975",
        )

        split = _CaSplitStub(
            symbol="OTLK",
            date=date(2023, 5, 1),
            ratio=Decimal("0.05"),
            old_conid="357194941",
            new_conid="690184975",
        )

        result = aggregate_executions_fifo(
            [buy_exec, sell_exec],
            corporate_actions=[split],
        )

        completed = [t for t in result if t.closed_at is not None]
        assert len(completed) == 1
        # entry_price of the stored lot: $1.00 / 0.05 = $20.00
        assert completed[0].entry_price == pytest.approx(Decimal("20.00"))

    @pytest.mark.unit
    def test_without_corporate_action_split_leaves_residual_open_lot(self) -> None:
        """Without a corporate action, only 50 of the 1 000-share lot are closed.

        When a 50-share closing execution arrives against a 1 000-share open lot
        (and no split has been registered), the FIFO aggregator matches what it
        can (50 shares → 1 completed trade) and leaves the residual 950 shares as
        an open lot.  The split test above demonstrates that registering the
        corporate action is what makes the lot sizes align exactly.
        """
        from app.utils.parsers.aggregator import aggregate_executions_fifo

        buy_time = datetime(2023, 4, 1, 9, 30, tzinfo=UTC)
        sell_time = datetime(2023, 6, 1, 9, 30, tzinfo=UTC)

        buy_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.00"),
            opened_at=buy_time,
        )
        # pnl is set → treated as a closing leg by the aggregator
        sell_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("20.00"),
            opened_at=sell_time,
            pnl=Decimal("500.00"),
        )

        result = aggregate_executions_fifo([buy_exec, sell_exec])

        completed = [t for t in result if t.closed_at is not None]
        open_lots = [t for t in result if t.closed_at is None]
        # 50 shares closed, 950 shares still open (sizes did not match)
        assert len(completed) == 1
        assert len(open_lots) == 1
        assert open_lots[0].quantity == Decimal("950")

    # ── ImportService: skip_manually_edited ───────────────────────────────────

    @pytest.mark.unit
    async def test_import_service_skips_manually_edited_trade(
        self,
        import_service: ImportService,
    ) -> None:
        """import_file must skip trades whose (broker_conid, opened_at) key is in
        the manually-edited set, and count them in trades_skipped (not created).

        Scenario:
        - Parser produces two trades.
        - One trade's key is in the manually-edited set.
        - Only the other trade should be persisted (trades_created = 1).
        - The skipped trade should NOT appear in trades_created or trades_skipped
          (error-skipped); the result's trades_skipped counter reflects the
          difference between parsed and created + manually-edited.
        """
        fake_account = MagicMock()
        now = datetime.now(tz=UTC)

        # Two trades; the second will be in the manually-edited set.
        trade_a = _make_trade_create(
            symbol="AAPL",
            opened_at=now,
            broker_conid="111111111",
        )
        trade_b = _make_trade_create(
            symbol="OTLK",
            opened_at=now,
            broker_conid="357194941",
        )

        # The key for trade_b is in the manually-edited set.
        manually_edited: set[tuple[str | None, datetime]] = {
            ("357194941", now),
        }

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ([trade_a, trade_b], [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=manually_edited,
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

        # trade_a is persisted; trade_b is silently skipped (manually edited)
        assert result.trades_parsed == 2
        assert result.trades_created == 1
        # trades_skipped = parsed - created - manually_edited_skipped = 2 - 1 - 1 = 0
        assert result.trades_skipped == 0

    @pytest.mark.unit
    async def test_import_service_creates_all_when_no_manually_edited(
        self,
        import_service: ImportService,
    ) -> None:
        """All parsed trades should be created when the manually-edited set is empty."""
        fake_account = MagicMock()
        parsed_trades = [
            _make_trade_create(symbol="AAPL", broker_conid="111111111"),
            _make_trade_create(symbol="MSFT", broker_conid="222222222"),
        ]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
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

        assert result.trades_parsed == 2
        assert result.trades_created == 2
        assert result.trades_skipped == 0
