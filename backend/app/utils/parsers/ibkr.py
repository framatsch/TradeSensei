from app.schemas.cash_transaction import CashTransactionCreateRequest

"""Interactive Brokers (IBKR) Activity Statement CSV parser.

IBKR exports a multi-section CSV.  This parser extracts the ``Trades``
section and maps each data row to a :class:`~app.schemas.trade.TradeCreate`.

Expected header row within the Trades section::

    Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,
    Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,
    Realized P&L,MTM P&L,Code

Data rows have the prefix ``Trades,Data,Order,...``.

Additionally, the parser reads the ``Forex Balances`` section to extract
the ``EUR.USD`` rate, which is used to populate ``pnl_eur`` for all closed
trades.  If no CSV rate is found, a fallback is performed via
:class:`~app.services.fx_rate_service.FxRateService` for the earliest
trade date.
"""

import csv
import io
import logging
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

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

# ─── Forex Balances section constants ────────────────────────────────────────

_FOREX_BALANCES_SECTION: str = "Forex Balances"
# Column index of the currency pair identifier in the Forex Balances section.
_COL_FB_PAIR: int = 4
# Column index of the rate value in the Forex Balances section.
_COL_FB_RATE: int = 7
_EUR_USD_PAIR: str = "EUR.USD"

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

_MULTI_DAY_WARNING: str = (
    "IBKR import spans multiple trading days but uses a single EUR/USD rate "
    "from the CSV export. pnl_eur values for days other than the export date "
    "may be slightly inaccurate. Consider importing per-day statements."
)


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
    parsed = datetime.strptime(raw.strip(), _IBKR_DATETIME_FORMAT)
    return parsed.replace(tzinfo=UTC)


class IBKRParser(BrokerParser):
    """Parser for Interactive Brokers Activity Statement CSV exports.

    Scans the raw CSV bytes for the ``Trades`` section, identifies the
    header row, and converts each ``Order``-discriminator data row into
    a :class:`~app.schemas.trade.TradeCreate`.

    After calling :meth:`parse`, the caller should invoke
    :meth:`enrich_pnl_eur` to populate ``pnl_eur`` on all closed trades,
    either from the EUR.USD rate extracted from the CSV's Forex Balances
    section, or via the Bundesbank API as fallback.

    Attributes:
        warnings: List of non-fatal warning messages collected during
            the most recent :meth:`parse` call.
        _csv_eur_usd_rate: EUR/USD rate extracted from the CSV Forex Balances
            section, or ``None`` if not present.
        _earliest_trade_date: Earliest ``opened_at`` date seen during
            :meth:`parse`, used for the Bundesbank fallback.
        _unique_trade_dates: Set of all ``opened_at`` dates, used to detect
            multi-day exports.
    """

    def __init__(self) -> None:
        """Initialise the parser with an empty warnings list."""
        self.warnings: list[str] = []
        self._csv_eur_usd_rate: Decimal | None = None
        self._earliest_trade_date: date_type | None = None
        self._unique_trade_dates: set[date_type] = set()

    def parse(self, content: bytes, filename: str) -> tuple[list[TradeCreate], list[CashTransactionCreateRequest]]:
        """Parse an IBKR Activity Statement CSV into :class:`TradeCreate` objects.

        Also extracts the ``EUR.USD`` rate from the ``Forex Balances`` section
        (if present) and records trade dates for the ``pnl_eur`` enrichment
        step.

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
        self._csv_eur_usd_rate = None
        self._earliest_trade_date = None
        self._unique_trade_dates = set()

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportParseError("IBKR file is not valid UTF-8 text.") from exc

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        # Extract EUR.USD rate from Forex Balances section.
        self._csv_eur_usd_rate = _extract_eur_usd_rate(rows)

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
                trade = self._parse_row(row)
                trades.append(trade)
                trade_date = trade.opened_at.date()
                self._unique_trade_dates.add(trade_date)
                if (
                    self._earliest_trade_date is None
                    or trade_date < self._earliest_trade_date
                ):
                    self._earliest_trade_date = trade_date
            except (ValueError, InvalidOperation, IndexError) as exc:
                msg = f"IBKR row {row_num}: skipped — {exc}"
                logger.warning(msg)
                self.warnings.append(msg)

        return trades, []

    async def enrich_pnl_eur(
        self,
        trades: list[TradeCreate],
        session: AsyncSession,
    ) -> None:
        """Populate ``pnl_eur`` on all closed trades using the EUR/USD rate.

        Lookup order:
        1. EUR.USD rate extracted from the CSV ``Forex Balances`` section.
        2. Bundesbank API (via :class:`~app.services.fx_rate_service.FxRateService`)
           for the earliest trade date, if no CSV rate is available.

        Also emits a warning when the import spans multiple calendar days and
        a single rate is applied to all trades.

        Args:
            trades: The list returned by :meth:`parse`.
            session: Active async SQLAlchemy session (used only for the
                Bundesbank fallback cache write).
        """
        # Import here to avoid circular imports at module load time.
        from app.services.fx_rate_service import FxRateService  # noqa: PLC0415

        rate = self._csv_eur_usd_rate

        if rate is None and self._earliest_trade_date is not None:
            # Fallback: fetch from Bundesbank for the earliest trade date.
            fx_service = FxRateService()
            rate = await fx_service.get_usd_to_eur(session, self._earliest_trade_date)
            if rate is None:
                msg = (
                    f"EUR/USD rate unavailable for {self._earliest_trade_date} "
                    "(Bundesbank API fallback failed). pnl_eur will be null."
                )
                logger.warning(msg)
                self.warnings.append(msg)
                return

        if rate is None:
            return

        # Multi-day warning: a single rate is used for all trades.
        if len(self._unique_trade_dates) > 1:
            self.warnings.append(_MULTI_DAY_WARNING)

        # Apply pnl_eur to all closed trades.
        for i, trade in enumerate(trades):
            if trade.pnl is not None:
                trades[i] = trade.model_copy(
                    update={"pnl_eur": trade.pnl * rate, "currency": "USD"}
                )
            else:
                trades[i] = trade.model_copy(update={"currency": "USD"})

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


def _extract_eur_usd_rate(rows: list[list[str]]) -> Decimal | None:
    """Extract the EUR.USD rate from an IBKR CSV's ``Forex Balances`` section.

    Looks for rows of the form::

        Forex Balances,Data,...,EUR.USD,...,<rate>,...

    Args:
        rows: All parsed CSV rows from the IBKR export.

    Returns:
        The EUR/USD rate as a :class:`~decimal.Decimal` if found,
        else ``None``.
    """
    for row in rows:
        if (
            len(row) > max(_COL_FB_PAIR, _COL_FB_RATE)
            and row[0].strip() == _FOREX_BALANCES_SECTION
            and len(row) > 1
            and row[1].strip() == "Data"
            and row[_COL_FB_PAIR].strip() == _EUR_USD_PAIR
        ):
            try:
                return Decimal(row[_COL_FB_RATE].strip().replace(",", ""))
            except InvalidOperation:
                logger.warning(
                    "Could not parse EUR.USD rate from Forex Balances: %r",
                    row[_COL_FB_RATE],
                )
                return None
    return None
