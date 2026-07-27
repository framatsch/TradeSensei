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

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.utils.conflict_detection import detect_duplicate_pairs

@dataclass
class _MockLeg:
    symbol: str
    executed_at: datetime
    direction: str
    quantity: Decimal
    price: Decimal
    origin: str
    source_id: str | None = None

def test_no_duplicate_pairs_empty():
    assert not detect_duplicate_pairs([])

def test_detect_duplicate_pairs_exact_match():
    dt = datetime(2026, 1, 1, 15, 30, 0)
    legs = [
        _MockLeg(symbol="AAPL", executed_at=dt, direction="LONG", quantity=Decimal("100"), price=Decimal("150"), origin="imported"),
        _MockLeg(symbol="AAPL", executed_at=dt, direction="LONG", quantity=Decimal("100"), price=Decimal("150"), origin="manual"),
    ]
    assert detect_duplicate_pairs(legs)

def test_detect_duplicate_pairs_diff_price():
    dt = datetime(2026, 1, 1, 15, 30, 0)
    legs = [
        _MockLeg(symbol="AAPL", executed_at=dt, direction="LONG", quantity=Decimal("100"), price=Decimal("150.05"), origin="imported"),
        _MockLeg(symbol="AAPL", executed_at=dt, direction="LONG", quantity=Decimal("100"), price=Decimal("150"), origin="manual"),
    ]
    assert not detect_duplicate_pairs(legs)

def test_detect_duplicate_pairs_linked_manual_ignored():
    dt = datetime(2026, 1, 1, 15, 30, 0)
    legs = [
        _MockLeg(symbol="AAPL", executed_at=dt, direction="LONG", quantity=Decimal("100"), price=Decimal("150"), origin="imported"),
        _MockLeg(symbol="AAPL", executed_at=dt, direction="LONG", quantity=Decimal("100"), price=Decimal("150"), origin="manual", source_id="some_id"),
    ]
    assert not detect_duplicate_pairs(legs)

def test_detect_duplicate_pairs_second_precision():
    dt1 = datetime(2026, 1, 1, 15, 30, 0, 100000)
    dt2 = datetime(2026, 1, 1, 15, 30, 0, 900000)
    legs = [
        _MockLeg(symbol="AAPL", executed_at=dt1, direction="LONG", quantity=Decimal("100"), price=Decimal("150"), origin="imported"),
        _MockLeg(symbol="AAPL", executed_at=dt2, direction="LONG", quantity=Decimal("100"), price=Decimal("150"), origin="manual"),
    ]
    assert detect_duplicate_pairs(legs)
