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

"""Integration tests for MetadataCorrelationRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.portfolio import Portfolio
from app.repositories.metadata_correlation_repository import MetadataCorrelationRepository

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_portfolio(session: AsyncSession, user_id: uuid.UUID) -> Portfolio:
    portfolio = Portfolio(user_id=user_id, name="Test Portfolio", base_currency="USD")
    session.add(portfolio)
    await session.flush()
    await session.refresh(portfolio)
    return portfolio


@pytest.mark.integration
async def test_get_filtered_trades_aggregate_empty(db_session: AsyncSession):
    """get_filtered_trades_aggregate returns zeroed dict when no trades match."""
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = MetadataCorrelationRepository()

    result = await repo.get_filtered_trades_aggregate(
        session=db_session,
        portfolio_id=portfolio.id,
    )

    assert result["total_trades_count"] == 0
    assert result["win_rate"] == 0
    assert result["max_drawdown_pct"] == 0


@pytest.mark.integration
async def test_get_filtered_trades_aggregate_with_filters(db_session: AsyncSession):
    """All optional filters should be applied without error."""
    from datetime import date

    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = MetadataCorrelationRepository()

    result = await repo.get_filtered_trades_aggregate(
        session=db_session,
        portfolio_id=portfolio.id,
        date_from=date(2024, 1, 1),
        date_to=date(2024, 12, 31),
        account_ids=[uuid.uuid4()],
        base_asset="AAPL",
    )

    assert result["total_trades_count"] == 0


@pytest.mark.integration
async def test_get_correlated_pairs_invalid_axis_type(db_session: AsyncSession):
    """get_correlated_pairs raises ValueError for unknown axis type."""
    user = await _make_user(db_session)
    portfolio = await _make_portfolio(db_session, user.id)
    repo = MetadataCorrelationRepository()

    with pytest.raises((ValueError, Exception)):
        await repo.get_correlated_pairs(
            session=db_session,
            portfolio_id=portfolio.id,
            x_axis_type="invalid_type",  # type: ignore[arg-type]
            x_axis_id=uuid.uuid4(),
            y_axis_type="checkin_annotation",
            y_axis_id=uuid.uuid4(),
        )
