"""Route handlers for logical execution operations."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import (
    ExecutionNotFoundError,
    ExecutionValidationError,
    TradeNotFoundError,
)
from app.models.user import User
from app.schemas.common import ResponseEnvelope
from app.schemas.execution import (
    LogicalExecutionCreate,
    LogicalExecutionRead,
    LogicalExecutionUpdate,
    ReassignExecutionRequest,
    ReassignExecutionResponse,
)
from app.schemas.trade import TradeRead
from app.services.execution import ExecutionService

router = APIRouter(tags=["Executions"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExecutionService:
    """Build an execution service bound to the current request session."""
    return ExecutionService(session)


@router.get(
    "/trades/{trade_id}/executions",
    response_model=ResponseEnvelope[list[LogicalExecutionRead]],
    status_code=status.HTTP_200_OK,
)
async def list_trade_executions(
    trade_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[list[LogicalExecutionRead]]:
    """Retrieve all logical executions associated with a specific trade."""
    try:
        executions = await service.list_for_trade(trade_id=trade_id, user_id=user.id)
    except TradeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found.",
        ) from exc
    return ResponseEnvelope(
        data=[LogicalExecutionRead.model_validate(e) for e in executions]
    )


@router.post(
    "/trades/{trade_id}/executions",
    response_model=ResponseEnvelope[LogicalExecutionRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_execution(
    trade_id: uuid.UUID,
    data: LogicalExecutionCreate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[LogicalExecutionRead]:
    """Create a manual execution and attach it to a specific trade.
    This triggers re-aggregation of the target trade.
    """
    try:
        execution = await service.create_manual_execution(
            trade_id=trade_id, user_id=user.id, data=data
        )
    except TradeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found.",
        ) from exc
    return ResponseEnvelope(data=LogicalExecutionRead.model_validate(execution))


@router.patch(
    "/executions/{execution_id}",
    response_model=ResponseEnvelope[LogicalExecutionRead],
    status_code=status.HTTP_200_OK,
)
async def update_execution(
    execution_id: uuid.UUID,
    data: LogicalExecutionUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[LogicalExecutionRead]:
    """Update a specific execution.
    If the execution belongs to a trade, the trade will be re-aggregated.
    """
    try:
        execution = await service.update_execution(
            execution_id=execution_id, user_id=user.id, data=data
        )
    except ExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found.",
        ) from exc
    return ResponseEnvelope(data=LogicalExecutionRead.model_validate(execution))


@router.delete(
    "/executions/{execution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_execution(
    execution_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> None:
    """Delete a specific execution.
    If it is the last execution in its trade, the trade will be deleted.
    Otherwise, the trade will be re-aggregated.
    """
    try:
        await service.delete_execution(execution_id=execution_id, user_id=user.id)
    except ExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found.",
        ) from exc


@router.post(
    "/executions/{execution_id}/reassign",
    response_model=ResponseEnvelope[ReassignExecutionResponse],
    status_code=status.HTTP_200_OK,
)
async def reassign_execution(
    execution_id: uuid.UUID,
    data: ReassignExecutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[ReassignExecutionResponse]:
    """Reassign an execution to another trade."""
    try:
        execution = await service.reassign_execution(
            execution_id=execution_id,
            target_trade_id=data.target_trade_id,
            user_id=user.id,
        )
    except ExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found.",
        ) from exc
    except TradeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target trade not found.",
        ) from exc
    except ExecutionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(
        data=ReassignExecutionResponse(
            execution=LogicalExecutionRead.model_validate(execution),
            message="Execution reassigned.",
        )
    )


@router.post(
    "/executions/{execution_id}/detach",
    response_model=ResponseEnvelope[TradeRead],
    status_code=status.HTTP_200_OK,
)
async def detach_execution(
    execution_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[TradeRead]:
    """Detach an execution from its current trade into a new trade."""
    try:
        trade = await service.detach_execution(
            execution_id=execution_id, user_id=user.id
        )
    except ExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found.",
        ) from exc
    except ExecutionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(data=TradeRead.model_validate(trade))
