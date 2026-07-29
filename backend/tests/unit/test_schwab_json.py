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

import json
from decimal import Decimal

import pytest

from app.core.exceptions import ImportParseError
from app.models.trade import AssetClass
from app.utils.parsers.schwab_json import (
    SchwabJSONParser,
    decode_schwab_wrapped_payload,
)


def test_decode_schwab_wrapped_payload():
    with pytest.raises(ImportParseError, match="not valid UTF-8"):
        decode_schwab_wrapped_payload(b"\xff\xff")
    with pytest.raises(ImportParseError, match="Invalid Schwab JSON"):
        decode_schwab_wrapped_payload(b"{bad json}")
    with pytest.raises(ImportParseError, match="legacy top-level arrays"):
        decode_schwab_wrapped_payload(b"[]")
    with pytest.raises(ImportParseError, match="must be a top-level object"):
        decode_schwab_wrapped_payload(b"\"string\"")
    with pytest.raises(ImportParseError, match="must include an 'accounts' array"):
        decode_schwab_wrapped_payload(b"{}")

def test_parse_not_implemented():
    with pytest.raises(NotImplementedError):
        SchwabJSONParser().parse(b"", "test.json")

def test_account_errors():
    parser = SchwabJSONParser()
    with pytest.raises(ImportParseError, match="expected object entry"):
        parser.parse_raw(b'{"accounts": ["bad"]}', "test.json")
    with pytest.raises(ImportParseError, match="missing required field 'accountNumber'"):
        parser.parse_raw(b'{"accounts": [{}]}', "test.json")
    with pytest.raises(ImportParseError, match="missing required 'transactions' array"):
        parser.parse_raw(b'{"accounts": [{"accountNumber": "123"}]}', "test.json")

def test_transaction_errors():
    payload = {
        "accounts": [
            {
                "accountNumber": "123",
                "transactions": [
                    "not a dict",
                    {"type": "TRADE", "status": "COMPLETED"}, # missing activityId
                    {
                        "type": "TRADE", "status": "COMPLETED", "activityId": "1",
                        "transferItems": "bad" # missing transferItems
                    },
                    {
                        "type": "TRADE", "status": "COMPLETED", "activityId": "2",
                        "transferItems": [
                            "bad leg",
                            {"instrument": "bad"},
                            {"instrument": {"assetType": "CURRENCY"}}, # no symbol, skipped
                        ]
                    },
                    {
                        "type": "TRADE", "status": "COMPLETED", "activityId": "3",
                        "transferItems": [
                            {"instrument": {"assetType": "EQUITY", "symbol": "AAPL"}, "instruction": "UNKNOWN", "cost": 0, "amount": 1, "price": 10}
                        ],
                        "netAmount": 0 # Indeterminate direction
                    },
                    {
                         "type": "TRADE", "status": "COMPLETED", "activityId": "4",
                         "transferItems": [
                             {"instrument": {"assetType": "EQUITY", "symbol": "AAPL"}, "instruction": "BUY", "amount": 1, "price": 10}
                         ],
                         "netAmount": -10 # No execution datetime
                    }
                ]
            }
        ]
    }
    parser = SchwabJSONParser()
    parser.parse_raw(json.dumps(payload).encode("utf-8"), "test.json")
    assert len(parser.warnings) == 5

@pytest.mark.parametrize("value,expected", [
    (None, ""),
    (True, ""),
    (123, "123"),
    (123.0, "123"),
    (123.5, "123.5"),
    (" 123 ", "123")
])
def test_normalize_activity_id(value, expected):
    assert SchwabJSONParser._normalize_activity_id(value) == expected

@pytest.mark.parametrize("date_str", [
    "",
    "2023-01-01T12:00:00+0000", # missing colon
])
def test_parse_datetime_errors(date_str):
    parser = SchwabJSONParser()
    if not date_str:
        with pytest.raises(ValueError):
            parser._parse_datetime(date_str)
    else:
        # test normalization
        dt = parser._parse_datetime(date_str)
        assert dt.isoformat() == "2023-01-01T12:00:00+00:00"

def test_resolve_direction_unknown():
    parser = SchwabJSONParser()
    assert parser._resolve_direction(instruction="UNKNOWN", cost=10, position_effect="", net_amount=0) is None

@pytest.mark.parametrize("cost, net_amount, expected", [
    ("bad", "bad", None),
    (0, 0, None),
    (10, 0, "SELL"),
    (-10, 0, "BUY"),
    (0, 10, "SELL"),
    (0, -10, "BUY"),
])
def test_resolve_action(cost, net_amount, expected):
    assert SchwabJSONParser._resolve_action(cost, net_amount) == expected

def test_map_asset_class():
    parser = SchwabJSONParser()
    assert parser._map_asset_class("UNKNOWN") == AssetClass.EQUITY
    assert parser._map_asset_class(None) == AssetClass.EQUITY

def test_extract_commission():
    parser = SchwabJSONParser()
    assert parser._extract_commission({}) == Decimal("0")
    assert parser._extract_commission({"transferItems": "bad"}) == Decimal("0")
    assert parser._extract_commission({"transferItems": [
        "bad",
        {"feeType": "UNKNOWN"},
        {"feeType": "COMMISSION", "instrument": "bad"},
        {"feeType": "COMMISSION", "instrument": {"assetType": "EQUITY"}},
        {"feeType": "COMMISSION", "instrument": {"assetType": "CURRENCY"}, "cost": "bad"},
        {"feeType": "COMMISSION", "instrument": {"assetType": "CURRENCY"}, "cost": "-1.5"}
    ]}) == Decimal("1.5")
