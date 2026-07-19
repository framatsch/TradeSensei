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

"""Unit tests for the shared OCC symbol parser (app.utils.occ)."""

from datetime import date
from decimal import Decimal

import pytest

from app.utils.occ import extract_occ_underlying, parse_occ_option


class TestParseOccOption:
    """Tests for :func:`~app.utils.occ.parse_occ_option`."""

    def test_call_option(self) -> None:
        """QQQ call: strike=712.000, expiry=2025-10-03, type='C'."""
        strike, expiry, option_type = parse_occ_option("QQQ   251003C00712000")
        assert strike == Decimal("712.000")
        assert expiry == date(2025, 10, 3)
        assert option_type == "C"

    def test_put_option(self) -> None:
        """AAPL put: strike=150.000, expiry=2026-03-20, type='P'."""
        strike, expiry, option_type = parse_occ_option("AAPL  260320P00150000")
        assert strike == Decimal("150.000")
        assert expiry == date(2026, 3, 20)
        assert option_type == "P"

    def test_equity_symbol_returns_nones(self) -> None:
        """Plain equity ticker is too short — all None."""
        strike, expiry, option_type = parse_occ_option("AAPL")
        assert strike is None
        assert expiry is None
        assert option_type is None

    def test_malformed_type_char_returns_nones(self) -> None:
        """'X' instead of 'C'/'P' in type position → all None."""
        strike, expiry, option_type = parse_occ_option("QQQ   251003X00712000")
        assert strike is None
        assert expiry is None
        assert option_type is None

    def test_exactly_15_chars_is_not_option(self) -> None:
        """A symbol exactly 15 chars long has no room for an underlying."""
        symbol = "251003C00712000"  # exactly 15 chars
        strike, expiry, option_type = parse_occ_option(symbol)
        assert strike is None
        assert expiry is None
        assert option_type is None

    def test_year_window_gt_50(self) -> None:
        """yy=99 should map to 1999, not 2099."""
        # Construct a symbol: underlying 'X     ', expiry 990101, call, strike 00100000
        symbol = "X     990101C00100000"
        strike, expiry, option_type = parse_occ_option(symbol)
        assert option_type == "C"
        assert expiry is not None
        assert expiry.year == 1999

    def test_year_window_at_cutoff(self) -> None:
        """yy=50 should map to 2050 (inclusive boundary)."""
        symbol = "X     500101C00100000"
        strike, expiry, option_type = parse_occ_option(symbol)
        assert expiry is not None
        assert expiry.year == 2050

    def test_strike_precision(self) -> None:
        """Strike 00712500 → Decimal('712.500') — fractional part preserved."""
        strike, _, _ = parse_occ_option("QQQ   251003C00712500")
        assert strike == Decimal("712.500")

    def test_non_digit_expiry_returns_nones(self) -> None:
        """Non-digit expiry bytes make the suffix invalid."""
        # Replace two digit chars in expiry with letters
        symbol = "AAPL  AB0320P00150000"
        strike, expiry, option_type = parse_occ_option(symbol)
        assert strike is None
        assert expiry is None
        assert option_type is None

    def test_invalid_date_returns_nones(self) -> None:
        """A syntactically valid but calendrically invalid date → None."""
        # Month 13 is invalid
        symbol = "AAPL  251399P00150000"
        strike, expiry, option_type = parse_occ_option(symbol)
        assert strike is None
        assert expiry is None
        assert option_type is None


class TestExtractOccUnderlying:
    """Tests for :func:`~app.utils.occ.extract_occ_underlying`."""

    def test_call_occ_symbol(self) -> None:
        """QQQ call OCC symbol → 'QQQ'."""
        assert extract_occ_underlying("QQQ   251003C00712000") == "QQQ"

    def test_equity_symbol_unchanged(self) -> None:
        """Plain equity ticker → returned unchanged."""
        assert extract_occ_underlying("AAPL") == "AAPL"

    def test_aapl_put_occ_symbol(self) -> None:
        """AAPL put OCC symbol → 'AAPL'."""
        assert extract_occ_underlying("AAPL  260320P00150000") == "AAPL"

    def test_malformed_type_char_unchanged(self) -> None:
        """Malformed type char → symbol returned as-is."""
        sym = "QQQ   251003X00712000"
        assert extract_occ_underlying(sym) == sym

    def test_strips_spaces_from_underlying(self) -> None:
        """Spaces between ticker and suffix are stripped."""
        result = extract_occ_underlying("QQQ   251003C00712000")
        assert result == "QQQ"
        assert " " not in result

    @pytest.mark.parametrize(
        "symbol,expected",
        [
            ("AAPL  230120C00150000", "AAPL"),
            ("SPY   251219P00450000", "SPY"),
            ("TSLA  260115C00250000", "TSLA"),
        ],
    )
    def test_parametrized_underlyings(self, symbol: str, expected: str) -> None:
        """Parametrised parity check against the old IBKR private helper."""
        assert extract_occ_underlying(symbol) == expected
