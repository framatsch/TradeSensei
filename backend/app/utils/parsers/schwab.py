"""Charles Schwab trade history CSV parser.

Schwab's trade history export is a plain CSV with the following header::

    Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount

This parser processes ``Buy`` and ``Sell`` action rows only and maps
them to :class:`~app.schemas.trade.TradeCreate` objects.
"""

import csv
import io
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from app.core.exceptions import ImportParseError
from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.base import BrokerParser

logger = logging.getLogger(__name__)

# ─── Schwab CSV column names ──────────────────────────────────────────────────

_COL_DATE: str = "Date"
_COL_ACTION: str = "Action"
_COL_SYMBOL: str = "Symbol"
_COL_QUANTITY: str = "Quantity"
_COL_PRICE: str = "Price"
_COL_FEES: str = "Fees & Comm"

# ─── Schwab date format ───────────────────────────────────────────────────────

_SCHWAB_DATE_FORMAT: str = "%m/%d/%Y"

# ─── Processable action values ────────────────────────────────────────────────

_ACTION_BUY: str = "Buy"
_ACTION_SELL: str = "Sell"
_PROCESSABLE_ACTIONS: frozenset[str] = frozenset({_ACTION_BUY, _ACTION_SELL})


def _strip_currency_symbol(raw: str) -> str:
    """Remove a leading ``$`` and surrounding whitespace from a numeric string.

    Args:
        raw: Raw string that may contain a ``$`` prefix (e.g. ``"$150.25"``).

    Returns:
        A clean numeric string suitable for :class:`~decimal.Decimal` parsing.
    """
    return raw.strip().lstrip("$").strip()


def _parse_decimal(raw: str) -> Decimal:
    """Parse a (possibly dollar-prefixed) string into a :class:`~decimal.Decimal`.

    Args:
        raw: Raw numeric string, optionally prefixed with ``$`` and/or
            containing commas as thousands separators.

    Returns:
        The parsed :class:`~decimal.Decimal` value.

    Raises:
        decimal.InvalidOperation: If the string cannot be converted.
    """
    cleaned = _strip_currency_symbol(raw).replace(",", "")
    return Decimal(cleaned)


def _parse_schwab_date(raw: str) -> datetime:
    """Parse a Schwab ``Date`` field into a timezone-aware UTC midnight datetime.

    Schwab format: ``"MM/DD/YYYY"``.

    Args:
        raw: The raw date string from the Schwab export.

    Returns:
        A timezone-aware :class:`~datetime.datetime` at midnight UTC.

    Raises:
        ValueError: If the string does not match the expected format.
    """
    dt = datetime.strptime(raw.strip(), _SCHWAB_DATE_FORMAT)
    return dt.replace(tzinfo=UTC)


class SchwabParser(BrokerParser):
    """Parser for Charles Schwab trade history CSV exports.

    Reads the CSV header to locate required columns by name, then
    converts each ``Buy``/``Sell`` row into a
    :class:`~app.schemas.trade.TradeCreate`.

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
        """Parse a Schwab trade history CSV into :class:`TradeCreate` objects.

        Args:
            content: Raw CSV file bytes.
            filename: Original filename (present for interface compatibility;
                Schwab exports are always CSV).

        Returns:
            A list of :class:`~app.schemas.trade.TradeCreate` instances.

        Raises:
            ImportParseError: If the file cannot be decoded or is missing
                required CSV columns.
        """
        self.warnings = []
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportParseError("Schwab file is not valid UTF-8 text.") from exc

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ImportParseError("Schwab CSV file appears to be empty.")

        required_cols = {_COL_DATE, _COL_ACTION, _COL_SYMBOL, _COL_QUANTITY, _COL_PRICE}
        fieldnames_set = set(reader.fieldnames)
        missing = required_cols - fieldnames_set
        if missing:
            raise ImportParseError(
                f"Schwab CSV is missing required column(s): "
                f"{', '.join(sorted(missing))}."
            )

        trades: list[TradeCreate] = []
        for row_num, row in enumerate(reader, start=2):  # 1-based; row 1 is the header
            action = row.get(_COL_ACTION, "").strip()
            if action not in _PROCESSABLE_ACTIONS:
                continue
            try:
                trades.append(self._parse_row(row))
            except (ValueError, InvalidOperation, KeyError) as exc:
                msg = f"Schwab row {row_num}: skipped — {exc}"
                logger.warning(msg)
                self.warnings.append(msg)

        return trades

    def _parse_row(self, row: dict[str, str]) -> TradeCreate:
        """Convert a single Schwab CSV row dict into a :class:`TradeCreate`.

        Args:
            row: Dictionary of column name → raw string value.

        Returns:
            A validated :class:`~app.schemas.trade.TradeCreate`.

        Raises:
            ValueError: If a required field is empty or invalid.
            KeyError: If an expected column is absent.
            decimal.InvalidOperation: If a numeric field cannot be parsed.
        """
        symbol = row[_COL_SYMBOL].strip()
        if not symbol:
            raise ValueError("Symbol column is empty.")

        action = row[_COL_ACTION].strip()
        direction = Direction.LONG if action == _ACTION_BUY else Direction.SHORT

        quantity = abs(_parse_decimal(row[_COL_QUANTITY]))
        entry_price = _parse_decimal(row[_COL_PRICE])

        fees_raw = row.get(_COL_FEES, "").strip()
        commission = abs(_parse_decimal(fees_raw)) if fees_raw else Decimal("0")

        opened_at = _parse_schwab_date(row[_COL_DATE])

        return TradeCreate(
            symbol=symbol,
            direction=direction,
            asset_class=AssetClass.EQUITY,
            quantity=quantity,
            entry_price=entry_price,
            commission=commission,
            opened_at=opened_at,
        )
