# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

""" "Interactive Brokers Flex Query XML parser.

Parses IBKR Flex Query XML responses (Activity Flex Query and Trade
Confirmation format) and maps each element to a
:class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`.

Two element types are supported:

- ``<Trade>`` — from Activity Flex Queries
- ``<Execution>`` — from Trade Confirmation queries

Both share the same output type
(:class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`)
and the same error-handling strategy: elements that fail to parse are
skipped with a warning rather than aborting the whole import.

The :meth:`IBKRXMLParser.parse_raw` method returns raw per-execution records
with no FIFO aggregation.  The legacy :meth:`IBKRXMLParser.parse` method
converts those raw records into :class:`~app.schemas.trade.TradeCreate` objects
and runs the FIFO aggregator for backward-compatibility with the existing import
pipeline; it will be removed once the import service is fully migrated.
"""

import logging
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.core.constants import NUMERIC_SCALE
from app.core.exceptions import ImportParseError
from app.models.trade import AssetClass, Direction
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.schemas.trade import TradeCreate
from app.utils.occ import extract_occ_underlying, parse_occ_option
from app.utils.parsers.aggregator import (
    CorporateActionLike,
    SeedLotLike,
    aggregate_executions_fifo,
)
from app.utils.parsers.base import BrokerParser

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────────

_BROKER_TYPE: str = "ibkr"


def _extract_occ_underlying(symbol: str) -> str:
    """Return the underlying ticker for an OCC-format option symbol.

    IBKR stores option symbols in OCC format:
      ``<UNDERLYING><YYMMDD><C|P><8-digit-strike>``
    where the underlying is left-padded with spaces to at least 6 chars in the
    standard format but may be longer for non-standard underlyings.

    For any symbol long enough to contain the 15-char numeric suffix and whose
    suffix passes basic validation (all-digit expiry, C/P type char, all-digit
    strike), the underlying is everything before that suffix, stripped of spaces.

    Non-option symbols (too short, or suffix fails validation) are returned as-is.
    """
    return extract_occ_underlying(symbol)


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
    dt = datetime.strptime(datetime_str, "%Y%m%d;%H%M%S") if ";" in datetime_str else datetime.strptime(date_str, "%Y%m%d")
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
    dt = datetime.strptime(f"{exec_date};{exec_time}", "%Y%m%d;%H%M%S") if exec_time else datetime.strptime(exec_date, "%Y%m%d")
    return dt.replace(tzinfo=UTC)


def _safe_decimal(value: str | None, default: Decimal = Decimal("0")) -> Decimal:
    """Parse a string to :class:`~decimal.Decimal`, returning ``default`` on failure.

    Args:
        value: Raw string value, may be ``None``.
        default: Value to return when ``value`` is ``None`` or unparseable.

    Returns:
        Parsed :class:`~decimal.Decimal` or ``default``, rounded to NUMERIC_SCALE.
    """
    if value is None:
        return default
    try:
        return Decimal(value.strip()).quantize(Decimal(f"1e-{NUMERIC_SCALE}"))
    except InvalidOperation:
        return default


def _derive_open_close(open_close_indicator: str) -> str | None:
    """Derive the per-leg open/close indicator from IBKR ``openCloseIndicator``.

    IBKR reports ``openCloseIndicator`` as ``"O"``, ``"C"``, or a mixed value
    (``"C;O"`` / ``"O;C"``) for a position flip.

    Args:
        open_close_indicator: Upper-cased ``openCloseIndicator`` attribute value.

    Returns:
        ``"O"`` when the indicator contains ``O`` but not ``C``; ``"C"`` when it
        contains ``C`` but not ``O``; otherwise ``None`` (mixed or empty).
    """
    has_open = "O" in open_close_indicator
    has_close = "C" in open_close_indicator
    if has_open and not has_close:
        return "O"
    if has_close and not has_open:
        return "C"
    return None


class IBKRXMLParser(BrokerParser):
    """Parser for IBKR Flex Query XML responses.

    Supports both Activity Flex Query (``<Trade>`` elements) and
    Trade Confirmation (``<Execution>`` elements).  Elements that fail
    to parse are skipped; the warning is stored in :attr:`warnings`.

    The primary entry point for the new raw-data pipeline is
    :meth:`parse_raw`, which returns one
    :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
    per execution with **no** FIFO aggregation.  The legacy :meth:`parse`
    method (which returns aggregated :class:`~app.schemas.trade.TradeCreate`
    objects) remains for backward compatibility.

    Attributes:
        warnings: Non-fatal warning messages from the most recent
            :meth:`parse` or :meth:`parse_raw` call.
    """

    def __init__(self) -> None:
        """Initialise the parser with an empty warnings list."""
        self.warnings: list[str] = []

    # ─── Raw parsing ─────────────────────────────────────────────────────────

    def parse_raw(
        self,
        content: bytes,
        filename: str,
    ) -> tuple[
        list[BrokerRawTransactionCreate],
        list[CorporateActionCreateRequest],
    ]:
        """Parse an IBKR Flex Query XML and return one raw record per execution.

        No FIFO aggregation is performed.  Each ``<Trade>`` or ``<Execution>``
        element that represents a tradeable instrument (non-CASH asset category)
        is converted to a
        :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
        record.

        The ``id`` field of each record is set to
        ``"ibkr:{transactionID}"`` when the attribute is present, or falls back
        to a deterministic composite key (``"ibkr:{symbol}:{datetime}:{qty}"``)
        for elements that lack a ``transactionID``.

        Args:
            content: Raw XML bytes from the Flex API or a file upload.
            filename: Original filename (present for interface compatibility).

        Returns:
            A tuple of raw transaction records and corporate actions.

        Raises:
            ImportParseError: If the bytes cannot be decoded or the XML
                cannot be parsed at the document level.
        """
        self.warnings = []
        root = self._parse_xml(content)

        raw_transactions: list[BrokerRawTransactionCreate] = []
        corporate_actions: list[CorporateActionCreateRequest] = []

        # Extract corporate actions (type="RS" or "FS")
        ca_elements = root.findall(".//CorporateAction")
        grouped_ca: dict[str, list[ET.Element]] = {}
        for elem in ca_elements:
            action_id = elem.get("actionID")
            action_type = elem.get("type")
            if not action_id or action_type not in ("RS", "FS"):
                continue
            grouped_ca.setdefault(action_id, []).append(elem)

        for _action_id, elems in grouped_ca.items():
            if len(elems) != 2:
                continue
            try:
                qty1 = Decimal(elems[0].get("quantity", "0"))
                qty2 = Decimal(elems[1].get("quantity", "0"))
            except InvalidOperation:
                continue

            if qty1 < 0 and qty2 > 0:
                old_elem, new_elem = elems[0], elems[1]
            elif qty2 < 0 and qty1 > 0:
                old_elem, new_elem = elems[1], elems[0]
            else:
                continue

            try:
                ratio = Decimal(new_elem.get("quantity", "0")) / abs(Decimal(old_elem.get("quantity", "0")))
                dt_str = new_elem.get("dateTime", "")
                if ";" in dt_str:
                    dt_str = dt_str.split(";")[0]
                ca_date = datetime.strptime(dt_str, "%Y%m%d").date()
                ca = CorporateActionCreateRequest(
                    symbol=new_elem.get("symbol", ""),
                    date=ca_date,
                    ratio=ratio,
                    old_conid=old_elem.get("conid", ""),
                    new_conid=new_elem.get("conid", ""),
                )
                corporate_actions.append(ca)
            except (ValueError, InvalidOperation):
                pass

        # Activity Flex Query: <Trade> elements
        for idx, elem in enumerate(root.findall(".//Trade"), start=1):
            result = self._parse_trade_element_raw(elem, idx)
            if isinstance(result, BrokerRawTransactionCreate):
                raw_transactions.append(result)

        # Trade Confirmation: <Execution> elements
        for idx, elem in enumerate(root.findall(".//Execution"), start=1):
            result = self._parse_execution_element_raw(elem, idx)
            if result is not None:
                raw_transactions.append(result)

        logger.info(
            "parse_raw: extracted %d raw transactions from IBKR Flex XML.",
            len(raw_transactions),
        )
        return raw_transactions, corporate_actions

    # ─── Legacy aggregated parsing ────────────────────────────────────────────

    def parse(
        self,
        content: bytes,
        filename: str,
        corporate_actions: Sequence[CorporateActionLike] | None = None,
        seed_open_lots: Sequence[SeedLotLike] | None = None,
        seed_orphaned_lots: Sequence[SeedLotLike] | None = None,
    ) -> tuple[list[TradeCreate], list[object]]:
        """Parse an IBKR Flex Query XML response.

         Args:
             content: Raw XML bytes from the Flex API or a file upload.
             filename: Original filename (present for interface compatibility).
             corporate_actions: Optional list of corporate actions to pass to
                 the aggregator so that split adjustments are applied during
                 execution matching.
             seed_open_lots: Optional sequence of existing open DB trades to
                 pre-populate the FIFO aggregator queue so that cross-period
                 imports correctly close positions opened in a prior import.
             seed_orphaned_lots: Optional sequence of existing orphaned DB trades
                 (closed trades with unknown entry, entry_price=0.001) so that
                 opening executions in this file can be matched against them.

        Returns:
            A tuple of parsed trades and cash transactions.

        Raises:
            ImportParseError: If the bytes cannot be decoded or the XML
                cannot be parsed at the document level.
        """
        self.warnings = []
        root = self._parse_xml(content)

        trades: list[TradeCreate] = []

        # Activity Flex Query: <Trade> elements
        for idx, elem in enumerate(root.findall(".//Trade"), start=1):
            result = self._parse_trade_element(elem, idx)
            if isinstance(result, TradeCreate):
                trades.append(result)

        # Trade Confirmation: <Execution> elements
        for idx, elem in enumerate(root.findall(".//Execution"), start=1):
            result = self._parse_execution_element(elem, idx)
            if isinstance(result, TradeCreate):
                trades.append(result)

        # Extract Open Positions for final validation
        open_positions_conids = set()
        for elem in root.findall(".//OpenPosition"):
            conid = elem.get("conid")
            if conid:
                open_positions_conids.add(conid)

        # Build a set of conids that are "acceptable as open" — includes both the
        # conids directly listed in <OpenPositions> AND any new conids that are the
        # result of a corporate-action remap of an old conid that was listed.  This
        # prevents false conflict flags when a reverse split changes the conid: the
        # 2023 XML lists the pre-split conid in <OpenPositions>, but after applying
        # the corporate action the aggregated lot carries the post-split conid.
        acceptable_open_conids = set(open_positions_conids)
        if corporate_actions:
            for ca in corporate_actions:
                if ca.old_conid is not None and ca.new_conid is not None and ca.old_conid in open_positions_conids:
                    acceptable_open_conids.add(ca.new_conid)

        # Group executions into round-trip trades.
        aggregated_trades = aggregate_executions_fifo(
            trades,
            corporate_actions=corporate_actions if corporate_actions else None,
            seed_open_lots=seed_open_lots if seed_open_lots else None,
            seed_orphaned_lots=seed_orphaned_lots if seed_orphaned_lots else None,
        )

        logger.info(
            "Parsed %d executions, aggregated into %d trades from IBKR Flex XML.",
            len(trades),
            len(aggregated_trades),
        )
        return aggregated_trades, []

    # ─── XML helpers ──────────────────────────────────────────────────────────

    def _parse_xml(self, content: bytes) -> ET.Element:
        """Decode and parse XML bytes into an ElementTree root.

        Args:
            content: Raw XML bytes.

        Returns:
            The root :class:`~xml.etree.ElementTree.Element`.

        Raises:
            ImportParseError: On UTF-8 decode failure or XML parse error.
        """
        try:
            xml_string = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ImportParseError("IBKR Flex XML file is not valid UTF-8.") from exc
        try:
            return ET.fromstring(xml_string)
        except ET.ParseError as exc:
            raise ImportParseError(f"Invalid IBKR Flex XML: {exc}") from exc

    @staticmethod
    def _build_raw_id(
        elem: ET.Element,
        symbol: str,
        executed_at: datetime,
        quantity: Decimal,
    ) -> str:
        """Build a composite broker execution ID for a raw transaction.

        Prefers the ``transactionID`` attribute when present.  Falls back to a
        deterministic composite key based on symbol, timestamp, and quantity.

        Args:
            elem: The XML element being parsed.
            symbol: Ticker symbol (already normalised to uppercase).
            executed_at: Parsed execution timestamp.
            quantity: Absolute execution quantity.

        Returns:
            A string of the form ``"ibkr:{id}"`` suitable for use as the
            ``BrokerRawTransaction.id`` primary key.
        """
        tx_id = (elem.get("transactionID") or "").strip()
        if tx_id:
            return f"{_BROKER_TYPE}:{tx_id}"
        # Fallback: deterministic composite key
        ts = executed_at.strftime("%Y%m%d%H%M%S")
        return f"{_BROKER_TYPE}:{symbol}:{ts}:{quantity}"

    # ─── Raw element parsers ──────────────────────────────────────────────────

    def _parse_trade_element_raw(self, elem: ET.Element, idx: int) -> BrokerRawTransactionCreate | None:
        """Parse a single ``<Trade>`` element into a raw transaction record.

        Args:
            elem: The ``<Trade>`` XML element.
            idx: 1-based element index for warning messages.

        Returns:
            A :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
            or ``None`` if the element was skipped.
        """
        try:
            asset_category = elem.get("assetCategory", "").upper()
            symbol = elem.get("symbol", "").strip().upper()
            conid = elem.get("conid", "").strip() or None

            if not symbol:
                self.warnings.append(f"<Trade> element {idx}: skipped — missing symbol attribute.")
                return None

            trade_date_str = elem.get("tradeDate", "")
            datetime_str = elem.get("dateTime", "")

            if not trade_date_str:
                self.warnings.append(f"<Trade> element {idx} ({symbol}): skipped — missing tradeDate.")
                return None

            executed_at = _parse_ibkr_datetime(trade_date_str, datetime_str)

            # CASH asset category → FX conversion; skip (no longer tracked)
            if asset_category == "CASH":
                return None

            asset_class = _map_asset_class(asset_category)
            strike: Decimal | None = None
            expiry = None
            option_type: str | None = None
            # For options, use the underlying ticker as the trade symbol.
            # The full OCC contract string stays in raw_data for reference.
            if asset_class == AssetClass.OPTION:
                strike, expiry, option_type = parse_occ_option(symbol)
                symbol = _extract_occ_underlying(symbol)

            quantity_raw = _safe_decimal(elem.get("quantity"))
            if quantity_raw == Decimal("0"):
                self.warnings.append(f"<Trade> element {idx} ({symbol}): skipped — quantity is zero.")
                return None

            direction = Direction.LONG if quantity_raw > 0 else Direction.SHORT
            quantity = abs(quantity_raw)

            multiplier_raw = int(elem.get("multiplier", "1") or "1")
            multiplier = multiplier_raw if multiplier_raw > 0 else 1

            price = _safe_decimal(elem.get("tradePrice"))

            if price == Decimal("0") and elem.get("transactionType") != "BookTrade":
                trade_money = _safe_decimal(elem.get("tradeMoney"))
                if trade_money != Decimal("0") and quantity != Decimal("0"):
                    price = abs(trade_money) / quantity / Decimal(multiplier)

            if price == Decimal("0") and elem.get("transactionType") != "BookTrade":
                cost = _safe_decimal(elem.get("cost"))
                if cost != Decimal("0") and quantity != Decimal("0"):
                    price = abs(cost) / quantity / Decimal(multiplier)

            if price < Decimal("0"):
                self.warnings.append(f"<Trade> element {idx} ({symbol}): skipped — could not determine a non-negative entry price.")
                return None

            ib_comm = abs(_safe_decimal(elem.get("ibCommission")))
            gen_comm = abs(_safe_decimal(elem.get("commission")))
            commission = max(ib_comm, gen_comm)
            pnl_raw = _safe_decimal(elem.get("fifoPnlRealized"))
            open_close_raw = (elem.get("openCloseIndicator") or "").upper()
            # A closing execution (openCloseIndicator contains "C" but not "O") with
            # fifoPnlRealized=0 is a genuine breakeven close, not an opening.
            # Preserve pnl=Decimal("0") so the FIFO aggregator treats it as a closing
            # leg rather than an opening leg.
            is_pure_close = "C" in open_close_raw and "O" not in open_close_raw
            pnl: Decimal | None = pnl_raw if (pnl_raw != Decimal("0") or is_pure_close) else None
            currency = (elem.get("currency") or "").upper().strip() or "USD"
            open_close = _derive_open_close(open_close_raw)

            raw_id = self._build_raw_id(elem, symbol, executed_at, quantity)

            return BrokerRawTransactionCreate(
                id=raw_id,
                broker_type=_BROKER_TYPE,
                symbol=symbol,
                conid=conid,
                asset_class=asset_class,
                direction=direction,
                quantity=quantity,
                price=price,
                commission=commission,
                executed_at=executed_at,
                pnl=pnl,
                currency=currency,
                multiplier=multiplier,
                open_close=open_close,
                strike=strike,
                expiry=expiry,
                option_type=option_type,
                raw_data=dict(elem.attrib),
            )
        except (ValueError, InvalidOperation, OverflowError) as exc:
            msg = f"<Trade> element {idx}: skipped — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None
        except Exception as exc:
            # Catch Pydantic ValidationError or other unexpected errors per-row
            msg = f"<Trade> element {idx}: skipped due to validation error — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None

    def _parse_execution_element_raw(self, elem: ET.Element, idx: int) -> BrokerRawTransactionCreate | None:
        """Parse a single ``<Execution>`` element into a raw transaction record.

        Args:
            elem: The ``<Execution>`` XML element.
            idx: 1-based element index for warning messages.

        Returns:
            A :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
            or ``None`` if the element was skipped due to a non-fatal error.
        """
        try:
            asset_category = elem.get("assetCategory", "").upper()
            symbol = elem.get("symbol", "").strip().upper()
            conid = elem.get("conid", "").strip() or None

            if not symbol:
                self.warnings.append(f"<Execution> element {idx}: skipped — missing symbol attribute.")
                return None

            asset_class = _map_asset_class(asset_category)
            strike: Decimal | None = None
            expiry = None
            option_type: str | None = None
            # For options, use the underlying ticker as the trade symbol.
            # The full OCC contract string stays in raw_data for reference.
            if asset_class == AssetClass.OPTION:
                strike, expiry, option_type = parse_occ_option(symbol)
                symbol = _extract_occ_underlying(symbol)

            exec_date = elem.get("execDate", "")
            exec_time = elem.get("execTime", "")

            if not exec_date:
                self.warnings.append(f"<Execution> element {idx} ({symbol}): skipped — missing execDate.")
                return None

            executed_at = _parse_execution_datetime(exec_date, exec_time)

            quantity_raw = _safe_decimal(elem.get("quantity"))
            if quantity_raw == Decimal("0"):
                self.warnings.append(f"<Execution> element {idx} ({symbol}): skipped — quantity is zero.")
                return None

            direction = Direction.LONG if quantity_raw > 0 else Direction.SHORT
            quantity = abs(quantity_raw)

            price = _safe_decimal(elem.get("price"))
            if price < Decimal("0"):
                self.warnings.append(f"<Execution> element {idx} ({symbol}): skipped — entry price is negative.")
                return None

            ib_comm = abs(_safe_decimal(elem.get("ibCommission")))
            gen_comm = abs(_safe_decimal(elem.get("commission")))
            commission = max(ib_comm, gen_comm)
            currency = (elem.get("currency") or "").upper().strip() or "USD"
            open_close = _derive_open_close((elem.get("openCloseIndicator") or "").upper())

            raw_id = self._build_raw_id(elem, symbol, executed_at, quantity)

            return BrokerRawTransactionCreate(
                id=raw_id,
                broker_type=_BROKER_TYPE,
                symbol=symbol,
                conid=conid,
                asset_class=asset_class,
                direction=direction,
                quantity=quantity,
                price=price,
                commission=commission,
                executed_at=executed_at,
                currency=currency,
                open_close=open_close,
                strike=strike,
                expiry=expiry,
                option_type=option_type,
                raw_data=dict(elem.attrib),
            )
        except (ValueError, InvalidOperation, OverflowError) as exc:
            msg = f"<Execution> element {idx}: skipped — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None
        except Exception as exc:
            msg = f"<Execution> element {idx}: skipped due to validation error — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None

    # ─── Legacy TradeCreate element parsers ───────────────────────────────────

    def _parse_trade_element(self, elem: ET.Element, idx: int) -> TradeCreate | None:
        """Parse a single ``<Trade>`` element from an Activity Flex Query.

        Args:
            elem: The ``<Trade>`` XML element.
            idx: 1-based element index for warning messages.

        Returns:
            A :class:`~app.schemas.trade.TradeCreate` or ``None`` if the element
            was skipped.
        """
        try:
            asset_category = elem.get("assetCategory", "").upper()
            symbol = elem.get("symbol", "").strip().upper()
            conid = elem.get("conid", "").strip() or None

            if not symbol:
                self.warnings.append(f"<Trade> element {idx}: skipped — missing symbol attribute.")
                return None

            trade_date_str = elem.get("tradeDate", "")
            datetime_str = elem.get("dateTime", "")

            if not trade_date_str:
                self.warnings.append(f"<Trade> element {idx} ({symbol}): skipped — missing tradeDate.")
                return None

            opened_at = _parse_ibkr_datetime(trade_date_str, datetime_str)

            # Filter out <Trade assetCategory="CASH"> (FX conversions)
            if asset_category == "CASH":
                return None

            asset_class = _map_asset_class(asset_category)
            # For options, use the underlying ticker as the trade symbol.
            # The full OCC contract string stays in raw_data for reference.
            if asset_class == AssetClass.OPTION:
                symbol = _extract_occ_underlying(symbol)

            quantity_raw = _safe_decimal(elem.get("quantity"))
            if quantity_raw == Decimal("0"):
                self.warnings.append(f"<Trade> element {idx} ({symbol}): skipped — quantity is zero.")
                return None

            direction = Direction.LONG if quantity_raw > 0 else Direction.SHORT
            quantity = abs(quantity_raw)

            # Price with 3-tier fallback (same logic as the original xml_parser.py)
            multiplier_raw = int(elem.get("multiplier", "1") or "1")
            multiplier = multiplier_raw if multiplier_raw > 0 else 1

            price = _safe_decimal(elem.get("tradePrice"))

            if price == Decimal("0") and elem.get("transactionType") != "BookTrade":
                trade_money = _safe_decimal(elem.get("tradeMoney"))
                if trade_money != Decimal("0") and quantity != Decimal("0"):
                    price = abs(trade_money) / quantity / Decimal(multiplier)

            if price == Decimal("0") and elem.get("transactionType") != "BookTrade":
                cost = _safe_decimal(elem.get("cost"))
                if cost != Decimal("0") and quantity != Decimal("0"):
                    price = abs(cost) / quantity / Decimal(multiplier)

            if price < Decimal("0"):
                self.warnings.append(f"<Trade> element {idx} ({symbol}): skipped — could not determine a non-negative entry price.")
                return None

            ib_comm = abs(_safe_decimal(elem.get("ibCommission")))
            gen_comm = abs(_safe_decimal(elem.get("commission")))
            commission = max(ib_comm, gen_comm)
            pnl_raw = _safe_decimal(elem.get("fifoPnlRealized"))

            open_close = (elem.get("openCloseIndicator") or "").upper()
            is_mixed_execution = "C;O" in open_close or "O;C" in open_close
            # Preserve pnl=Decimal("0") for breakeven pure-close executions.
            _is_pure_close = "C" in open_close and "O" not in open_close
            pnl: Decimal | None = pnl_raw if (pnl_raw != Decimal("0") or _is_pure_close) else None

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
                broker_conid=conid,
                multiplier=multiplier,
                is_mixed_execution=is_mixed_execution,
            )
        except (ValueError, InvalidOperation, OverflowError) as exc:
            msg = f"<Trade> element {idx}: skipped — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None
        except Exception as exc:
            msg = f"<Trade> element {idx}: skipped due to validation error — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None

    def _parse_execution_element(self, elem: ET.Element, idx: int) -> TradeCreate | None:
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
            conid = elem.get("conid", "").strip() or None

            if not symbol:
                self.warnings.append(f"<Execution> element {idx}: skipped — missing symbol attribute.")
                return None

            asset_class = _map_asset_class(asset_category)
            # For options, use the underlying ticker as the trade symbol.
            # The full OCC contract string stays in raw_data for reference.
            if asset_class == AssetClass.OPTION:
                symbol = _extract_occ_underlying(symbol)

            exec_date = elem.get("execDate", "")
            exec_time = elem.get("execTime", "")

            if not exec_date:
                self.warnings.append(f"<Execution> element {idx} ({symbol}): skipped — missing execDate.")
                return None

            opened_at = _parse_execution_datetime(exec_date, exec_time)

            quantity_raw = _safe_decimal(elem.get("quantity"))
            if quantity_raw == Decimal("0"):
                self.warnings.append(f"<Execution> element {idx} ({symbol}): skipped — quantity is zero.")
                return None

            direction = Direction.LONG if quantity_raw > 0 else Direction.SHORT
            quantity = abs(quantity_raw)

            price = _safe_decimal(elem.get("price"))
            if price < Decimal("0"):
                self.warnings.append(f"<Execution> element {idx} ({symbol}): skipped — entry price is negative.")
                return None

            ib_comm = abs(_safe_decimal(elem.get("ibCommission")))
            gen_comm = abs(_safe_decimal(elem.get("commission")))
            commission = max(ib_comm, gen_comm)

            return TradeCreate(
                symbol=symbol,
                direction=direction,
                asset_class=asset_class,
                quantity=quantity,
                entry_price=price,
                commission=commission,
                opened_at=opened_at,
                broker_conid=conid,
            )
        except (ValueError, InvalidOperation, OverflowError) as exc:
            msg = f"<Execution> element {idx}: skipped — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None
        except Exception as exc:
            msg = f"<Execution> element {idx}: skipped due to validation error — {exc}"
            logger.warning(msg)
            self.warnings.append(msg)
            return None
