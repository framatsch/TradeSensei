"""Normalizes raw Schwab order JSON into :class:`~app.schemas.trade.TradeCreate`.

Only FILLED MARKET/LIMIT orders are converted.  Orders with unsupported
status or type are returned as ``None`` and are silently skipped by the
caller.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate

# Schwab order statuses considered complete / eligible for import
_SUPPORTED_STATUSES: frozenset[str] = frozenset({"FILLED"})

# Schwab order types that map to a simple entry/exit price
_SUPPORTED_ORDER_TYPES: frozenset[str] = frozenset({"MARKET", "LIMIT"})

# Schwab instruction → Direction mapping
_DIRECTION_MAP: dict[str, Direction] = {
    "BUY": Direction.LONG,
    "SELL": Direction.SHORT,
}

# Schwab asset type → AssetClass mapping
_ASSET_CLASS_MAP: dict[str, AssetClass] = {
    "EQUITY": AssetClass.EQUITY,
    "OPTION": AssetClass.OPTION,
}


def _parse_decimal(value: Any) -> Decimal | None:
    """Safely convert a value to :class:`~decimal.Decimal`.

    Args:
        value: Raw value from the order JSON.

    Returns:
        A :class:`~decimal.Decimal` instance, or ``None`` if conversion
        fails.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    """Safely parse an ISO-8601 datetime string to a timezone-aware UTC object.

    Args:
        value: Raw value from the order JSON (expected to be a string).

    Returns:
        A timezone-aware :class:`~datetime.datetime` in UTC, or ``None``
        if parsing fails.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        return None


class SchwabOrderNormalizer:
    """Converts a Schwab order JSON dict into a :class:`~app.schemas.trade.TradeCreate`.

    This is a pure-data transformer: no IO, no side effects.
    """

    @staticmethod
    def normalize(order_json: dict[str, Any]) -> TradeCreate | None:
        """Normalize a Schwab order JSON dict into a TradeCreate schema.

        Returns ``None`` for any order that cannot be meaningfully imported
        (wrong status, unsupported order type, missing required fields).

        Args:
            order_json: A raw order dictionary as returned by the Schwab API.

        Returns:
            A populated :class:`~app.schemas.trade.TradeCreate` ready for
            persistence, or ``None`` if the order should be skipped.
        """
        # Only import filled orders
        status = order_json.get("status")
        if status not in _SUPPORTED_STATUSES:
            return None

        # Only import market / limit order types
        order_type = order_json.get("orderType")
        if order_type not in _SUPPORTED_ORDER_TYPES:
            return None

        # --- Symbol --------------------------------------------------------
        symbol: str | None = None
        order_leg_collection = order_json.get("orderLegCollection") or []
        instruction: str | None = None
        asset_type: str | None = None

        if isinstance(order_leg_collection, list) and order_leg_collection:
            first_leg: dict[str, Any] = order_leg_collection[0]
            instruction = first_leg.get("instruction")
            instrument: dict[str, Any] = first_leg.get("instrument") or {}
            symbol = instrument.get("symbol")
            asset_type = instrument.get("assetType")

        # Fall back to top-level symbol field for simpler order shapes
        if not symbol:
            symbol = order_json.get("symbol")

        if not symbol:
            return None

        # --- Direction -----------------------------------------------------
        direction = _DIRECTION_MAP.get(str(instruction or ""))
        if direction is None:
            return None

        # --- Asset class ---------------------------------------------------
        asset_class = _ASSET_CLASS_MAP.get(str(asset_type or ""), AssetClass.EQUITY)

        # --- Quantity ------------------------------------------------------
        quantity = _parse_decimal(order_json.get("filledQuantity"))
        if quantity is None or quantity <= Decimal("0"):
            return None

        # --- Price ---------------------------------------------------------
        price = _parse_decimal(order_json.get("price"))
        if price is None or price <= Decimal("0"):
            # Try average fill price from order activity
            order_activity = order_json.get("orderActivityCollection") or []
            if isinstance(order_activity, list) and order_activity:
                exec_legs = order_activity[0].get("executionLegs") or []
                if isinstance(exec_legs, list) and exec_legs:
                    price = _parse_decimal(exec_legs[0].get("price"))
        if price is None or price <= Decimal("0"):
            return None

        # --- Timestamps ---------------------------------------------------
        close_time_raw = order_json.get("closeTime") or order_json.get("enteredTime")
        trade_time = _parse_datetime(close_time_raw)
        if trade_time is None:
            return None

        # --- Broker order ID ---------------------------------------------
        broker_order_id = str(order_json.get("orderId", "")) or None

        return TradeCreate(
            symbol=symbol,
            direction=direction,
            asset_class=asset_class,
            quantity=quantity,
            entry_price=price,
            exit_price=price,
            opened_at=trade_time,
            closed_at=trade_time,
            currency="USD",
            broker_order_id=broker_order_id,
        )
