import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.execution import (
    LogicalExecutionCreate,
    LogicalExecutionRead,
    LogicalExecutionUpdate,
)
from app.schemas.trade import TradeRead
from app.services.execution import ExecutionService

router = APIRouter(tags=["Executions"])


@router.get(
    "/trades/{trade_id}/executions",
    response_model=list[LogicalExecutionRead],
    status_code=status.HTTP_200_OK,
)
async def list_trade_executions(
    trade_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LogicalExecutionRead]:
    """Retrieve all logical executions associated with a specific trade."""
    service = ExecutionService(session)
    executions = await service.list_for_trade(trade_id=trade_id, user_id=user.id)
    return [LogicalExecutionRead.model_validate(e) for e in executions]


@router.post(
    "/trades/{trade_id}/executions",
    response_model=LogicalExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_execution(
    trade_id: uuid.UUID,
    data: LogicalExecutionCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LogicalExecutionRead:
    """Create a manual execution and attach it to a specific trade.
    This triggers re-aggregation of the target trade.
    """
    service = ExecutionService(session)
    execution = await service.create_manual_execution(
        trade_id=trade_id, user_id=user.id, data=data
    )
    return LogicalExecutionRead.model_validate(execution)


@router.patch(
    "/executions/{execution_id}",
    response_model=LogicalExecutionRead,
    status_code=status.HTTP_200_OK,
)
async def update_execution(
    execution_id: uuid.UUID,
    data: LogicalExecutionUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LogicalExecutionRead:
    """Update a specific execution.
    If the execution belongs to a trade, the trade will be re-aggregated.
    """
    service = ExecutionService(session)
    execution = await service.update_execution(
        execution_id=execution_id, user_id=user.id, data=data
    )
    return LogicalExecutionRead.model_validate(execution)


@router.delete(
    "/executions/{execution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_execution(
    execution_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a specific execution.
    If it is the last execution in its trade, the trade will be deleted.
    Otherwise, the trade will be re-aggregated.
    """
    service = ExecutionService(session)
    await service.delete_execution(execution_id=execution_id, user_id=user.id)


class ReassignExecutionRequest(BaseModel):
    target_trade_id: uuid.UUID


@router.post(
    "/executions/{execution_id}/reassign",
    status_code=status.HTTP_200_OK,
)
async def reassign_execution(
    execution_id: uuid.UUID,
    data: ReassignExecutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Reassign an execution to another trade."""
    service = ExecutionService(session)
    # execution service returns execution, let's just return a dict
    execution = await service.reassign_execution(
        execution_id=execution_id, target_trade_id=data.target_trade_id, user_id=user.id
    )
    return {
        "execution": LogicalExecutionRead.model_validate(execution).model_dump(),
        "message": "Execution reassigned.",
    }


@router.post(
    "/executions/{execution_id}/detach",
    response_model=TradeRead,
    status_code=status.HTTP_200_OK,
)
async def detach_execution(
    execution_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TradeRead:
    """Detach an execution from its current trade into a new trade."""
    service = ExecutionService(session)
    trade = await service.detach_execution(execution_id=execution_id, user_id=user.id)
    return TradeRead.model_validate(trade)
