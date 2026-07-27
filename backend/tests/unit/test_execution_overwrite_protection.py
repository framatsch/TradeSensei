import pytest
from uuid import uuid4
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.execution import ExecutionService
from app.models.logical_execution import LogicalExecution, EXECUTION_ORIGIN_IMPORTED, EXECUTION_ORIGIN_SPLIT, EXECUTION_ORIGIN_MERGED, EXECUTION_ORIGIN_MANUAL
from app.schemas.execution import LogicalExecutionUpdate, LinkBrokerTransactionRequest
from app.models.broker_raw_transaction import BrokerRawTransaction

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
    service.brt_repo = mock_brt_repo
    service.audit_service = mock_audit_service
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


