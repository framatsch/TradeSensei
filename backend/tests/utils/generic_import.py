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

"""Convert native IBKR fixtures to the public generic format for equivalence tests."""

import csv
import io
import json

from app.models.trade import AssetClass, Direction
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.services.brokers.generic.validation import csv_columns
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from app.utils.parsers.schwab_json import SchwabJSONParser


def _execution_document(raw: BrokerRawTransactionCreate, *, external_ids: bool) -> dict[str, object]:
    """Project one native execution onto broker-neutral public fields."""
    execution: dict[str, object] = {
        "executed_at": raw.executed_at.isoformat(),
        "symbol": raw.symbol,
        "asset_class": raw.asset_class,
        "side": "BUY" if raw.direction == Direction.LONG else "SELL",
        "quantity": str(raw.quantity),
        "price": str(raw.price),
        "commission": str(raw.commission),
        "currency": raw.currency,
        "multiplier": raw.multiplier,
    }
    if external_ids:
        execution["external_id"] = raw.id.split(":", 1)[1]
    if raw.conid:
        execution["contract_id"] = raw.conid
    if raw.order_id:
        execution["order_id"] = raw.order_id
    if raw.is_mixed_execution:
        execution["position_effect"] = "CLOSE_OPEN"
    elif raw.open_close is not None:
        execution["position_effect"] = "OPEN" if raw.open_close == "O" else "CLOSE"
    if raw.pnl is not None:
        execution["realized_pnl"] = str(raw.pnl)
    if raw.asset_class == AssetClass.OPTION:
        if raw.strike is None or raw.expiry is None or raw.option_type is None:
            raise ValueError("Native fixture option lacks contract details.")
        execution["option"] = {"strike": str(raw.strike), "expiry": raw.expiry.isoformat(), "right": raw.option_type}
    return execution


def ibkr_fixture_to_generic(content: bytes, filename: str, *, external_ids: bool = True) -> bytes:
    """Convert the executions and splits actually accepted by the native parser.

    Native fixtures intentionally contain invalid rows skipped by the IBKR parser.
    These are omitted rather than made valid: equivalence compares the accepted
    executions, not broker-specific parser warning messages. Decimal values are
    emitted as strings so the conversion never passes through binary floats.
    """
    raws, actions = IBKRXMLParser().parse_raw(content, filename)
    splits: list[dict[str, object]] = []
    for action in actions:
        split: dict[str, object] = {
            "type": "SPLIT",
            "symbol": action.symbol,
            "date": action.date.isoformat(),
            "ratio": str(action.ratio),
        }
        if action.old_conid:
            split["old_contract_id"] = action.old_conid
        if action.new_conid:
            split["new_contract_id"] = action.new_conid
        splits.append(split)
    return json.dumps(
        {
            "format": "tradesensei.executions",
            "version": "1.0",
            "source": "IBKR test fixture",
            "executions": [_execution_document(raw, external_ids=external_ids) for raw in raws],
            "corporate_actions": splits,
        }
    ).encode("utf-8")


def broker_fixture_to_generic_csv(content: bytes, filename: str, broker: str) -> bytes:
    """Export the exact executions accepted by a native sample parser to CSV.

    No fills, timestamps, IDs or economic values are invented. Rows rejected
    by the native parser remain rejected; non-execution data has no CSV form.
    This helper is test-only, not a new production ingestion path.
    """
    parser = IBKRXMLParser() if broker == "ibkr" else SchwabJSONParser()
    raws, actions = parser.parse_raw(content, filename)
    if actions:
        raise ValueError("Stock splits need JSON and cannot be preserved in execution CSV.")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=csv_columns(), lineterminator="\n")
    writer.writeheader()
    for raw in raws:
        execution = _execution_document(raw, external_ids=True)
        option = execution.pop("option", None)
        if isinstance(option, dict):
            execution.update({f"option_{key}": value for key, value in option.items()})
        writer.writerow(execution)
    return stream.getvalue().encode("utf-8")
