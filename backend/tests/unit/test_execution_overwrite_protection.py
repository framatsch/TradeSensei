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
from uuid import uuid4
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.execution import ExecutionService
from app.models.logical_execution import LogicalExecution, EXECUTION_ORIGIN_IMPORTED, EXECUTION_ORIGIN_SPLIT, EXECUTION_ORIGIN_MERGED, EXECUTION_ORIGIN_MANUAL
from app.schemas.execution import LogicalExecutionUpdate

@pytest.fixture
def mock_execution_repo():
    return AsyncMock()

@pytest.fixture
def mock_trade_repo():
    return AsyncMock()

@pytest.fixture
def mock_brt_repo():
    return AsyncMock()

@pytest.fixture
def mock_audit_service():
    return AsyncMock()

@pytest.fixture
def execution_service(mock_session, mock_execution_repo, mock_trade_repo, mock_brt_repo, mock_audit_service):
    service = ExecutionService(mock_session)
    service.execution_repo = mock_execution_repo
    service.trade_repo = mock_trade_repo
    service.raw_transaction_repo = mock_brt_repo
    service._audit = mock_audit_service
    service._re_aggregate_trade = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_update_execution_marks_all_editable_origins(execution_service, mock_execution_repo):
    user_id = uuid4()
    for origin in [EXECUTION_ORIGIN_IMPORTED, EXECUTION_ORIGIN_SPLIT, EXECUTION_ORIGIN_MERGED]:
        execution_id = uuid4()
        execution = LogicalExecution(id=execution_id, user_id=user_id, origin=origin, user_modified=False)
        mock_execution_repo.get_by_id.return_value = execution
        mock_execution_repo.update.return_value = execution
        
        await execution_service.update_execution(
            execution_id=execution_id,
            user_id=user_id,
            data=LogicalExecutionUpdate(price=Decimal("10.0"))
        )
        
        mock_execution_repo.update.assert_called_with(execution, price=Decimal("10.0"), user_modified=True)

    execution_id = uuid4()
    execution = LogicalExecution(id=execution_id, user_id=user_id, origin=EXECUTION_ORIGIN_MANUAL, user_modified=False)
    mock_execution_repo.get_by_id.return_value = execution
    mock_execution_repo.update.return_value = execution
    
    await execution_service.update_execution(
        execution_id=execution_id,
        user_id=user_id,
        data=LogicalExecutionUpdate(price=Decimal("10.0"))
    )
    
    mock_execution_repo.update.assert_called_with(execution, price=Decimal("10.0"))
