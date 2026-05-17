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

from app.models.trade import AssetClass, Direction
from app.utils.parsers.schwab_json import SchwabJSONParser


def _txn_item(instruction: str = "BUY") -> dict[str, object]:
    return {
        "activityId": "A-1",
        "type": "TRADE",
        "status": "COMPLETED",
        "transactionDate": "2024-01-01T11:43:00.000-05:00",
        "transactionItem": {
            "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
            "instruction": instruction,
            "price": 184.5,
            "amount": 100,
        },
    }


def _txn_transfer(instruction: str = "SELL_SHORT") -> dict[str, object]:
    return {
        "activityId": "A-2",
        "type": "TRADE",
        "status": "VALID",
        "time": "2024-01-04T14:26:00.000Z",
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
def test_parse_datetime_handles_offset_and_utc_z() -> None:
    parser = SchwabJSONParser()
    from_offset = parser._parse_datetime("2024-01-01T11:43:00.000-05:00")
    from_utc = parser._parse_datetime("2024-01-01T16:43:00.000Z")
    expected = datetime(2024, 1, 1, 16, 43, 0, tzinfo=UTC)
    assert from_offset == expected
    assert from_utc == expected


@pytest.mark.unit
def test_extract_instrument_transaction_item() -> None:
    parser = SchwabJSONParser()
    instrument = parser._extract_instrument(_txn_item())
    assert instrument["symbol"] == "AAPL"
    assert instrument["price"] == 184.5
    assert instrument["amount"] == 100
    assert instrument["instruction"] == "BUY"
    assert instrument["assetType"] == "EQUITY"


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
def test_extract_commission_transfer_items_and_transaction_item() -> None:
    parser = SchwabJSONParser()
    commission_transfer = parser._extract_commission(_txn_transfer())
    commission_item = parser._extract_commission(_txn_item())
    assert commission_transfer == Decimal("0.75")
    assert commission_item == Decimal("0")


@pytest.mark.unit
def test_parse_raw_filters_non_trade_records() -> None:
    parser = SchwabJSONParser()
    payload = [
        _txn_item(),
        {
            "activityId": "A-NONTRADE",
            "type": "DIVIDEND",
            "status": "COMPLETED",
            "transactionDate": "2024-01-01T00:00:00.000Z",
        },
    ]
    raw, corporate_actions = parser.parse_raw(
        json.dumps(payload).encode("utf-8"),
        "schwab.json",
    )
    assert len(raw) == 1
    assert corporate_actions == []


@pytest.mark.unit
def test_parse_raw_completed_record_maps_fields() -> None:
    parser = SchwabJSONParser()
    raw, _ = parser.parse_raw(
        json.dumps([_txn_item()]).encode("utf-8"),
        "schwab.json",
    )
    assert len(raw) == 1
    record = raw[0]
    assert record.id == "schwab:A-1"
    assert record.direction == Direction.LONG
    assert record.quantity == Decimal("100")
    assert record.price == Decimal("184.5")
    assert record.asset_class == AssetClass.EQUITY
    assert record.currency == "USD"


@pytest.mark.unit
def test_parse_raw_unknown_instruction_skips_record() -> None:
    parser = SchwabJSONParser()
    raw, _ = parser.parse_raw(
        json.dumps([_txn_item(instruction="UNKNOWN")]).encode("utf-8"),
        "schwab.json",
    )
    assert raw == []
