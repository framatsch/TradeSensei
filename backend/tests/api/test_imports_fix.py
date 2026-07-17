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

import pytest
from app.api.v1.imports import _validate_account_import
from app.models.account import Account, AccountType
from app.core.exceptions import ImportNotAllowedError, AccountNotFoundError
from app.utils.parsers.factory import BrokerType
import uuid
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_validate_account_import_success(mock_session):
    account_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    mock_account = Account(id=account_id, type=AccountType.IBKR)
    
    with patch("app.api.v1.imports.AccountRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.get_by_id = AsyncMock(return_value=mock_account)
        
        broker = await _validate_account_import(account_id, portfolio_id, user_id, "xml", mock_session)
        assert broker == BrokerType.IBKR
        
        # Test not found
        mock_repo_instance.get_by_id.return_value = None
        with pytest.raises(AccountNotFoundError):
            await _validate_account_import(account_id, portfolio_id, user_id, "xml", mock_session)

        # Test manual
        mock_account.type = AccountType.MANUAL
        mock_repo_instance.get_by_id.return_value = mock_account
        with pytest.raises(ImportNotAllowedError):
            await _validate_account_import(account_id, portfolio_id, user_id, "xml", mock_session)

        # Test bad extension
        mock_account.type = AccountType.IBKR
        mock_repo_instance.get_by_id.return_value = mock_account
        with pytest.raises(ImportNotAllowedError):
            await _validate_account_import(account_id, portfolio_id, user_id, "csv", mock_session)

        # Test schwab csv exception
        mock_account.type = AccountType.SCHWAB
        mock_repo_instance.get_by_id.return_value = mock_account
        with pytest.raises(ImportNotAllowedError) as exc_info:
            await _validate_account_import(account_id, portfolio_id, user_id, "csv", mock_session)
        assert "Schwab accounts require JSON format" in str(exc_info.value)
