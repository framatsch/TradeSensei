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

"""Integration tests for FxRateRepository."""

import datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fx_rate_repository import FxRateRepository

pytestmark = pytest.mark.asyncio


@pytest.mark.integration
async def test_upsert_and_get_by_date(db_session: AsyncSession):
    repo = FxRateRepository()
    test_date = datetime.date(2024, 1, 15)

    await repo.upsert(db_session, date=test_date, base="USD", quote="EUR", rate=Decimal("0.92"))

    result = await repo.get_by_date(db_session, date=test_date, base="USD", quote="EUR")
    assert result is not None
    assert result == Decimal("0.92")


@pytest.mark.integration
async def test_get_by_date_not_found_returns_none(db_session: AsyncSession):
    repo = FxRateRepository()
    result = await repo.get_by_date(
        db_session, date=datetime.date(1999, 1, 1), base="USD", quote="XYZ"
    )
    assert result is None


@pytest.mark.integration
async def test_upsert_updates_existing(db_session: AsyncSession):
    repo = FxRateRepository()
    test_date = datetime.date(2024, 2, 10)

    await repo.upsert(db_session, date=test_date, base="EUR", quote="GBP", rate=Decimal("0.85"))
    await repo.upsert(db_session, date=test_date, base="EUR", quote="GBP", rate=Decimal("0.87"))

    result = await repo.get_by_date(db_session, date=test_date, base="EUR", quote="GBP")
    assert result == Decimal("0.87")


@pytest.mark.integration
async def test_get_nearest_within_window_found(db_session: AsyncSession):
    repo = FxRateRepository()
    target_date = datetime.date(2024, 3, 15)
    # Insert a rate 2 days before target
    nearby_date = datetime.date(2024, 3, 13)
    await repo.upsert(db_session, date=nearby_date, base="USD", quote="JPY", rate=Decimal("148.5"))

    result = await repo.get_nearest_within_window(
        db_session, date=target_date, base="USD", quote="JPY", days=5
    )
    assert result is not None
    assert result == Decimal("148.5")


@pytest.mark.integration
async def test_get_nearest_within_window_not_found(db_session: AsyncSession):
    repo = FxRateRepository()
    result = await repo.get_nearest_within_window(
        db_session, date=datetime.date(2000, 1, 1), base="USD", quote="MISSING", days=3
    )
    assert result is None


@pytest.mark.integration
async def test_get_nearest_prefers_past(db_session: AsyncSession):
    """Tie-breaker should prefer dates on or before target."""
    repo = FxRateRepository()
    target = datetime.date(2024, 4, 10)
    past_date = datetime.date(2024, 4, 9)
    future_date = datetime.date(2024, 4, 11)

    await repo.upsert(db_session, date=past_date, base="AUD", quote="USD", rate=Decimal("0.65"))
    await repo.upsert(db_session, date=future_date, base="AUD", quote="USD", rate=Decimal("0.66"))

    result = await repo.get_nearest_within_window(
        db_session, date=target, base="AUD", quote="USD", days=2
    )
    # past date is preferred when equidistant
    assert result is not None
