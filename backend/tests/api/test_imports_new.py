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
from app.core.dependencies import require_portfolio_owner
from typing import Any
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError

import pytest
from httpx import AsyncClient

from app.api.v1.imports import _get_service
from app.core.deps import get_session_with_rls
from app.utils.parsers.factory import BrokerType
from app.schemas.imports import ImportResult, FreshStartResult

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_service():
    mock = AsyncMock()
    return mock

@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    app.dependency_overrides[require_portfolio_owner] = lambda: None
    app.dependency_overrides[get_session_with_rls] = lambda: AsyncMock()
    yield mock_service
    app.dependency_overrides.clear()

async def test_upload_import_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    mock_result = ImportResult(
        broker="ibkr",
        filename="test.xml",
        trades_parsed=5,
        trades_created=5,
        trades_skipped=0,
        raw_transactions_created=5,
        raw_suppressed_skipped=0,
        raw_deleted_skipped=0,
        warnings=[]
    )
    override_dependency.import_file.return_value = mock_result
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            data={"account_id": str(account_id), "overwrite_manually_edited": "false"},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 200
    assert response.json()["data"]["trades_parsed"] == 5

async def test_upload_import_account_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    from app.core.exceptions import AccountNotFoundError
    
    with patch("app.api.v1.imports._validate_account_import", side_effect=AccountNotFoundError("Not found")):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            data={"account_id": str(account_id)},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 404

async def test_upload_import_not_allowed(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    from app.core.exceptions import ImportNotAllowedError
    
    with patch("app.api.v1.imports._validate_account_import", side_effect=ImportNotAllowedError("Not allowed")):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            data={"account_id": str(account_id)},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 422

async def test_upload_import_file_too_large(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    large_content = b"0" * (21 * 1024 * 1024)
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        with patch("app.api.v1.imports.IMPORT_MAX_FILE_SIZE_MB", 20):
            response = await client.post(
                f"/api/v1/portfolios/{portfolio_id}/imports/upload",
                data={"account_id": str(account_id)},
                files={"file": ("test.xml", large_content, "text/xml")},
                headers=primary_user["headers"]
            )
        
    assert response.status_code == 413

async def test_upload_import_parse_error(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    from app.core.exceptions import ImportParseError
    override_dependency.import_file.side_effect = ImportParseError("Parse error")
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            data={"account_id": str(account_id)},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 400

async def test_upload_import_account_mismatch(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    from app.core.exceptions import ImportAccountMismatchError
    override_dependency.import_file.side_effect = ImportAccountMismatchError("Mismatch")
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            data={"account_id": str(account_id)},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 422

async def test_upload_import_validation_error(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    from pydantic import ValidationError
    # We just need any validation error for mock
    override_dependency.import_file.side_effect = ValidationError.from_exception_data(
        title="Test", line_errors=[]
    )
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            data={"account_id": str(account_id)},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 400

async def test_upload_import_general_exception(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    override_dependency.import_file.side_effect = Exception("General error")
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/upload",
            data={"account_id": str(account_id)},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 400

async def test_fresh_start_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    mock_result = FreshStartResult(
        account_id=account_id,
        executions_deleted=5,
        trades_deleted=5,
        import_result=ImportResult(
            broker="ibkr",
            filename="test.xml",
            trades_parsed=5,
            trades_created=5,
            trades_skipped=0,
            raw_transactions_created=5,
            raw_suppressed_skipped=0,
            raw_deleted_skipped=0,
            warnings=[]
        )
    )
    override_dependency.fresh_start_import.return_value = mock_result
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/{account_id}/fresh-start",
            data={"acknowledged": "true"},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 200
    assert response.json()["data"]["executions_deleted"] == 5

async def test_fresh_start_not_acknowledged(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    with patch("app.api.v1.imports._validate_account_import", return_value=BrokerType.IBKR):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/{account_id}/fresh-start",
            data={"acknowledged": "false"},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 400

async def test_fresh_start_account_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    account_id = uuid.uuid4()
    
    from app.core.exceptions import AccountNotFoundError
    
    with patch("app.api.v1.imports._validate_account_import", side_effect=AccountNotFoundError("Not found")):
        response = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/imports/{account_id}/fresh-start",
            data={"acknowledged": "true"},
            files={"file": ("test.xml", b"<xml></xml>", "text/xml")},
            headers=primary_user["headers"]
        )
        
    assert response.status_code == 404

async def test_validate_account_import_success(mock_session):
    from app.api.v1.imports import _validate_account_import
    from app.models.account import Account, AccountType
    from app.core.exceptions import ImportNotAllowedError, AccountNotFoundError
    from unittest.mock import MagicMock
    
    account_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    mock_account = Account(id=account_id, type=AccountType.IBKR)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_account
    mock_session.execute.return_value = mock_result
    
    broker = await _validate_account_import(account_id, portfolio_id, user_id, "xml", mock_session)
    assert broker == BrokerType.IBKR
    
    # Test not found
    mock_result.scalar_one_or_none.return_value = None
    with pytest.raises(AccountNotFoundError):
        await _validate_account_import(account_id, portfolio_id, user_id, "xml", mock_session)

    # Test manual
    mock_account.type = AccountType.MANUAL
    mock_result.scalar_one_or_none.return_value = mock_account
    with pytest.raises(ImportNotAllowedError):
        await _validate_account_import(account_id, portfolio_id, user_id, "xml", mock_session)

    # Test bad extension
    mock_account.type = AccountType.IBKR
    mock_session.scalar.return_value = mock_account
    with pytest.raises(ImportNotAllowedError):
        await _validate_account_import(account_id, portfolio_id, user_id, "csv", mock_session)

    # Test schwab csv exception message specifically handled in code
    mock_account.type = AccountType.SCHWAB
    mock_session.scalar.return_value = mock_account
    with pytest.raises(ImportNotAllowedError) as exc_info:
        await _validate_account_import(account_id, portfolio_id, user_id, "csv", mock_session)
    assert "Schwab accounts require JSON format" in str(exc_info.value)

