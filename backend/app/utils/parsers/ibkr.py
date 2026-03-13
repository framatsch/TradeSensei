"""Interactive Brokers (IBKR) Activity Statement CSV parser.

IBKR exports a multi-section CSV.  This parser extracts the ``Trades``
section and maps each data row to a :class:`~app.schemas.trade.TradeCreate`.

Expected header row within the Trades section::

    Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,
    Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,
    Realized P&L,MTM P&L,Code

Data rows have the prefix ``Trades,Data,Order,...``.
"""

import csv
import io
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.core.exceptions import ImportParseError
from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.base import BrokerParser

logger = logging.getLogger(__name__)

# ─── Column index constants ───────────────────────────────────────────────────
# These indices match the IBKR Activity Statement Trades section header.

_COL_ASSET_CATEGORY: int = 3
_COL_CURRENCY: int = 4
_COL_SYMBOL: int = 5
_COL_DATETIME: int = 6
_COL_QUANTITY: int = 7
_COL_T_PRICE: int = 8
_COL_COMM_FEE: int = 11
_COL_REALIZED_PNL: int = 13

# ─── IBKR asset category mapping ─────────────────────────────────────────────

_ASSET_CLASS_MAP: dict[str, AssetClass] = {
    "Stocks": AssetClass.EQUITY,
    "Options": AssetClass.OPTION,
    "Forex": AssetClass.FOREX,
    "Futures": AssetClass.FUTURE,
}

# ─── Datetime format ──────────────────────────────────────────────────────────

_IBKR_DATETIME_FORMAT: str = "%Y-%m-%d, %H:%M:%S"

# ─── Minimum expected column count ───────────────────────────────────────────

_MIN_COLUMNS: int = 16

# ─── Closed-trade timestamp offset ───────────────────────────────────────────
# IBKR rows carry a single timestamp.  TradeCreate requires closed_at > opened_at,
# so we add a one-second delta when a trade is recorded as closed (realized P&L ≠ 0).

_CLOSED_AT_OFFSET: timedelta = timedelta(seconds=1)


def _map_asset_class(raw: str) -> AssetClass:
    """Map an IBKR asset-category string to an :class:`~app.models.trade.AssetClass`.

    Args:
        raw: The raw asset category string from the IBKR export.

    Returns:
        The corresponding :class:`~app.models.trade.AssetClass` value.
        Falls back to :attr:`~app.models.trade.AssetClass.EQUITY` for
        unrecognised categories.
    """
    return _ASSET_CLASS_MAP.get(raw.strip(), AssetClass.EQUITY)


def _parse_decimal(raw: str) -> Decimal:
    """Parse a string into a :class:`~decimal.Decimal`, stripping commas.

    Args:
        raw: Raw numeric string, potentially containing commas as
            thousands separators (e.g. ``"1,234.56"``).

    Returns:
        The parsed :class:`~decimal.Decimal` value.

    Raises:
        decimal.InvalidOperation: If the string cannot be converted.
    """
    return Decimal(raw.strip().replace(",", ""))


def _parse_ibkr_datetime(raw: str) -> datetime:
    """Parse an IBKR ``Date/Time`` field into a timezone-aware UTC datetime.

    IBKR format: ``"YYYY-MM-DD, HH:MM:SS"``.

    Args:
        raw: The raw date/time string from the IBKR export.

    Returns:
        A timezone-aware :class:`~datetime.datetime` in UTC.

    Raises:
        ValueError: If the string does not match the expected format.
    """
    dt = datetime.strptime(raw.strip(), _IBKR_DATETIME_FORMAT)
    return dt.replace(tzinfo=UTC)


class IBKRParser(BrokerParser):
    """Parser for Interactive Brokers Activity Statement CSV exports.

    Scans the raw CSV bytes for the ``Trades`` section, identifies the
    header row, and converts each ``Order``-discriminator data row into
    a :class:`~app.schemas.trade.TradeCreate`.

    Rows that fail to parse are skipped; the warning message is stored in
    :attr:`warnings` and can be retrieved after calling :meth:`parse`.

    Attributes:
        warnings: List of non-fatal warning messages collected during
            the most recent :meth:`parse` call.
    """

    def __init__(self) -> None:
        """Initialise the parser with an empty warnings list."""
        self.warnings: list[str] = []

    def parse(self, content: bytes, filename: str) -> list[TradeCreate]:
        """Parse an IBKR Activity Statement CSV into :class:`TradeCreate` objects.

        Args:
            content: Raw CSV file bytes.
            filename: Original filename (present for interface compatibility;
                IBKR exports are always CSV).

        Returns:
            A list of :class:`~app.schemas.trade.TradeCreate` instances.

        Raises:
            ImportParseError: If the Trades section cannot be located in
                the file.
        """
        self.warnings = []
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportParseError("IBKR file is not valid UTF-8 text.") from exc

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        # Locate the Trades header row and collect data rows.
        header_found: bool = False
        trade_rows: list[list[str]] = []

        for row in rows:
            if not row:
                continue
            if row[0] == "Trades" and len(row) > 1 and row[1] == "Header":
                header_found = True
                continue
            if (
                header_found
                and row[0] == "Trades"
                and len(row) > 2
                and row[2] == "Order"
            ):
                trade_rows.append(row)

        if not header_found:
            raise ImportParseError(
                "Could not locate the 'Trades,Header' section in the IBKR file. "
                "Please export an Activity Statement in CSV format."
            )

        trades: list[TradeCreate] = []
        for row_num, row in enumerate(trade_rows, start=1):
            try:
                trades.append(self._parse_row(row))
            except (ValueError, InvalidOperation, IndexError) as exc:
                msg = f"IBKR row {row_num}: skipped — {exc}"
                logger.warning(msg)
                self.warnings.append(msg)

        return trades

    def _parse_row(self, row: list[str]) -> TradeCreate:
        """Convert a single IBKR trades data row into a :class:`TradeCreate`.

        Args:
            row: Parsed CSV row fields.

        Returns:
            A validated :class:`~app.schemas.trade.TradeCreate`.

        Raises:
            ValueError: If any required field is missing or invalid.
            IndexError: If the row has fewer columns than expected.
            decimal.InvalidOperation: If a numeric field cannot be parsed.
        """
        if len(row) < _MIN_COLUMNS:
            raise ValueError(
                f"Row has only {len(row)} columns; expected at least {_MIN_COLUMNS}."
            )

        symbol = row[_COL_SYMBOL].strip()
        asset_class = _map_asset_class(row[_COL_ASSET_CATEGORY])

        quantity_raw = _parse_decimal(row[_COL_QUANTITY])
        direction = Direction.LONG if quantity_raw > 0 else Direction.SHORT
        quantity = abs(quantity_raw)

        entry_price = _parse_decimal(row[_COL_T_PRICE])
        commission = abs(_parse_decimal(row[_COL_COMM_FEE]))

        realized_pnl_raw = _parse_decimal(row[_COL_REALIZED_PNL])
        pnl: Decimal | None = (
            realized_pnl_raw if realized_pnl_raw != Decimal("0") else None
        )

        opened_at = _parse_ibkr_datetime(row[_COL_DATETIME])
        # A non-zero realized P&L indicates the position was closed on this row.
        # TradeCreate requires closed_at > opened_at, so add a 1-second offset.
        closed_at: datetime | None = (
            opened_at + _CLOSED_AT_OFFSET if pnl is not None else None
        )

        return TradeCreate(
            symbol=symbol,
            direction=direction,
            asset_class=asset_class,
            quantity=quantity,
            entry_price=entry_price,
            commission=commission,
            pnl=pnl,
            opened_at=opened_at,
            closed_at=closed_at,
        )
