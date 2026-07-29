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

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.portfolios import _get_service
from app.core.exceptions import PortfolioNotFoundError, PortfolioValidationError
from app.schemas.portfolio import PortfolioRead

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


def make_portfolio_read() -> PortfolioRead:
    return PortfolioRead(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Portfolio",
        base_currency="USD",
        color_hex="#ffffff",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


async def test_list_portfolios(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio = make_portfolio_read()
    override_dependency.list_portfolios.return_value = [portfolio]
    resp = await client.get("/api/v1/portfolios", headers=primary_user["headers"])
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


async def test_create_portfolio_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio = make_portfolio_read()
    override_dependency.create_portfolio.return_value = portfolio
    resp = await client.post("/api/v1/portfolios", headers=primary_user["headers"], json={"name": "New Port", "base_currency": "USD"})
    assert resp.status_code == 201


async def test_create_portfolio_validation_error(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.create_portfolio.side_effect = PortfolioValidationError("conflict")
    resp = await client.post("/api/v1/portfolios", headers=primary_user["headers"], json={"name": "Conflict", "base_currency": "USD"})
    assert resp.status_code == 409


async def test_get_portfolio_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio = make_portfolio_read()
    override_dependency.get_portfolio.return_value = portfolio
    resp = await client.get(f"/api/v1/portfolios/{portfolio.id}", headers=primary_user["headers"])
    assert resp.status_code == 200


async def test_get_portfolio_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.get_portfolio.side_effect = PortfolioNotFoundError("not found")
    resp = await client.get(f"/api/v1/portfolios/{uuid.uuid4()}", headers=primary_user["headers"])
    assert resp.status_code == 404


async def test_update_portfolio_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio = make_portfolio_read()
    override_dependency.update_portfolio.return_value = portfolio
    resp = await client.patch(f"/api/v1/portfolios/{portfolio.id}", headers=primary_user["headers"], json={"name": "Updated Port"})
    assert resp.status_code == 200


async def test_update_portfolio_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.update_portfolio.side_effect = PortfolioNotFoundError("not found")
    resp = await client.patch(f"/api/v1/portfolios/{uuid.uuid4()}", headers=primary_user["headers"], json={"name": "Updated Port"})
    assert resp.status_code == 404


async def test_update_portfolio_validation_error_422(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.update_portfolio.side_effect = PortfolioValidationError("base_currency cannot be changed")
    resp = await client.patch(f"/api/v1/portfolios/{uuid.uuid4()}", headers=primary_user["headers"], json={"base_currency": "EUR"})
    assert resp.status_code == 422


async def test_update_portfolio_validation_error_409(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.update_portfolio.side_effect = PortfolioValidationError("name conflict")
    resp = await client.patch(f"/api/v1/portfolios/{uuid.uuid4()}", headers=primary_user["headers"], json={"name": "Conflict"})
    assert resp.status_code == 409


async def test_delete_portfolio_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.delete_portfolio.return_value = None
    resp = await client.delete(f"/api/v1/portfolios/{uuid.uuid4()}", headers=primary_user["headers"])
    assert resp.status_code == 204


async def test_delete_portfolio_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.delete_portfolio.side_effect = PortfolioNotFoundError("not found")
    resp = await client.delete(f"/api/v1/portfolios/{uuid.uuid4()}", headers=primary_user["headers"])
    assert resp.status_code == 404


async def test_delete_portfolio_validation_error(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.delete_portfolio.side_effect = PortfolioValidationError("conflict")
    resp = await client.delete(f"/api/v1/portfolios/{uuid.uuid4()}", headers=primary_user["headers"])
    assert resp.status_code == 409
