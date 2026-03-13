"""Interactive Brokers Flex Query XML parser.

Parses IBKR Flex Query XML responses (Activity Flex Query and Trade
Confirmation format) and maps each element to a
:class:`~app.schemas.trade.TradeCreate`.

Two element types are supported:

- ``<Trade>`` — from Activity Flex Queries
- ``<Execution>`` — from Trade Confirmation queries

Both share the same output type (:class:`~app.schemas.trade.TradeCreate`)
and the same error-handling strategy: elements that fail to parse are
skipped with a warning rather than aborting the whole import.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.core.exceptions import ImportParseError
from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate
from app.utils.parsers.base import BrokerParser

logger = logging.getLogger(__name__)

# ─── Asset class mapping ──────────────────────────────────────────────────────

_ASSET_CLASS_MAP: dict[str, AssetClass] = {
    "STK": AssetClass.EQUITY,
    "OPT": AssetClass.OPTION,
    "FUT": AssetClass.FUTURE,
    "FOP": AssetClass.FUTURE,  # Futures options → FUTURE
    "CASH": AssetClass.FOREX,
    "FXCFD": AssetClass.FOREX,
    "CRYPTO": AssetClass.CRYPTO,
}

# ─── Timestamp offset for closed trades ──────────────────────────────────────
# IBKR XML carries a single timestamp per row.  TradeCreate requires
# closed_at > opened_at, so we add 1 second when a trade is recorded as
# closed (realized P&L ≠ 0).

_CLOSED_AT_OFFSET: timedelta = timedelta(seconds=1)


def _map_asset_class(asset_category: str) -> AssetClass:
    """Map an IBKR ``assetCategory`` attribute to an :class:`AssetClass`.

    Args:
        asset_category: Raw ``assetCategory`` string from the XML element
            (e.g. ``"STK"``, ``"OPT"``).

    Returns:
        The matching :class:`~app.models.trade.AssetClass`.  Falls back to
        :attr:`~app.models.trade.AssetClass.EQUITY` for unknown values.
    """
    return _ASSET_CLASS_MAP.get(asset_category.upper().strip(), AssetClass.EQUITY)


def _parse_ibkr_datetime(date_str: str, datetime_str: str) -> datetime:
    """Parse IBKR date / datetime fields into a timezone-aware UTC datetime.

    IBKR Flex Query uses two formats:

    - Combined: ``"YYYYMMDD;HHMMSS"`` in the ``dateTime`` attribute.
    - Date-only: ``"YYYYMMDD"`` in the ``tradeDate`` attribute.

    Args:
        date_str: Date string in ``YYYYMMDD`` format.
        datetime_str: Combined datetime string in ``YYYYMMDD;HHMMSS`` format,
            or an empty string if not available.

    Returns:
        A timezone-aware :class:`~datetime.datetime` in UTC.

    Raises:
        ValueError: If neither string can be parsed.
    """
    if ";" in datetime_str:
        dt = datetime.strptime(datetime_str, "%Y%m%d;%H%M%S")
    else:
        dt = datetime.strptime(date_str, "%Y%m%d")
    return dt.replace(tzinfo=UTC)


def _parse_execution_datetime(exec_date: str, exec_time: str) -> datetime:
    """Parse execution date/time fields from a Trade Confirmation element.

    Args:
        exec_date: Date string in ``YYYYMMDD`` format.
        exec_time: Time string in ``HHMMSS`` format, or empty string.

    Returns:
        A timezone-aware :class:`~datetime.datetime` in UTC.

    Raises:
        ValueError: If the strings cannot be parsed.
    """
    if exec_time:
        dt = datetime.strptime(f"{exec_date};{exec_time}", "%Y%m%d;%H%M%S")
    else:
        dt = datetime.strptime(exec_date, "%Y%m%d")
    return dt.replace(tzinfo=UTC)


def _safe_decimal(value: str | None, default: Decimal = Decimal("0")) -> Decimal:
    """Parse a string to :class:`~decimal.Decimal`, returning ``default`` on failure.

    Args:
        value: Raw string value, may be ``None``.
        default: Value to return when ``value`` is ``None`` or unparseable.

    Returns:
        Parsed :class:`~decimal.Decimal` or ``default``.
    """
    if value is None:
        return default
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return default


class IBKRXMLParser(BrokerParser):
    """Parser for IBKR Flex Query XML responses.

    Supports both Activity Flex Query (``<Trade>`` elements) and
    Trade Confirmation (``<Execution>`` elements).  Elements that fail
    to parse are skipped; the warning is stored in :attr:`warnings`.

    Attributes:
        warnings: Non-fatal warning messages from the most recent
            :meth:`parse` call.
    """

    def __init__(self) -> None:
        """Initialise the parser with an empty warnings list."""
        self.warnings: list[str] = []

    def parse(self, content: bytes, filename: str) -> list[TradeCreate]:
        """Parse an IBKR Flex Query XML response into :class:`TradeCreate` objects.

        Args:
            content: Raw XML bytes from the Flex API or a file upload.
            filename: Original filename (present for interface compatibility).

        Returns:
            A list of :class:`~app.schemas.trade.TradeCreate` instances.

        Raises:
            ImportParseError: If the bytes cannot be decoded or the XML
                cannot be parsed at the document level.
        """
        self.warnings = []
        try:
            xml_string = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ImportParseError("IBKR Flex XML file is not valid UTF-8.") from exc

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as exc:
            raise ImportParseError(f"Invalid IBKR Flex XML: {exc}") from exc

        trades: list[TradeCreate] = []

        # Activity Flex Query: <Trade> elements
        for idx, elem in enumerate(root.findall(".//Trade"), start=1):
            result = self._parse_trade_element(elem, idx)
            if result is not None:
                trades.append(result)

        # Trade Confirmation: <Execution> elements
        for idx, elem in enumerate(root.findall(".//Execution"), start=1):
            result = self._parse_execution_element(elem, idx)
            if result is not None:
                trades.append(result)

        logger.info("Parsed %d trades from IBKR Flex XML.", len(trades))
        return trades

    def _parse_trade_element(self, elem: ET.Element, idx: int) -> TradeCreate | None:
        """Parse a single ``<Trade>`` element from an Activity Flex Query.

        Args:
            elem: The ``<Trade>`` XML element.
            idx: 1-based element index for warning messages.

        Returns:
            A :class:`~app.schemas.trade.TradeCreate` or ``None`` if the
            element was skipped due to a non-fatal error.
        """
        try:
            asset_category = elem.get("assetCategory", "").upper()
            symbol = elem.get("symbol", "").strip().upper()

            if not symbol:
                self.warnings.append(
                    f"<Trade> element {idx}: skipped — missing symbol attribute."
                )
                return None

            asset_class = _map_asset_class(asset_category)

            trade_date_str = elem.get("tradeDate", "")
            datetime_str = elem.get("dateTime", "")

            if not trade_date_str:
                self.warnings.append(
                    f"<Trade> element {idx} ({symbol}): skipped — missing tradeDate."
                )
                return None

            opened_at = _parse_ibkr_datetime(trade_date_str, datetime_str)

            quantity_raw = _safe_decimal(elem.get("quantity"))
            if quantity_raw == Decimal("0"):
                self.warnings.append(
                    f"<Trade> element {idx} ({symbol}): skipped — quantity is zero."
                )
                return None

            direction = Direction.LONG if quantity_raw > 0 else Direction.SHORT
            quantity = abs(quantity_raw)

            # Price with 3-tier fallback (same logic as the original xml_parser.py)
            multiplier_raw = int(elem.get("multiplier", "1") or "1")
            multiplier = multiplier_raw if multiplier_raw > 0 else 1

            price = _safe_decimal(elem.get("tradePrice"))

            if price == Decimal("0"):
                trade_money = _safe_decimal(elem.get("tradeMoney"))
                if trade_money != Decimal("0") and quantity != Decimal("0"):
                    price = abs(trade_money) / quantity / Decimal(multiplier)

            if price == Decimal("0"):
                cost = _safe_decimal(elem.get("cost"))
                if cost != Decimal("0") and quantity != Decimal("0"):
                    price = abs(cost) / quantity / Decimal(multiplier)

            if price <= Decimal("0"):
                self.warnings.append(
                    f"<Trade> element {idx} ({symbol}): skipped — "
                    "could not determine a positive entry price."
                )
                return None

            commission = abs(_safe_decimal(elem.get("commission")))
            pnl_raw = _safe_decimal(elem.get("fifoPnlRealized"))
            pnl: Decimal | None = pnl_raw if pnl_raw != Decimal("0") else None

            closed_at = opened_at + _CLOSED_AT_OFFSET if pnl is not None else None

            return TradeCreate(
                symbol=symbol,
                direction=direction,
                asset_class=asset_class,
                quantity=quantity,
                entry_price=price,
                commission=commission,
                pnl=pnl,
                opened_at=opened_at,
                closed_at=closed_at,
            )
        except (ValueError, InvalidOperation, OverflowError) as exc:
            msg = f"<Trade> element {idx}: skipped — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None

    def _parse_execution_element(
        self, elem: ET.Element, idx: int
    ) -> TradeCreate | None:
        """Parse a single ``<Execution>`` element from a Trade Confirmation query.

        Args:
            elem: The ``<Execution>`` XML element.
            idx: 1-based element index for warning messages.

        Returns:
            A :class:`~app.schemas.trade.TradeCreate` or ``None`` if the
            element was skipped due to a non-fatal error.
        """
        try:
            asset_category = elem.get("assetCategory", "").upper()
            symbol = elem.get("symbol", "").strip().upper()

            if not symbol:
                self.warnings.append(
                    f"<Execution> element {idx}: skipped — missing symbol attribute."
                )
                return None

            asset_class = _map_asset_class(asset_category)

            exec_date = elem.get("execDate", "")
            exec_time = elem.get("execTime", "")

            if not exec_date:
                self.warnings.append(
                    f"<Execution> element {idx} ({symbol}): skipped — missing execDate."
                )
                return None

            opened_at = _parse_execution_datetime(exec_date, exec_time)

            quantity_raw = _safe_decimal(elem.get("quantity"))
            if quantity_raw == Decimal("0"):
                self.warnings.append(
                    f"<Execution> element {idx} ({symbol}): skipped — quantity is zero."
                )
                return None

            direction = Direction.LONG if quantity_raw > 0 else Direction.SHORT
            quantity = abs(quantity_raw)

            price = _safe_decimal(elem.get("price"))
            if price <= Decimal("0"):
                self.warnings.append(
                    f"<Execution> element {idx} ({symbol}): skipped — "
                    "entry price is zero or negative."
                )
                return None

            commission = abs(_safe_decimal(elem.get("commission")))

            return TradeCreate(
                symbol=symbol,
                direction=direction,
                asset_class=asset_class,
                quantity=quantity,
                entry_price=price,
                commission=commission,
                opened_at=opened_at,
            )
        except (ValueError, InvalidOperation, OverflowError) as exc:
            msg = f"<Execution> element {idx}: skipped — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None
