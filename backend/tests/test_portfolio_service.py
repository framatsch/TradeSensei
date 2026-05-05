"""Unit tests for PortfolioService."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import PortfolioValidationError
from app.models.portfolio import Portfolio
from app.schemas.portfolio import PortfolioCreate, PortfolioRead, PortfolioUpdate
from app.services.portfolio_service import PortfolioService


def _make_portfolio(
    *,
    name: str = "Main",
    base_currency: str = "USD",
    user_id: uuid.UUID | None = None,
) -> Portfolio:
    item = Portfolio()
    item.id = uuid.uuid4()  # type: ignore[assignment]
    item.user_id = user_id if user_id is not None else uuid.uuid4()  # type: ignore[assignment]
    item.name = name  # type: ignore[assignment]
    item.base_currency = base_currency  # type: ignore[assignment]
    item.color_hex = "#123456"  # type: ignore[assignment]
    item.created_at = datetime.now(UTC)  # type: ignore[assignment]
    item.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    return item


@pytest.fixture()
def service(mock_session: AsyncMock) -> PortfolioService:
    return PortfolioService(mock_session)


@pytest.mark.unit
async def test_create_portfolio_rejects_duplicate_name(
    service: PortfolioService,
) -> None:
    user_id = uuid.uuid4()
    service._repo.get_by_name = AsyncMock(return_value=_make_portfolio(user_id=user_id))  # type: ignore[method-assign]

    with pytest.raises(PortfolioValidationError) as exc:
        await service.create_portfolio(
            user_id,
            PortfolioCreate(name="Main", base_currency="USD", color_hex="#123456"),
        )

    

@pytest.mark.unit
async def test_create_portfolio_success_returns_read(service: PortfolioService) -> None:
    user_id = uuid.uuid4()
    created = _make_portfolio(name="Growth", base_currency="EUR", user_id=user_id)
    service._repo.get_by_name = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service._repo.create = AsyncMock(return_value=created)  # type: ignore[method-assign]

    result = await service.create_portfolio(
        user_id,
        PortfolioCreate(name="Growth", base_currency="EUR", color_hex="#654321"),
    )

    assert isinstance(result, PortfolioRead)
    assert result.name == "Growth"
    assert result.base_currency == "EUR"
    service._session.commit.assert_awaited_once()


@pytest.mark.unit
async def test_update_portfolio_rejects_base_currency_change_when_trades_exist(
    service: PortfolioService,
) -> None:
    user_id = uuid.uuid4()
    existing = _make_portfolio(name="Main", base_currency="USD", user_id=user_id)
    service._repo.get_by_id = AsyncMock(return_value=existing)  # type: ignore[method-assign]
    service._repo.has_trades = AsyncMock(return_value=True)  # type: ignore[method-assign]

    with pytest.raises(PortfolioValidationError) as exc:
        await service.update_portfolio(
            existing.id,
            user_id,
            PortfolioUpdate(base_currency="EUR"),
        )

    

@pytest.mark.unit
async def test_update_portfolio_rejects_duplicate_name(
    service: PortfolioService,
) -> None:
    user_id = uuid.uuid4()
    existing = _make_portfolio(name="Main", base_currency="USD", user_id=user_id)
    duplicate = _make_portfolio(name="Other", base_currency="USD", user_id=user_id)
    service._repo.get_by_id = AsyncMock(return_value=existing)  # type: ignore[method-assign]
    service._repo.get_by_name = AsyncMock(return_value=duplicate)  # type: ignore[method-assign]

    with pytest.raises(PortfolioValidationError) as exc:
        await service.update_portfolio(
            existing.id,
            user_id,
            PortfolioUpdate(name="Other"),
        )

    

@pytest.mark.unit
async def test_delete_portfolio_rejects_when_accounts_linked(
    service: PortfolioService,
) -> None:
    user_id = uuid.uuid4()
    existing = _make_portfolio(name="Main", base_currency="USD", user_id=user_id)
    service._repo.get_by_id = AsyncMock(return_value=existing)  # type: ignore[method-assign]
    service._repo.has_accounts = AsyncMock(return_value=True)  # type: ignore[method-assign]

    with pytest.raises(PortfolioValidationError) as exc:
        await service.delete_portfolio(existing.id, user_id)

    