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

"""Unit tests for FxRateService."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _make_service(repo=None):
    from app.services.fx_rate_service import FxRateService
    svc = FxRateService.__new__(FxRateService)
    svc._repo = repo or AsyncMock()
    return svc


_DATE = dt.date(2024, 1, 15)
_RATE = Decimal("0.92")


async def test_get_usd_to_eur_returns_cached_rate():
    mock_repo = AsyncMock()
    mock_repo.get_by_date = AsyncMock(return_value=_RATE)
    svc = _make_service(mock_repo)
    session = AsyncMock()

    with patch("app.services.fx_rate_service.fetch_ecb_rate") as mock_fetch:
        result = await svc.get_usd_to_eur(session, _DATE)

    assert result == _RATE
    mock_repo.get_by_date.assert_called_once_with(session, _DATE, "USD", "EUR")
    mock_fetch.assert_not_called()


async def test_get_usd_to_eur_fetches_and_caches_on_miss():
    mock_repo = AsyncMock()
    mock_repo.get_by_date = AsyncMock(return_value=None)
    mock_repo.upsert = AsyncMock()
    svc = _make_service(mock_repo)
    session = AsyncMock()

    with patch("app.services.fx_rate_service.fetch_ecb_rate", new=AsyncMock(return_value=_RATE)):
        result = await svc.get_usd_to_eur(session, _DATE)

    assert result == _RATE
    mock_repo.upsert.assert_called_once_with(session, _DATE, "USD", "EUR", _RATE)


async def test_get_usd_to_eur_returns_none_when_api_unavailable():
    mock_repo = AsyncMock()
    mock_repo.get_by_date = AsyncMock(return_value=None)
    mock_repo.upsert = AsyncMock()
    svc = _make_service(mock_repo)
    session = AsyncMock()

    with patch("app.services.fx_rate_service.fetch_ecb_rate", new=AsyncMock(return_value=None)):
        result = await svc.get_usd_to_eur(session, _DATE)

    assert result is None
    mock_repo.upsert.assert_not_called()


async def test_get_usd_to_eur_passes_correct_date_to_repo():
    specific_date = dt.date(2023, 6, 30)
    mock_repo = AsyncMock()
    mock_repo.get_by_date = AsyncMock(return_value=Decimal("0.88"))
    svc = _make_service(mock_repo)
    session = AsyncMock()

    with patch("app.services.fx_rate_service.fetch_ecb_rate"):
        await svc.get_usd_to_eur(session, specific_date)

    call_args = mock_repo.get_by_date.call_args
    assert call_args[0][1] == specific_date
