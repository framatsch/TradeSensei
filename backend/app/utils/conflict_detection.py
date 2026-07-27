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

"""Unlinked-duplicate conflict detection for the FIFO trade projection.

See the ``execution-overwrite-protection`` capability spec: when a user
creates a manual replacement execution for a broken imported fill without
linking it to the original broker transaction, subsequent imports
re-materialise the imported leg and the position duplicates. The trade-level
``has_conflict`` flag surfaces this so the UI can prompt the user to resolve
it (delete one leg or link the manual leg to the broker transaction).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol


class _ConflictLeg(Protocol):
    """Structural type for legs considered in duplicate detection."""

    @property
    def symbol(self) -> str: ...
    @property
    def executed_at(self) -> datetime: ...
    @property
    def direction(self) -> object: ...  # Direction enum or str
    @property
    def quantity(self) -> Decimal: ...
    @property
    def price(self) -> Decimal: ...
    @property
    def origin(self) -> str: ...
    @property
    def source_id(self) -> str | None: ...


def _second_precision(value: datetime) -> datetime:
    """Truncate a datetime to whole seconds for the duplicate key."""
    return value.replace(microsecond=0)


def _direction_value(value: object) -> object:
    """Normalise a Direction enum to its string value for comparison."""
    return getattr(value, "value", value)


def detect_duplicate_pairs(legs: Sequence[_ConflictLeg]) -> bool:
    """Return True iff at least one unlinked duplicate pair exists.

    A duplicate pair is an ``origin='imported'`` leg and an ``origin='manual'``
    leg with ``source_id=NULL`` on the same trade that share the five-field
    key ``(symbol, executed_at to the second, direction, quantity, price)``.
    Linked manual executions (``source_id`` set) are stand-ins for the
    imported fill and are never treated as duplicates.

    The check is O(N) in the number of legs: imported keys are hashed once,
    then each unlinked manual leg probes the set.

    Args:
        legs: The trade's current (non-deleted) execution legs.

    Returns:
        True when at least one duplicate pair exists, False otherwise.
    """
    imported_keys: set[tuple[object, ...]] = set()
    for leg in legs:
        if leg.origin == "imported":
            imported_keys.add(
                (
                    leg.symbol,
                    _second_precision(leg.executed_at),
                    _direction_value(leg.direction),
                    leg.quantity,
                    leg.price,
                )
            )

    if not imported_keys:
        return False

    for leg in legs:
        if leg.origin == "manual" and leg.source_id is None:
            key = (
                leg.symbol,
                _second_precision(leg.executed_at),
                _direction_value(leg.direction),
                leg.quantity,
                leg.price,
            )
            if key in imported_keys:
                return True
    return False
