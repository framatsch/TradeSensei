"""Unit tests for SchwabOrderNormalizer.normalize().

All tests are pure-data: no IO, no database, no HTTP.  Every case exercises
a different branch of the normalizer's filtering and field-mapping logic.
"""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from typing import Any

import pytest

from app.models.trade import AssetClass, Direction
from app.utils.schwab_normalizer import SchwabOrderNormalizer


def _base_order(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid Schwab FILLED LIMIT BUY order dict.

    Callers can pass keyword arguments to override individual fields or
    add new top-level keys before passing to the normalizer.

    Args:
        **overrides: Fields to merge into the base order dict.

    Returns:
        A dict representing a complete, valid Schwab order.
    """
    order: dict[str, Any] = {
        "orderId": "12345",
        "status": "FILLED",
        "orderType": "LIMIT",
        "filledQuantity": 10,
        "price": 150.00,
        "closeTime": "2024-01-15T10:30:00Z",
        "orderLegCollection": [
            {
                "instruction": "BUY",
                "instrument": {"symbol": "AAPL", "assetType": "EQUITY"},
            }
        ],
    }
    order.update(overrides)
    return order


async def test_normalize_valid_buy_order() -> None:
    """normalize() returns a populated TradeCreate for a valid BUY LIMIT order.

    Verifies all mapped fields: symbol, direction, asset_class, quantity,
    entry_price, exit_price, opened_at, closed_at, currency, broker_order_id.
    """
    result = SchwabOrderNormalizer.normalize(_base_order())

    assert result is not None
    assert result.symbol == "AAPL"
    assert result.direction == Direction.LONG
    assert result.asset_class == AssetClass.EQUITY
    assert result.quantity == Decimal("10")
    assert result.entry_price == Decimal("150.0")
    assert result.exit_price == Decimal("150.0")
    assert result.currency == "USD"
    assert result.broker_order_id == "12345"
    assert result.opened_at is not None
    assert result.opened_at.tzinfo is not None


async def test_normalize_valid_sell_order() -> None:
    """normalize() maps SELL instruction to Direction.SHORT.

    Ensures the _DIRECTION_MAP lookup works for the sell side.
    """
    order = _base_order()
    order["orderLegCollection"][0]["instruction"] = "SELL"

    result = SchwabOrderNormalizer.normalize(order)

    assert result is not None
    assert result.direction == Direction.SHORT


async def test_normalize_skips_non_filled() -> None:
    """normalize() returns None for an order whose status is not FILLED.

    WORKING, PENDING_ACTIVATION, CANCELLED, etc. are all non-importable.
    """
    result = SchwabOrderNormalizer.normalize(_base_order(status="WORKING"))

    assert result is None


async def test_normalize_skips_unsupported_order_type() -> None:
    """normalize() returns None when orderType is not MARKET or LIMIT.

    STOP, STOP_LIMIT, TRAILING_STOP, etc. are not handled by the normalizer.
    """
    result = SchwabOrderNormalizer.normalize(_base_order(orderType="STOP"))

    assert result is None


async def test_normalize_missing_symbol() -> None:
    """normalize() returns None when no symbol can be resolved.

    Both the orderLegCollection instrument.symbol and the top-level symbol
    fallback are missing.
    """
    order = _base_order()
    order["orderLegCollection"][0]["instrument"] = {}
    # No top-level symbol fallback either
    result = SchwabOrderNormalizer.normalize(order)

    assert result is None


async def test_normalize_unknown_instruction() -> None:
    """normalize() returns None for an instruction not in BUY/SELL.

    An instruction like "SHORT_SELL" is not in the _DIRECTION_MAP.
    """
    order = _base_order()
    order["orderLegCollection"][0]["instruction"] = "SHORT_SELL"

    result = SchwabOrderNormalizer.normalize(order)

    assert result is None


async def test_normalize_zero_quantity() -> None:
    """normalize() returns None when filledQuantity is zero.

    A zero fill has no meaningful trade to record.
    """
    result = SchwabOrderNormalizer.normalize(_base_order(filledQuantity=0))

    assert result is None


async def test_normalize_uses_execution_price_fallback() -> None:
    """normalize() uses orderActivityCollection price when top-level price is absent.

    When the top-level ``price`` key is missing or zero, the normalizer
    falls back to the price reported in the first execution leg.
    """
    order = _base_order(price=0)
    order["orderActivityCollection"] = [
        {
            "executionLegs": [{"price": 155.50}],
        }
    ]

    result = SchwabOrderNormalizer.normalize(order)

    assert result is not None
    assert result.entry_price == Decimal("155.5")


async def test_normalize_no_valid_price() -> None:
    """normalize() returns None when neither top-level price nor fallback yields a value.

    The order has price=0 and an empty orderActivityCollection, so no
    valid entry price can be determined.
    """
    order = _base_order(price=0, orderActivityCollection=[])

    result = SchwabOrderNormalizer.normalize(order)

    assert result is None


async def test_normalize_invalid_datetime() -> None:
    """normalize() returns None when closeTime and enteredTime are unparseable.

    The normalizer cannot determine a trade timestamp without at least one
    parseable datetime field.
    """
    order = _base_order(closeTime="not-a-date", enteredTime=None)
    result = SchwabOrderNormalizer.normalize(order)

    assert result is None


async def test_normalize_option_asset_class() -> None:
    """normalize() maps assetType='OPTION' to AssetClass.OPTION.

    Verifies that the _ASSET_CLASS_MAP lookup for options works correctly.
    """
    order = _base_order()
    order["orderLegCollection"][0]["instrument"]["assetType"] = "OPTION"

    result = SchwabOrderNormalizer.normalize(order)

    assert result is not None
    assert result.asset_class == AssetClass.OPTION


async def test_normalize_unknown_asset_class() -> None:
    """normalize() defaults to AssetClass.EQUITY for an unrecognised assetType.

    Futures, Forex, Crypto, etc. are not in the _ASSET_CLASS_MAP so the
    normalizer falls back to EQUITY as the safe default.
    """
    order = _base_order()
    order["orderLegCollection"][0]["instrument"]["assetType"] = "FUTURE"

    result = SchwabOrderNormalizer.normalize(order)

    assert result is not None
    assert result.asset_class == AssetClass.EQUITY


async def test_normalize_broker_order_id() -> None:
    """normalize() sets broker_order_id from the orderId field.

    The broker_order_id is used for deduplication on subsequent sync runs.
    """
    result = SchwabOrderNormalizer.normalize(_base_order(orderId="98765"))

    assert result is not None
    assert result.broker_order_id == "98765"


async def test_normalize_market_order_type() -> None:
    """normalize() accepts MARKET orders in addition to LIMIT orders.

    Ensures that both supported order types pass the filter gate.
    """
    result = SchwabOrderNormalizer.normalize(_base_order(orderType="MARKET"))

    assert result is not None


async def test_normalize_timestamp_from_entered_time() -> None:
    """normalize() falls back to enteredTime when closeTime is absent.

    The normalizer accepts either timestamp field to determine the trade time.
    """
    order = _base_order()
    del order["closeTime"]
    order["enteredTime"] = "2024-03-10T14:00:00+00:00"

    result = SchwabOrderNormalizer.normalize(order)

    assert result is not None
    assert result.opened_at is not None
    assert result.opened_at.tzinfo is not None
    assert result.opened_at.year == 2024
