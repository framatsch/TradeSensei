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

"""Unit tests for Schwab JSON parser helpers and raw parsing."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.exceptions import ImportParseError
from app.models.trade import AssetClass, Direction
from app.utils.parsers.schwab_json import SchwabJSONParser


def _wrapped_payload(*transactions: dict[str, object]) -> dict[str, object]:
    return {
        "fetchedAt": "2026-07-02T18:00:00Z",
        "dateRange": {
            "start": "2026-07-01T00:00:00.000Z",
            "end": "2026-07-02T23:59:59.000Z",
        },
        "accounts": [
            {
                "accountNumber": "45302130",
                "accountHash": "hash-1",
                "positions": [],
                "transactions": list(transactions),
            }
        ],
    }


def _txn_transfer(
    instruction: str = "SELL_SHORT",
    status: str = "VALID",
    txn_type: str = "TRADE",
) -> dict[str, object]:
    return {
        "activityId": "A-2",
        "type": txn_type,
        "status": status,
        "time": "2026-07-02T17:35:33+0000",
        "transferItems": [
            {
                "instrument": {"symbol": "AMZN", "assetType": "EQUITY"},
                "instruction": instruction,
                "price": 145.76,
                "amount": 20,
            },
            {"feeType": "COMMISSION", "cost": "-0.65"},
            {"feeType": "SEC_FEE", "cost": "-0.10"},
        ],
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("instruction", "expected"),
    [
        ("BUY", Direction.LONG),
        ("SELL", Direction.LONG),
        ("BUY_TO_OPEN", Direction.LONG),
        ("SELL_TO_CLOSE", Direction.LONG),
        ("SELL_SHORT", Direction.SHORT),
        ("BUY_TO_COVER", Direction.SHORT),
        ("SELL_TO_OPEN", Direction.SHORT),
        ("BUY_TO_CLOSE", Direction.SHORT),
        ("SOMETHING_ELSE", None),
    ],
)
def test_map_direction(instruction: str, expected: Direction | None) -> None:
    parser = SchwabJSONParser()
    assert parser._map_direction(instruction) == expected


@pytest.mark.unit
def test_parse_datetime_handles_compact_utc_offset() -> None:
    parser = SchwabJSONParser()
    from_compact_offset = parser._parse_datetime("2026-07-02T17:35:33+0000")
    from_utc = parser._parse_datetime("2026-07-02T17:35:33Z")
    expected = datetime(2026, 7, 2, 17, 35, 33, tzinfo=UTC)
    assert from_compact_offset == expected
    assert from_utc == expected


@pytest.mark.unit
def test_extract_instrument_transfer_items() -> None:
    parser = SchwabJSONParser()
    instrument = parser._extract_instrument(_txn_transfer())
    assert instrument["symbol"] == "AMZN"
    assert instrument["price"] == 145.76
    assert instrument["amount"] == 20
    assert instrument["instruction"] == "SELL_SHORT"
    assert instrument["assetType"] == "EQUITY"


@pytest.mark.unit
def test_extract_commission_transfer_items() -> None:
    parser = SchwabJSONParser()
    commission_transfer = parser._extract_commission(_txn_transfer())
    assert commission_transfer == Decimal("0.75")


@pytest.mark.unit
def test_parse_raw_filters_non_trade_and_invalid_status() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(
        _txn_transfer(instruction="BUY"),
        _txn_transfer(txn_type="DIVIDEND"),
        _txn_transfer(status="PENDING"),
    )
    raw, corporate_actions = parser.parse_raw(
        json.dumps(payload).encode("utf-8"),
        "schwab.json",
    )
    assert len(raw) == 1
    assert corporate_actions == []


@pytest.mark.unit
def test_parse_raw_completed_record_maps_fields() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(_txn_transfer(instruction="BUY"))
    raw, _ = parser.parse_raw(
        json.dumps(payload).encode("utf-8"),
        "schwab.json",
    )
    assert len(raw) == 1
    record = raw[0]
    assert record.id == "schwab:A-2"
    assert record.direction == Direction.LONG
    assert record.quantity == Decimal("20")
    assert record.price == Decimal("145.76")
    assert record.asset_class == AssetClass.EQUITY
    assert record.currency == "USD"


@pytest.mark.unit
def test_parse_raw_unknown_instruction_skips_record() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(_txn_transfer(instruction="UNKNOWN"))
    raw, _ = parser.parse_raw(
        json.dumps(payload).encode("utf-8"),
        "schwab.json",
    )
    assert raw == []


@pytest.mark.unit
def test_parse_raw_rejects_legacy_top_level_array() -> None:
    parser = SchwabJSONParser()
    legacy_payload = [_txn_transfer(instruction="BUY")]

    with pytest.raises(ImportParseError, match="legacy top-level arrays"):
        parser.parse_raw(json.dumps(legacy_payload).encode("utf-8"), "schwab.json")
