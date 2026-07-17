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

"""Unit tests for MetadataCorrelationService."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.metadata_correlation_service import MetadataCorrelationService

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_PORTFOLIO_ID = uuid.uuid4()
_AXIS_ID = uuid.uuid4()
_OTHER_AXIS_ID = uuid.uuid4()


def _make_service():
    svc = MetadataCorrelationService.__new__(MetadataCorrelationService)
    svc.repository = AsyncMock()
    return svc


def _mock_session():
    session = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# get_correlation - same axis validation
# ---------------------------------------------------------------------------


async def test_get_correlation_raises_when_x_and_y_are_same():
    svc = _make_service()
    session = _mock_session()

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_correlation(
            session=session,
            portfolio_id=_PORTFOLIO_ID,
            x_axis_type="trade_annotation",
            x_axis_id=_AXIS_ID,
            y_axis_type="trade_annotation",
            y_axis_id=_AXIS_ID,
        )

    assert exc_info.value.status_code == 422


async def test_get_correlation_different_types_same_id_is_valid():
    """Same UUID but different types is allowed."""
    svc = _make_service()
    session = _mock_session()

    # Mock the _get_axis_meta to avoid DB calls
    async def _fake_get_axis_meta(sess, axis_type, axis_id):
        return "string", "Name"

    svc._get_axis_meta = _fake_get_axis_meta

    svc.repository.get_correlated_pairs = AsyncMock(return_value=[])
    svc.repository.get_filtered_trades_aggregate = AsyncMock(return_value={
        "win_rate": Decimal("0.5"),
        "max_drawdown_pct": Decimal("0"),
        "total_trades_count": 0,
    })

    # Should not raise — x_axis_type != y_axis_type even though same ID
    result = await svc.get_correlation(
        session=session,
        portfolio_id=_PORTFOLIO_ID,
        x_axis_type="trade_annotation",
        x_axis_id=_AXIS_ID,
        y_axis_type="trade_taxonomy",  # Different type
        y_axis_id=_AXIS_ID,
    )
    assert result is not None


# ---------------------------------------------------------------------------
# _get_axis_meta - taxonomy paths
# ---------------------------------------------------------------------------


async def test_get_axis_meta_raises_404_when_taxonomy_not_found():
    svc = _make_service()
    session = AsyncMock()

    # Mock session.execute to return no taxonomy
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await svc._get_axis_meta(session, "trade_taxonomy", _AXIS_ID)

    assert exc_info.value.status_code == 404


async def test_get_axis_meta_raises_422_when_checkin_taxonomy_has_wrong_scope():
    svc = _make_service()
    session = AsyncMock()

    mock_tax = MagicMock()
    mock_tax.name = "Test"
    mock_tax.scope = "trades"  # Wrong scope for checkin_taxonomy

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_tax)
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await svc._get_axis_meta(session, "checkin_taxonomy", _AXIS_ID)

    assert exc_info.value.status_code == 422


async def test_get_axis_meta_raises_422_when_trade_taxonomy_has_wrong_scope():
    svc = _make_service()
    session = AsyncMock()

    mock_tax = MagicMock()
    mock_tax.name = "Test"
    mock_tax.scope = "checkins"  # Wrong scope for trade_taxonomy

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_tax)
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await svc._get_axis_meta(session, "trade_taxonomy", _AXIS_ID)

    assert exc_info.value.status_code == 422


async def test_get_axis_meta_raises_404_when_annotation_not_found():
    svc = _make_service()
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await svc._get_axis_meta(session, "trade_annotation", _AXIS_ID)

    assert exc_info.value.status_code == 404


async def test_get_axis_meta_raises_422_when_checkin_annotation_has_wrong_scope():
    svc = _make_service()
    session = AsyncMock()

    mock_ad = MagicMock()
    mock_ad.name = "Test"
    mock_ad.scope = "trades"  # Wrong for checkin_annotation
    mock_ad.type = "int"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_ad)
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await svc._get_axis_meta(session, "checkin_annotation", _AXIS_ID)

    assert exc_info.value.status_code == 422


async def test_get_axis_meta_returns_correct_type_for_int_annotation():
    svc = _make_service()
    session = AsyncMock()

    mock_ad = MagicMock()
    mock_ad.name = "Score"
    mock_ad.scope = "trades"
    mock_ad.type = "int"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_ad)
    session.execute = AsyncMock(return_value=mock_result)

    data_type, name = await svc._get_axis_meta(session, "trade_annotation", _AXIS_ID)

    assert data_type == "number"
    assert name == "Score"


async def test_get_axis_meta_returns_correct_type_for_bool_annotation():
    svc = _make_service()
    session = AsyncMock()

    mock_ad = MagicMock()
    mock_ad.name = "Flag"
    mock_ad.scope = "trades"
    mock_ad.type = "bool"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_ad)
    session.execute = AsyncMock(return_value=mock_result)

    data_type, name = await svc._get_axis_meta(session, "trade_annotation", _AXIS_ID)

    assert data_type == "boolean"


async def test_get_axis_meta_returns_string_for_string_enum():
    svc = _make_service()
    session = AsyncMock()

    mock_ad = MagicMock()
    mock_ad.name = "Category"
    mock_ad.scope = "trades"
    mock_ad.type = "string_enum"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_ad)
    session.execute = AsyncMock(return_value=mock_result)

    data_type, name = await svc._get_axis_meta(session, "trade_annotation", _AXIS_ID)

    assert data_type == "string"


# ---------------------------------------------------------------------------
# get_correlation - full flow
# ---------------------------------------------------------------------------


async def test_get_correlation_converts_numeric_values():
    svc = _make_service()
    session = AsyncMock()

    async def _fake_get_axis_meta(sess, axis_type, axis_id):
        return "number", "Score"

    svc._get_axis_meta = _fake_get_axis_meta

    pairs = [
        {
            "x_value": "3.5",
            "y_value": "1.2",
            "date": date(2024, 1, 15),
            "trade_id": uuid.uuid4(),
            "trade_symbol": "AAPL",
            "trade_pnl": Decimal("100"),
            "x_label": None,
            "y_label": None,
        }
    ]

    svc.repository.get_correlated_pairs = AsyncMock(return_value=pairs)
    svc.repository.get_filtered_trades_aggregate = AsyncMock(return_value={
        "win_rate": Decimal("0.6"),
        "max_drawdown_pct": Decimal("-0.1"),
        "total_trades_count": 10,
    })

    result = await svc.get_correlation(
        session=session,
        portfolio_id=_PORTFOLIO_ID,
        x_axis_type="trade_annotation",
        x_axis_id=_AXIS_ID,
        y_axis_type="trade_annotation",
        y_axis_id=_OTHER_AXIS_ID,
    )

    assert len(result.data_points) == 1
    assert result.data_points[0].x_value == 3.5
    assert result.data_points[0].y_value == 1.2
    assert result.kpis.matched_count == 1
    assert result.kpis.total_trades_count == 10
