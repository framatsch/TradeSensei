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

"""Shared OCC (Options Clearing Corporation) symbol parser.

OCC option symbols encode the full contract specification in a fixed-width
string of the form::

    <UNDERLYING><YYMMDD><C|P><8-digit-strike>

where:

- ``UNDERLYING`` is the underlying ticker, left-padded with spaces so the
  total length before the 15-char suffix is at least 6 characters in the
  standard representation (e.g. ``QQQ   251003C00712000``).
- ``YYMMDD`` is the 6-digit expiry date (year, month, day).
- ``C`` or ``P`` is the option type (call or put).
- The 8-digit integer is ``strike × 1000`` (e.g. ``00712000`` → $712.000).

The 15-char suffix is always at the *end* of the symbol string, so any symbol
shorter than or equal to 15 characters cannot be an OCC option string.

Year window (matching ``frontend/lib/parseOccSymbol.ts``)::

    yy <= 50  →  2000 + yy
    yy >  50  →  1900 + yy

This module is deliberately dependency-light: it imports only from the Python
standard library so that Alembic migration scripts can import it without
pulling in the full application stack.
"""

from datetime import date
from decimal import Decimal

# The OCC suffix is always exactly 15 characters:
# YYMMDD (6) + C/P (1) + 8-digit strike (8) = 15
_OCC_SUFFIX_LEN: int = 15

# Year-window cutoff: yy <= 50 → 2000+yy, else 1900+yy
_OCC_YEAR_CUTOFF: int = 50


def parse_occ_option(
    symbol: str,
) -> tuple[Decimal | None, date | None, str | None]:
    """Parse an OCC option symbol into its typed contract components.

    Validates the 15-character suffix of ``symbol`` (all-digit expiry,
    ``C`` or ``P`` type character, all-digit strike).  Returns
    ``(None, None, None)`` for:

    - Equity or other non-option symbols (too short to contain the suffix).
    - Symbols whose 15-char suffix fails validation (e.g. an ``X`` instead
      of ``C``/``P``, or non-digit expiry/strike bytes).

    The year for the expiry date is resolved using the same window as the
    frontend ``parseOccSymbol.ts`` helper: ``yy <= 50 → 2000+yy``,
    ``yy > 50 → 1900+yy``.

    Strike is returned as a :class:`~decimal.Decimal` by dividing the raw
    8-digit integer by 1000 (e.g. ``00712000`` → ``Decimal('712.000')``).

    Args:
        symbol: The raw symbol string, potentially in OCC format.  Must
            already be upper-cased; leading/trailing whitespace is allowed
            and is stripped before the suffix is located.

    Returns:
        A 3-tuple ``(strike, expiry, option_type)`` where:

        - ``strike`` is a :class:`~decimal.Decimal` (e.g. ``Decimal('712.000')``).
        - ``expiry`` is a :class:`~datetime.date` (e.g. ``date(2025, 10, 3)``).
        - ``option_type`` is ``'C'`` or ``'P'``.

        All three elements are ``None`` when ``symbol`` is not a valid OCC
        option string.
    """
    if len(symbol) <= _OCC_SUFFIX_LEN:
        return None, None, None

    suffix_start = len(symbol) - _OCC_SUFFIX_LEN
    expiry_str = symbol[suffix_start : suffix_start + 6]
    type_char = symbol[suffix_start + 6]
    strike_str = symbol[suffix_start + 7 :]

    # Validate: expiry digits, type char, strike digits
    if not expiry_str.isdigit():
        return None, None, None
    if type_char not in ("C", "P"):
        return None, None, None
    if not strike_str.isdigit():
        return None, None, None

    # Parse expiry date with year-window logic
    yy = int(expiry_str[0:2])
    mm = int(expiry_str[2:4])
    dd = int(expiry_str[4:6])
    year = (2000 + yy) if yy <= _OCC_YEAR_CUTOFF else (1900 + yy)
    try:
        expiry = date(year, mm, dd)
    except ValueError:
        return None, None, None

    # Parse strike: raw integer / 1000
    strike = Decimal(strike_str) / Decimal(1000)

    return strike, expiry, type_char


def extract_occ_underlying(symbol: str) -> str:
    """Return the underlying ticker for an OCC-format option symbol.

    For any symbol long enough to contain the 15-char OCC suffix and whose
    suffix passes validation (all-digit expiry, ``C``/``P`` type character,
    all-digit strike), the underlying is everything *before* that suffix,
    stripped of leading/trailing spaces.

    Non-option symbols (too short, or suffix fails validation) are returned
    unchanged.

    This function replaces the private ``_extract_occ_underlying`` helper
    that previously lived only in ``app.utils.parsers.ibkr_xml``.  Both the
    IBKR and Schwab parsers now import from here, and the old private helper
    in ``ibkr_xml`` delegates to this implementation.

    Args:
        symbol: The raw symbol string, potentially in OCC format.

    Returns:
        The underlying ticker (e.g. ``'QQQ'``), or ``symbol`` unchanged if
        it is not a valid OCC option string.
    """
    if len(symbol) <= _OCC_SUFFIX_LEN:
        return symbol
    suffix_start = len(symbol) - _OCC_SUFFIX_LEN
    expiry_str = symbol[suffix_start : suffix_start + 6]
    type_char = symbol[suffix_start + 6]
    strike_str = symbol[suffix_start + 7 :]
    if expiry_str.isdigit() and type_char in ("C", "P") and strike_str.isdigit():
        return symbol[:suffix_start].strip()
    return symbol
