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

"""Utilities for taxonomy/annotation scope handling.

Scopes are stored as comma-separated strings (e.g. ``"trades,checkins"``).
Use :func:`scope_contains` everywhere instead of set-literal comparisons so
that multi-scope values are handled correctly.
"""

VALID_SCOPE_TOKENS: frozenset[str] = frozenset({"trades", "checkins", "playbook"})


def scope_contains(scope_str: str, target: str) -> bool:
    """Return True if *target* is one of the tokens in *scope_str*.

    Examples::

        scope_contains("trades,checkins", "trades")   # True
        scope_contains("trades,checkins", "playbook")  # False
        scope_contains("playbook", "playbook")         # True
    """
    parts = {p.strip() for p in scope_str.split(",") if p.strip()}
    return target in parts


def normalize_scope(scope_str: str) -> str:
    """Validate and normalise a comma-separated scope string.

    Raises :class:`ValueError` when an unknown token is present.
    Returns tokens sorted alphabetically so ``"trades,checkins"`` and
    ``"checkins,trades"`` are treated as the same value.
    """
    tokens = {p.strip() for p in scope_str.split(",") if p.strip()}
    if not tokens:
        raise ValueError("scope must contain at least one valid token")
    invalid = tokens - VALID_SCOPE_TOKENS
    if invalid:
        raise ValueError(f"Invalid scope token(s): {', '.join(sorted(invalid))}. Allowed: {', '.join(sorted(VALID_SCOPE_TOKENS))}")
    return ",".join(sorted(tokens))
