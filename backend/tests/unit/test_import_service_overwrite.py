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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.import_service import ImportService
from app.utils.parsers.factory import BrokerType


@pytest.fixture
def import_service():
    session = AsyncMock()
    svc = ImportService(session=session)
    svc._account_repo = AsyncMock()
    svc._portfolio_repo = AsyncMock()
    svc._raw_repo = AsyncMock()
    svc._logical_svc = AsyncMock()
    svc._exec_repo = AsyncMock()
    svc._trade_repo = AsyncMock()
    svc._ca_repo = AsyncMock()
    
    # Defaults
    svc._account_repo.get_by_id.return_value = MagicMock(id=uuid.uuid4())
    svc._portfolio_repo.get_by_id.return_value = MagicMock(base_currency="USD")
    svc._exec_repo.delete_split_children_for_account.return_value = 1
    svc._exec_repo.restore_split_parents_for_account.return_value = 1
    svc._raw_repo.bulk_upsert.return_value = []
    svc._logical_svc.bulk_create_from_raw.return_value = ([], 0)
    svc._trade_repo.list_open_combo_positions_by_user.return_value = []
    svc._ca_repo.list_by_user.return_value = []
    
    return svc

@pytest.mark.asyncio
async def test_import_file_with_overwrite_manually_edited(import_service):
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    
    mock_parser = MagicMock()
    mock_parser.parse_raw.return_value = ([], [])
    mock_parser.enrich_pnl_eur = AsyncMock()
    mock_parser.warnings = []

    with patch("app.services.import_service.get_parser", return_value=mock_parser):
        await import_service.import_file(
            content=b"<dummy />",
            filename="dummy.xml",
            broker=BrokerType.IBKR,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=user_id,
            overwrite_manually_edited=True,
        )

    import_service._exec_repo.delete_split_children_for_account.assert_called_once_with(
        user_id=user_id,
        account_id=account_id,
        override=True
    )
    import_service._exec_repo.restore_split_parents_for_account.assert_called_once_with(
        user_id=user_id,
        account_id=account_id,
        override=True
    )
    import_service._trade_repo.delete_by_user_account.assert_called_once_with(
        user_id=user_id,
        account_id=account_id,
        include_manually_edited=True,
        exclude_trade_ids=[]
    )

@pytest.mark.asyncio
async def test_import_file_without_overwrite_manually_edited(import_service):
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    
    mock_parser = MagicMock()
    mock_parser.parse_raw.return_value = ([], [])
    mock_parser.enrich_pnl_eur = AsyncMock()
    mock_parser.warnings = []

    with patch("app.services.import_service.get_parser", return_value=mock_parser):
        await import_service.import_file(
            content=b"<dummy />",
            filename="dummy.xml",
            broker=BrokerType.IBKR,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=user_id,
            overwrite_manually_edited=False,
        )

    import_service._exec_repo.delete_split_children_for_account.assert_called_once_with(
        user_id=user_id,
        account_id=account_id,
        override=False
    )
    import_service._exec_repo.restore_split_parents_for_account.assert_called_once_with(
        user_id=user_id,
        account_id=account_id,
        override=False
    )
    import_service._trade_repo.delete_by_user_account.assert_called_once_with(
        user_id=user_id,
        account_id=account_id,
        include_manually_edited=False,
        exclude_trade_ids=[]
    )
