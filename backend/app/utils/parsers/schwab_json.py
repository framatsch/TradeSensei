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
from app.schemas.cash_transaction import CashTransactionCreateRequest
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import CorporateActionLike, SeedLotLike
from app.utils.parsers.base import BrokerParser

logger = logging.getLogger(__name__)

_BROKER_TYPE = "schwab"
_VALID_TRADE_STATUSES = frozenset({"COMPLETED", "VALID"})
_CLOSING_INSTRUCTIONS = frozenset({"SELL", "BUY_TO_COVER"})
_FEE_TYPES = frozenset({"COMMISSION", "SEC_FEE", "TAF_FEE"})


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
    ) -> tuple[list[TradeCreate], list[CashTransactionCreateRequest]]:
        del content, filename, corporate_actions, seed_open_lots, seed_orphaned_lots
        raise NotImplementedError("SchwabJSONParser only supports parse_raw().")

    def parse_raw(
        self,
        content: bytes,
        filename: str,
    ) -> tuple[
        list[BrokerRawTransactionCreate],
        list[CashTransactionCreateRequest],
        list[CorporateActionCreateRequest],
    ]:
        del filename
        self.warnings = []

        try:
            payload = json.loads(content.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise ImportParseError("Schwab JSON file is not valid UTF-8 text.") from exc
        except json.JSONDecodeError as exc:
            raise ImportParseError(f"Invalid Schwab JSON: {exc}") from exc

        if not isinstance(payload, list):
            raise ImportParseError("Schwab JSON payload must be a top-level array.")

        raw_records: list[BrokerRawTransactionCreate] = []

        for idx, txn in enumerate(payload, start=1):
            if not isinstance(txn, dict):
                msg = f"Schwab JSON item {idx}: skipped - expected object entry."
                logger.warning(msg)
                self.warnings.append(msg)
                continue

            txn_type = str(txn.get("type", "")).upper()
            txn_status = str(txn.get("status", "")).upper()
            if txn_type != "TRADE" or txn_status not in _VALID_TRADE_STATUSES:
                continue

            activity_id = str(txn.get("activityId", "")).strip()
            if not activity_id:
                msg = f"Schwab JSON item {idx}: skipped - missing activityId."
                logger.warning(msg)
                self.warnings.append(msg)
                continue

            try:
                instrument = self._extract_instrument(txn)
                direction = self._map_direction(instrument["instruction"])
                if direction is None:
                    msg = f"Schwab transaction skipped due to unknown instruction (activityId={activity_id})."
                    logger.warning(msg)
                    self.warnings.append(msg)
                    continue

                execution_direction = self._map_execution_direction(instrument["instruction"])
                if execution_direction is None:
                    msg = f"Schwab transaction skipped due to unknown instruction (activityId={activity_id})."
                    logger.warning(msg)
                    self.warnings.append(msg)
                    continue

                executed_at = self._parse_datetime(str(txn.get("transactionDate") or txn.get("time") or ""))
                quantity = abs(Decimal(str(instrument["amount"])))
                price = abs(Decimal(str(instrument["price"])))
                commission = self._extract_commission(txn)
                asset_class = self._map_asset_class(instrument["assetType"])
                pnl = Decimal("0") if str(instrument["instruction"]).upper() in _CLOSING_INSTRUCTIONS else None

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
                        raw_data=txn,
                    )
                )
            except (KeyError, ValueError, InvalidOperation) as exc:
                msg = f"Schwab transaction {activity_id or idx}: skipped - could not parse record ({exc})."
                logger.warning(msg)
                self.warnings.append(msg)

        return raw_records, [], []

    def _extract_instrument(self, txn: dict[str, object]) -> dict[str, object]:
        transaction_item = txn.get("transactionItem")
        if isinstance(transaction_item, dict):
            instrument = transaction_item.get("instrument")
            if not isinstance(instrument, dict):
                raise ValueError("transactionItem.instrument missing")
            return {
                "symbol": instrument.get("symbol"),
                "price": transaction_item.get("price"),
                "amount": transaction_item.get("amount"),
                "instruction": transaction_item.get("instruction"),
                "assetType": instrument.get("assetType"),
            }

        transfer_items = txn.get("transferItems")
        if not isinstance(transfer_items, list) or not transfer_items:
            raise ValueError("missing transactionItem/transferItems")

        instrument_leg: dict[str, object] | None = None
        for leg in transfer_items:
            if not isinstance(leg, dict):
                continue
            leg_instrument = leg.get("instrument")
            if not isinstance(leg_instrument, dict):
                continue
            symbol = str(leg_instrument.get("symbol", "")).strip()
            if symbol:
                instrument_leg = leg
                break

        if instrument_leg is None:
            raise ValueError("transferItems has no instrument leg")

        instrument = instrument_leg.get("instrument")
        assert isinstance(instrument, dict)
        return {
            "symbol": instrument.get("symbol"),
            "price": instrument_leg.get("price") or instrument_leg.get("cost"),
            "amount": instrument_leg.get("amount") or instrument_leg.get("quantity"),
            "instruction": instrument_leg.get("instruction"),
            "assetType": instrument.get("assetType"),
        }

    def _parse_datetime(self, value: str) -> datetime:
        if not value:
            raise ValueError("missing datetime field")
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _map_direction(self, instruction: object) -> Direction | None:
        raw = str(instruction or "").upper()
        if raw in {"BUY", "SELL", "BUY_TO_OPEN", "SELL_TO_CLOSE"}:
            return Direction.LONG
        if raw in {"SELL_SHORT", "BUY_TO_COVER", "SELL_TO_OPEN", "BUY_TO_CLOSE"}:
            return Direction.SHORT
        logger.warning("Unknown Schwab instruction: %s", raw)
        return None

    def _map_execution_direction(self, instruction: object) -> Direction | None:
        raw = str(instruction or "").upper()
        if raw in {"BUY", "BUY_TO_COVER", "BUY_TO_OPEN", "BUY_TO_CLOSE"}:
            return Direction.LONG
        if raw in {"SELL", "SELL_SHORT", "SELL_TO_OPEN", "SELL_TO_CLOSE"}:
            return Direction.SHORT
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
        if isinstance(txn.get("transactionItem"), dict):
            return Decimal("0")

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
            symbol = ""
            if isinstance(instrument, dict):
                symbol = str(instrument.get("symbol", "")).strip()
            if symbol:
                continue

            try:
                cost = Decimal(str(leg.get("cost", "0")))
            except InvalidOperation:
                continue
            commission += abs(cost)
        return commission
