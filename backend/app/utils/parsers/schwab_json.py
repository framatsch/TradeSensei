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

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from app.core.exceptions import ImportParseError
from app.models.trade import AssetClass, Direction
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import CorporateActionLike, SeedLotLike
from app.utils.parsers.base import BrokerParser

logger = logging.getLogger(__name__)

_BROKER_TYPE = "schwab"
_VALID_TRADE_STATUSES = frozenset({"COMPLETED", "VALID"})
_FEE_TYPES = frozenset({"COMMISSION", "SEC_FEE", "TAF_FEE", "OPT_REG_FEE"})
_TRADE_ASSET_TYPES = frozenset({"EQUITY", "OPTION"})
_FUTURE_ASSET_TYPES = frozenset({"FUTURE", "FUTURE_OPTION"})


def decode_schwab_wrapped_payload(content: bytes) -> dict[str, object]:
    """Decode and validate Schwab wrapped JSON payload.

    Expected shape is a top-level object with an ``accounts`` array.
    """
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ImportParseError("Schwab JSON file is not valid UTF-8 text.") from exc
    except json.JSONDecodeError as exc:
        raise ImportParseError(f"Invalid Schwab JSON: {exc}") from exc

    if isinstance(payload, list):
        raise ImportParseError(
            "Schwab JSON payload must use wrapped format "
            "{fetchedAt, dateRange, accounts:[...]} with a top-level object; "
            "legacy top-level arrays are no longer supported."
        )
    if not isinstance(payload, dict):
        raise ImportParseError("Schwab JSON payload must be a top-level object with an accounts array.")

    accounts = payload.get("accounts")
    if not isinstance(accounts, list):
        raise ImportParseError("Schwab JSON payload must include an 'accounts' array.")

    return payload


def _derive_open_close(position_effect: str) -> str | None:
    """Derive the per-leg open/close indicator from a Schwab ``positionEffect``.

    Args:
        position_effect: Upper-cased ``positionEffect`` value from the primary
            trade leg (e.g. ``"OPENING"`` / ``"CLOSING"``).

    Returns:
        ``"O"`` for ``OPENING``, ``"C"`` for ``CLOSING``, otherwise ``None``.
    """
    if position_effect == "OPENING":
        return "O"
    if position_effect == "CLOSING":
        return "C"
    return None


class SchwabJSONParser(BrokerParser):
    """Parse Schwab JSON transactions into broker raw transactions."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def parse(
        self,
        content: bytes,
        filename: str,
        corporate_actions: Sequence[CorporateActionLike] | None = None,
        seed_open_lots: Sequence[SeedLotLike] | None = None,
        seed_orphaned_lots: Sequence[SeedLotLike] | None = None,
    ) -> tuple[list[TradeCreate], list[object]]:
        del content, filename, corporate_actions, seed_open_lots, seed_orphaned_lots
        raise NotImplementedError("SchwabJSONParser only supports parse_raw().")

    def parse_raw(
        self,
        content: bytes,
        filename: str,
    ) -> tuple[
        list[BrokerRawTransactionCreate],
        list[CorporateActionCreateRequest],
    ]:
        del filename
        self.warnings = []

        payload = decode_schwab_wrapped_payload(content)
        accounts = payload.get("accounts")
        assert isinstance(accounts, list)

        raw_records: list[BrokerRawTransactionCreate] = []

        for account_idx, account_entry in enumerate(accounts, start=1):
            if not isinstance(account_entry, dict):
                raise ImportParseError(f"Schwab JSON accounts[{account_idx}]: expected object entry.")

            account_number = str(account_entry.get("accountNumber", "")).strip()
            transactions = account_entry.get("transactions")
            if not account_number:
                raise ImportParseError(f"Schwab JSON accounts[{account_idx}]: missing required field 'accountNumber'.")
            if not isinstance(transactions, list):
                raise ImportParseError(f"Schwab JSON accounts[{account_idx}] ({account_number}): missing required 'transactions' array.")

            for idx, txn in enumerate(transactions, start=1):
                if not isinstance(txn, dict):
                    msg = f"Schwab JSON account {account_number} transaction {idx}: skipped - expected object entry."
                    logger.warning(msg)
                    self.warnings.append(msg)
                    continue

                txn_type = str(txn.get("type", "")).upper()
                txn_status = str(txn.get("status", "")).upper()
                if txn_type != "TRADE" or txn_status not in _VALID_TRADE_STATUSES:
                    continue

                activity_id = self._normalize_activity_id(txn.get("activityId"))
                if not activity_id:
                    msg = f"Schwab JSON account {account_number} transaction {idx}: skipped - missing activityId."
                    logger.warning(msg)
                    self.warnings.append(msg)
                    continue

                try:
                    instrument = self._extract_instrument(txn)
                    if instrument is None:
                        # No EQUITY/OPTION execution leg: fee/interest/tax-only
                        # transaction (CURRENCY legs only) — ignore silently.
                        continue

                    asset_type = str(instrument["assetType"] or "").upper()
                    if asset_type in _FUTURE_ASSET_TYPES:
                        msg = f"Schwab futures not yet supported; transaction skipped (activityId={activity_id})."
                        logger.warning(msg)
                        self.warnings.append(msg)
                        continue

                    position_effect = str(instrument["positionEffect"] or "").upper()
                    net_amount = txn.get("netAmount")
                    execution_direction = self._resolve_direction(
                        instruction=instrument["instruction"],
                        cost=instrument["cost"],
                        position_effect=position_effect,
                        net_amount=net_amount,
                    )
                    if execution_direction is None:
                        msg = f"Schwab transaction skipped - indeterminate direction (activityId={activity_id})."
                        logger.warning(msg)
                        self.warnings.append(msg)
                        continue

                    executed_at = self._parse_execution_datetime(txn)
                    quantity = abs(Decimal(str(instrument["amount"])))
                    price = abs(Decimal(str(instrument["price"])))
                    commission = self._extract_commission(txn)
                    asset_class = self._map_asset_class(instrument["assetType"])
                    pnl = Decimal("0") if position_effect == "CLOSING" else None
                    open_close = _derive_open_close(position_effect)

                    raw_records.append(
                        BrokerRawTransactionCreate(
                            id=f"{_BROKER_TYPE}:{activity_id}",
                            broker_type=_BROKER_TYPE,
                            symbol=str(instrument["symbol"]).upper(),
                            asset_class=asset_class,
                            direction=execution_direction,
                            quantity=quantity,
                            price=price,
                            commission=commission,
                            executed_at=executed_at,
                            pnl=pnl,
                            currency="USD",
                            multiplier=1,
                            open_close=open_close,
                            raw_data=txn,
                        )
                    )
                except (KeyError, ValueError, InvalidOperation) as exc:
                    msg = f"Schwab transaction {activity_id or idx}: skipped - could not parse record ({exc})."
                    logger.warning(msg)
                    self.warnings.append(msg)

        return raw_records, []

    def _extract_instrument(self, txn: dict[str, object]) -> dict[str, object] | None:
        """Return the primary EQUITY/OPTION/FUTURE execution leg fields.

        Selects the first ``transferItems`` leg whose ``instrument.assetType``
        is a trade type (``EQUITY``/``OPTION``) — or a futures type
        (``FUTURE``/``FUTURE_OPTION``) so the caller can skip it with a
        warning — and has a non-empty symbol.  ``CURRENCY`` legs are never
        selected.  Returns ``None`` when the transaction has no such leg
        (fee/interest/tax-only transactions).
        """
        transfer_items = txn.get("transferItems")
        if not isinstance(transfer_items, list) or not transfer_items:
            raise ValueError("missing transferItems")

        instrument_leg: dict[str, object] | None = None
        for leg in transfer_items:
            if not isinstance(leg, dict):
                continue
            leg_instrument = leg.get("instrument")
            if not isinstance(leg_instrument, dict):
                continue
            asset_type = str(leg_instrument.get("assetType", "")).upper()
            if asset_type not in _TRADE_ASSET_TYPES and asset_type not in _FUTURE_ASSET_TYPES:
                continue
            symbol = str(leg_instrument.get("symbol", "")).strip()
            if symbol:
                instrument_leg = leg
                break

        if instrument_leg is None:
            return None

        instrument = instrument_leg.get("instrument")
        assert isinstance(instrument, dict)
        return {
            "symbol": instrument.get("symbol"),
            "price": instrument_leg.get("price") or instrument_leg.get("cost"),
            "amount": instrument_leg.get("amount") or instrument_leg.get("quantity"),
            "instruction": instrument_leg.get("instruction"),
            "assetType": instrument.get("assetType"),
            "positionEffect": instrument_leg.get("positionEffect"),
            "cost": instrument_leg.get("cost"),
        }

    @staticmethod
    def _normalize_activity_id(value: object) -> str:
        """Normalize an activityId to a plain string id (no decimal suffix)."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return ""
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return str(int(value)) if value.is_integer() else str(value)
        return str(value).strip()

    def _parse_execution_datetime(self, txn: dict[str, object]) -> datetime:
        """Resolve the execution timestamp with a ``time → tradeDate → transactionDate`` fallback."""
        for key in ("time", "tradeDate", "transactionDate"):
            value = txn.get(key)
            if value:
                return self._parse_datetime(str(value))
        raise ValueError("missing execution datetime (time/tradeDate/transactionDate)")

    def _parse_datetime(self, value: str) -> datetime:
        if not value:
            raise ValueError("missing datetime field")
        normalized = value.replace("Z", "+00:00")
        # Normalize a trailing numeric offset without a colon (e.g. "+0000" → "+00:00").
        if len(normalized) >= 5 and normalized[-5] in {"+", "-"} and normalized[-3] != ":":
            normalized = f"{normalized[:-2]}:{normalized[-2:]}"
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _resolve_direction(
        self,
        *,
        instruction: object,
        cost: object,
        position_effect: str,
        net_amount: object,
    ) -> Direction | None:
        """Resolve the execution (buy/sell) direction for a trade leg.

        Prefers an explicit ``instruction`` (OPTION legs, legacy fixtures).
        Otherwise derives the buy/sell action from the sign of ``cost``
        (negative = buy, positive = sell), falling back to the sign of the
        transaction ``netAmount`` when ``cost`` is absent or zero, then maps
        the action to a :class:`~app.models.trade.Direction`.
        """
        raw = str(instruction or "").upper()
        if raw:
            if raw in {"BUY", "BUY_TO_COVER", "BUY_TO_OPEN", "BUY_TO_CLOSE"}:
                return Direction.LONG
            if raw in {"SELL", "SELL_SHORT", "SELL_TO_OPEN", "SELL_TO_CLOSE"}:
                return Direction.SHORT
            logger.warning("Unknown Schwab instruction: %s", raw)
            return None

        action = self._resolve_action(cost, net_amount)
        if action is None:
            return None
        # Direction is the execution (buy/sell) side, disambiguated for
        # FIFO by positionEffect elsewhere. cost<0 = buy, cost>0 = sell.
        del position_effect
        return Direction.LONG if action == "BUY" else Direction.SHORT

    @staticmethod
    def _resolve_action(cost: object, net_amount: object) -> str | None:
        """Return ``"BUY"``/``"SELL"`` from the cost sign, falling back to netAmount."""
        for candidate in (cost, net_amount):
            if candidate is None:
                continue
            try:
                value = Decimal(str(candidate))
            except InvalidOperation:
                continue
            if value < 0:
                return "BUY"
            if value > 0:
                return "SELL"
        return None

    def _map_asset_class(self, asset_type: object) -> AssetClass:
        raw = str(asset_type or "").upper()
        if raw == "EQUITY":
            return AssetClass.EQUITY
        if raw == "OPTION":
            return AssetClass.OPTION
        logger.warning("Unknown Schwab assetType '%s' - defaulting to EQUITY", raw)
        return AssetClass.EQUITY

    def _extract_commission(self, txn: dict[str, object]) -> Decimal:
        transfer_items = txn.get("transferItems")
        if not isinstance(transfer_items, list):
            return Decimal("0")

        commission = Decimal("0")
        for leg in transfer_items:
            if not isinstance(leg, dict):
                continue
            fee_type = str(leg.get("feeType", "")).upper()
            if fee_type not in _FEE_TYPES:
                continue
            instrument = leg.get("instrument")
            asset_type = ""
            if isinstance(instrument, dict):
                asset_type = str(instrument.get("assetType", "")).upper()
            # Fees are CURRENCY legs; never treat a trade leg as a fee.
            if asset_type and asset_type != "CURRENCY":
                continue

            try:
                cost = Decimal(str(leg.get("cost", "0")))
            except InvalidOperation:
                continue
            commission += abs(cost)
        return commission
