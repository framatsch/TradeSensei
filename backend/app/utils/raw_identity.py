"""Pure canonical raw execution identity helpers shared by import and preview."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal


def normalized_decimal(value: Decimal) -> str:
    """Return an exact scale-independent representation without context rounding."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def execution_fingerprint(
    executed_at: datetime,
    symbol: str,
    asset_class: str,
    conid: str | None,
    side: str,
    quantity: Decimal,
    price: Decimal,
    currency: str,
) -> str:
    """Hash only immutable fill identity fields, using an unambiguous encoding."""
    values = [
        executed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        symbol,
        asset_class,
        conid,
        side,
        normalized_decimal(quantity),
        normalized_decimal(price),
        currency,
    ]
    return hashlib.sha256(json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def stamped_raw_id(raw_id: str, user_id: str, account_id: str | None, account_scoped: bool) -> str:
    """Namespace adapter-local identity identically for preview and persistence."""
    if account_scoped:
        if account_id is None:
            raise ValueError("Account is required for account-scoped identity")
        broker, identity = raw_id.split(":", 1)
        return f"{user_id}:{broker}:{account_id}:{identity}"
    return raw_id if raw_id.startswith(f"{user_id}:") else f"{user_id}:{raw_id}"
