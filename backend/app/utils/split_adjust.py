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

"""Helpers for split-adjusted execution values.

This module intentionally mirrors the split math used by
``app/utils/parsers/aggregator.py:_apply_split_event``:

- ``quantity *= ratio``
- ``price /= ratio``
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.corporate_action import CorporateAction


def split_adjust_execution_values(
    raw_price: Decimal,
    raw_quantity: Decimal,
    executed_at: datetime,
    symbol: str,
    conid: str | None,
    corporate_actions: Sequence[CorporateAction],
) -> tuple[Decimal, Decimal]:
    """Return split-adjusted execution values for chart alignment.

    Applies every matching corporate action in chronological order using
    ``Decimal`` arithmetic.
    """
    executed_date_utc = executed_at.astimezone(UTC).date()

    applicable_actions = [
        action
        for action in corporate_actions
        if _matches_action(action=action, symbol=symbol, conid=conid)
        and action.date > executed_date_utc
    ]
    if not applicable_actions:
        return raw_price, raw_quantity

    ratio_product = Decimal("1")
    for action in sorted(applicable_actions, key=lambda item: item.date):
        ratio_product *= action.ratio

    if ratio_product == Decimal("1"):
        return raw_price, raw_quantity

    return raw_price / ratio_product, raw_quantity * ratio_product


def _matches_action(
    action: CorporateAction,
    symbol: str,
    conid: str | None,
) -> bool:
    """Check whether a corporate action applies to one execution leg."""
    if action.symbol == symbol:
        return True

    if conid is None:
        return False

    return conid in {action.old_conid, action.new_conid}
