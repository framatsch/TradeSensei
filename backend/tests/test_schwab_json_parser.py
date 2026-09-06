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

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.trade import Direction
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


def _equity_txn(
    *,
    activity_id: int = 1,
    status: str = "VALID",
    cost: float = -1000.0,
    net_amount: float = -1000.0,
    position_effect: str = "OPENING",
    include_instruction: str | None = None,
    fee_type: str | None = None,
) -> dict[str, object]:
    leg: dict[str, object] = {
        "instrument": {"assetType": "EQUITY", "symbol": "AAPL"},
        "amount": 10.0,
        "cost": cost,
        "price": 100.0,
        "positionEffect": position_effect,
    }
    if include_instruction is not None:
        leg["instruction"] = include_instruction

    transfer_items: list[dict[str, object]] = [leg]
    if fee_type is not None:
        transfer_items.insert(
            0,
            {
                "instrument": {"assetType": "CURRENCY", "symbol": "CURRENCY_USD"},
                "amount": 0.01,
                "cost": -0.01,
                "feeType": fee_type,
            },
        )

    return {
        "activityId": activity_id,
        "type": "TRADE",
        "status": status,
        "time": "2026-07-02T17:35:33+0000",
        "tradeDate": "2026-07-02T17:35:33+0000",
        "netAmount": net_amount,
        "transferItems": transfer_items,
    }


@pytest.mark.unit
def test_instruction_branch_kept_for_options() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(
        {
            "activityId": 7001,
            "type": "TRADE",
            "status": "VALID",
            "time": "2026-07-02T17:35:33+0000",
            "netAmount": 500.0,
            "transferItems": [
                {
                    "instrument": {"assetType": "OPTION", "symbol": "AAPL  260717C00200000"},
                    "instruction": "SELL_TO_OPEN",
                    "amount": 1.0,
                    "cost": 500.0,
                    "price": 5.0,
                    "positionEffect": "OPENING",
                }
            ],
        }
    )
    raw, _ = parser.parse_raw(json.dumps(payload).encode("utf-8"), "schwab_option.json")
    assert len(raw) == 1
    assert raw[0].direction == Direction.SHORT
    assert raw[0].strike == Decimal("200")
    assert raw[0].expiry is not None
    assert raw[0].expiry.isoformat() == "2026-07-17"
    assert raw[0].option_type == "C"


@pytest.mark.unit
def test_fee_only_transaction_is_ignored_without_warning() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(
        {
            "activityId": 8001,
            "type": "TRADE",
            "status": "VALID",
            "time": "2026-07-02T17:35:33+0000",
            "netAmount": -0.1,
            "transferItems": [
                {
                    "instrument": {"assetType": "CURRENCY", "symbol": "CURRENCY_USD"},
                    "amount": 0.1,
                    "cost": -0.1,
                    "feeType": "SEC_FEE",
                }
            ],
        }
    )
    raw, _ = parser.parse_raw(json.dumps(payload).encode("utf-8"), "fees_only.json")
    assert raw == []
    assert parser.warnings == []


@pytest.mark.unit
def test_pending_or_cancelled_status_skipped_without_warning() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(
        _equity_txn(activity_id=8101, status="PENDING"),
        _equity_txn(activity_id=8102, status="CANCELLED"),
    )
    raw, _ = parser.parse_raw(json.dumps(payload).encode("utf-8"), "statuses.json")
    assert raw == []
    assert parser.warnings == []


@pytest.mark.unit
def test_future_transaction_skipped_with_one_warning() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(
        {
            "activityId": 8201,
            "type": "TRADE",
            "status": "VALID",
            "time": "2026-07-02T17:35:33+0000",
            "netAmount": 10.0,
            "transferItems": [
                {
                    "instrument": {"assetType": "FUTURE", "symbol": "ESU6"},
                    "amount": 1.0,
                    "cost": 10.0,
                    "price": 10.0,
                    "positionEffect": "OPENING",
                }
            ],
        }
    )
    raw, _ = parser.parse_raw(json.dumps(payload).encode("utf-8"), "future.json")
    assert raw == []
    assert len(parser.warnings) == 1
    assert "futures not yet supported" in parser.warnings[0]
    assert "activityId=8201" in parser.warnings[0]


@pytest.mark.unit
def test_opt_reg_fee_is_included_in_commission() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(_equity_txn(activity_id=8301, fee_type="OPT_REG_FEE"))
    raw, _ = parser.parse_raw(json.dumps(payload).encode("utf-8"), "opt_reg_fee.json")
    assert len(raw) == 1
    assert str(raw[0].commission) == "0.01"


@pytest.mark.unit
def test_schwab_open_close_mapping_opening_closing_and_absent() -> None:
    """Schwab positionEffect maps to open_close: OPENING→O, CLOSING→C, absent→None."""
    from app.utils.parsers.schwab_json import _derive_open_close

    assert _derive_open_close("OPENING") == "O"
    assert _derive_open_close("CLOSING") == "C"
    assert _derive_open_close("") is None
    assert _derive_open_close("SOMETHING") is None

    parser = SchwabJSONParser()

    opening_payload = _wrapped_payload(_equity_txn(activity_id=9001, position_effect="OPENING"))
    opening_raw, _ = parser.parse_raw(json.dumps(opening_payload).encode("utf-8"), "opening.json")
    assert len(opening_raw) == 1
    assert opening_raw[0].open_close == "O"

    closing_payload = _wrapped_payload(_equity_txn(activity_id=9002, position_effect="CLOSING"))
    closing_raw, _ = parser.parse_raw(json.dumps(closing_payload).encode("utf-8"), "closing.json")
    assert len(closing_raw) == 1
    assert closing_raw[0].open_close == "C"

    # positionEffect absent → open_close is None.
    absent_txn = {
        "activityId": 9003,
        "type": "TRADE",
        "status": "VALID",
        "time": "2026-07-02T17:35:33+0000",
        "netAmount": -1000.0,
        "transferItems": [
            {
                "instrument": {"assetType": "EQUITY", "symbol": "AAPL"},
                "amount": 10.0,
                "cost": -1000.0,
                "price": 100.0,
            }
        ],
    }
    absent_payload = _wrapped_payload(absent_txn)
    absent_raw, _ = parser.parse_raw(json.dumps(absent_payload).encode("utf-8"), "absent.json")
    assert len(absent_raw) == 1
    assert absent_raw[0].open_close is None


@pytest.mark.unit
def test_schwab_closing_position_sets_zero_pnl_as_presence_sentinel() -> None:
    parser = SchwabJSONParser()
    payload = _wrapped_payload(_equity_txn(activity_id=9004, position_effect="CLOSING"))
    raw, _ = parser.parse_raw(json.dumps(payload).encode("utf-8"), "closing_sentinel.json")
    assert len(raw) == 1
    assert raw[0].pnl == Decimal("0")


@pytest.mark.unit
def test_real_export_regression_five_records_zero_warnings_and_cost_direction() -> None:
    parser = SchwabJSONParser()
    fixture = Path(__file__).resolve().parents[2] / "tests" / "test_data" / "schwab" / "schwab_transactions_real_trimmed.json"
    raw, _ = parser.parse_raw(fixture.read_bytes(), fixture.name)

    assert len(raw) == 5
    assert parser.warnings == []

    by_id = {record.id: record for record in raw}
    assert by_id["schwab:124780687237"].direction == Direction.LONG
    assert by_id["schwab:123987433325"].direction == Direction.SHORT
    assert by_id["schwab:123689628930"].direction == Direction.LONG
    assert by_id["schwab:123835463029"].direction == Direction.LONG
    assert by_id["schwab:124694896745"].direction == Direction.LONG
