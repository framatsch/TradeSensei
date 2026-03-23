from __future__ import annotations

import csv
import io
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ImportParseError
from app.models.cash_transaction import CashTransactionType
from app.models.trade import AssetClass, Direction
from app.schemas.cash_transaction import CashTransactionCreateRequest
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import CorporateActionLike
from app.utils.parsers.base import BrokerParser

"""Charles Schwab trade history CSV parser."""

logger = logging.getLogger(__name__)

# ─── Schwab CSV column names ──────────────────────────────────────────────────

_COL_DATE: str = "Date"
_COL_ACTION: str = "Action"
_COL_SYMBOL: str = "Symbol"
_COL_DESCRIPTION: str = "Description"
_COL_QUANTITY: str = "Quantity"
_COL_PRICE: str = "Price"
_COL_FEES: str = "Fees & Comm"
_COL_AMOUNT: str = "Amount"

# ─── Schwab date format ───────────────────────────────────────────────────────

_SCHWAB_DATE_FORMAT: str = "%m/%d/%Y"

# ─── Processable action values ────────────────────────────────────────────────

_ACTION_BUY: str = "Buy"
_ACTION_SELL: str = "Sell"
_PROCESSABLE_ACTIONS: frozenset[str] = frozenset({_ACTION_BUY, _ACTION_SELL})


def _map_cash_transaction_type(
    action: str, amount: Decimal
) -> CashTransactionType | None:
    """Map a Schwab Action string to a CashTransactionType.

    Returns None if the action is not a cash transaction.
    """
    action_upper = action.upper()

    if action_upper in {"BUY", "SELL", "BUY TO COVER", "SELL SHORT"}:
        return None

    if "DIVIDEND" in action_upper:
        return CashTransactionType.DIVIDEND
    if "TAX" in action_upper:
        return CashTransactionType.WITHHOLDING_TAX
    if "INTEREST" in action_upper:
        return CashTransactionType.INTEREST
    if (
        "DEPOSIT" in action_upper
        or "FUNDS RECEIVED" in action_upper
        or "WIRE IN" in action_upper
    ):
        return CashTransactionType.DEPOSIT
    if (
        "WITHDRAWAL" in action_upper
        or "FUNDS PAID" in action_upper
        or "WIRE OUT" in action_upper
        or "FUNDS SENT" in action_upper
    ):
        return CashTransactionType.WITHDRAWAL
    if "FEE" in action_upper or "COMMISSION" in action_upper:
        return CashTransactionType.FEE

    # Other cash events typically have an amount
    if amount != Decimal("0"):
        return CashTransactionType.OTHER

    return None


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

    After calling :meth:`parse`, call :meth:`enrich_pnl_eur` to populate
    ``pnl_eur`` for all trades that have a ``pnl`` value.

    Attributes:
        warnings: List of non-fatal warning messages collected during
            the most recent :meth:`parse` / :meth:`enrich_pnl_eur` call.
    """

    def __init__(self) -> None:
        """Initialise the parser with an empty warnings list."""
        self.warnings: list[str] = []

    def parse(
        self,
        content: bytes,
        filename: str,
        corporate_actions: Sequence[CorporateActionLike] | None = None,  # noqa: ARG002
        seed_open_lots: Sequence[object] | None = None,  # noqa: ARG002
    ) -> tuple[list[TradeCreate], list[CashTransactionCreateRequest]]:
        """Parse a Schwab trade history CSV into :class:`TradeCreate` objects.

        Sets ``currency="USD"`` on every parsed trade.  ``pnl_eur`` is not
        populated here — call :meth:`enrich_pnl_eur` afterwards.

        Args:
            content: Raw CSV file bytes.
            filename: Original filename (present for interface compatibility;
                Schwab exports are always CSV).
            corporate_actions: Accepted for interface compatibility; not used
                by this parser.

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
        cash_transactions: list[CashTransactionCreateRequest] = []

        for row_num, row in enumerate(reader, start=2):  # 1-based; row 1 is the header
            try:
                result = self._parse_row(row)
                if isinstance(result, TradeCreate):
                    trades.append(result)
                elif isinstance(result, CashTransactionCreateRequest):
                    cash_transactions.append(result)
            except (ValueError, InvalidOperation, KeyError) as exc:
                msg = f"Schwab row {row_num}: skipped — {exc}"
                logger.warning(msg)
                self.warnings.append(msg)

        return trades, cash_transactions

    async def enrich_pnl_eur(
        self,
        trades: list[TradeCreate],
        session: AsyncSession,
    ) -> None:
        """Populate ``pnl_eur`` on closed trades using per-date Bundesbank rates.

        For each unique ``opened_at`` date, fetches the EUR/USD rate via
        :class:`~app.services.fx_rate_service.FxRateService` (DB cache first,
        then Bundesbank API).  Applies ``pnl_eur = pnl * rate`` for all
        trades with a non-null ``pnl``.

        Trades without ``pnl`` (open positions) are left unchanged.

        A warning is added to :attr:`warnings` for any date where the rate
        cannot be retrieved.

        Args:
            trades: The list returned by :meth:`parse`.
            session: Active async SQLAlchemy session (for rate caching).
        """
        # Import here to avoid circular imports at module load time.
        from app.services.fx_rate_service import FxRateService  # noqa: PLC0415

        fx_service = FxRateService()

        # Build a set of unique dates for trades that have pnl.
        dates_needed = {
            trade.opened_at.date() for trade in trades if trade.pnl is not None
        }

        # Fetch rates for all needed dates up front.
        rates: dict[object, Decimal | None] = {}
        for trade_date in dates_needed:
            rate = await fx_service.get_usd_to_eur(session, trade_date)
            if rate is None:
                msg = (
                    f"EUR/USD rate unavailable for {trade_date} "
                    "(Bundesbank API fallback failed). "
                    "pnl_eur will be null for trades on this date."
                )
                logger.warning(msg)
                self.warnings.append(msg)
            rates[trade_date] = rate

        # Apply pnl_eur to each trade.
        for i, trade in enumerate(trades):
            if trade.pnl is not None:
                rate = rates.get(trade.opened_at.date())
                if rate is not None:
                    trades[i] = trade.model_copy(update={"pnl_eur": trade.pnl * rate})

    def _parse_row(
        self, row: dict[str, str]
    ) -> TradeCreate | CashTransactionCreateRequest | None:
        """Convert a single Schwab CSV row dict into a Pydantic schema.

        Sets ``currency="USD"`` on every trade and cash transaction.

        Args:
            row: Dictionary of column name → raw string value.

        Returns:
            A validated :class:`~app.schemas.trade.TradeCreate`,
            cash transaction request, or None.

        Raises:
            ValueError: If a required field is empty or invalid.
            KeyError: If an expected column is absent.
            decimal.InvalidOperation: If a numeric field cannot be parsed.
        """
        action = row[_COL_ACTION].strip()

        # Check if it's a cash transaction
        amount_raw = row.get(_COL_AMOUNT, "").strip()
        amount = _parse_decimal(amount_raw) if amount_raw else Decimal("0")

        cash_tx_type = _map_cash_transaction_type(action, amount)
        if cash_tx_type is not None:
            if amount == Decimal("0"):
                return None  # Skip cash transactions with zero amount

            date = _parse_schwab_date(row[_COL_DATE])
            symbol = row.get(_COL_SYMBOL, "").strip() or None
            description = row.get(_COL_DESCRIPTION, "").strip() or action

            return CashTransactionCreateRequest(
                date=date,
                type=cash_tx_type,
                symbol=symbol,
                amount=amount,
                currency="USD",
                description=description,
            )

        if action not in _PROCESSABLE_ACTIONS:
            return None

        symbol = row[_COL_SYMBOL].strip()
        if not symbol:
            raise ValueError("Symbol column is empty.")

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
            currency="USD",
        )
