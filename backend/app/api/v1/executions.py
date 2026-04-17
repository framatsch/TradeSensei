"""Route handlers for logical execution operations."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_session_with_rls
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
    MergeExecutionsRequest,
    MergeExecutionsResponse,
    ReassignExecutionRequest,
    ReassignExecutionResponse,
    SplitExecutionRequest,
    SplitExecutionResponse,
)
from app.schemas.trade import TradeRead
from app.services.execution import ExecutionService

router = APIRouter(tags=["Executions"])


def _get_service(
    session: Annotated[AsyncSession, Depends(get_session_with_rls)],
) -> ExecutionService:
    """Build an execution service bound to the current request session."""
    return ExecutionService(session)


@router.get(
    "/trades/{trade_id}/executions",
    response_model=ResponseEnvelope[list[LogicalExecutionRead]],
    status_code=status.HTTP_200_OK,
    summary="List executions for a trade",
    description=(
        "Retrieve all logical execution legs for a specific trade. "
        "By default, soft-deleted executions are excluded. "
        "Pass ``include_deleted=true`` to include them "
        "(they will show ``deleted=true``)."
    ),
)
async def list_trade_executions(
    trade_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
    include_deleted: Annotated[
        bool,
        Query(
            description=(
                "When true, include soft-deleted executions in the response. "
                "Defaults to false."
            )
        ),
    ] = False,
) -> ResponseEnvelope[list[LogicalExecutionRead]]:
    """Retrieve all logical executions associated with a specific trade."""
    try:
        executions = await service.list_for_trade(
            trade_id=trade_id,
            user_id=user.id,
            include_deleted=include_deleted,
        )
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
    summary="Create a manual execution",
    description=(
        "Create a manual execution leg and attach it to a specific trade. "
        "The execution will have ``origin='manual'``. "
        "This triggers re-aggregation of the target trade."
    ),
)
async def create_manual_execution(
    trade_id: uuid.UUID,
    data: LogicalExecutionCreate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[LogicalExecutionRead]:
    """Create a manual execution and attach it to a specific trade."""
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
    summary="Update an execution",
    description=(
        "Update price, quantity, commission, or timestamp of an execution. "
        "When patching an execution with ``origin='imported'``, the service "
        "automatically sets ``user_modified=true``. "
        "If the execution belongs to a trade, the trade is re-aggregated."
    ),
)
async def update_execution(
    execution_id: uuid.UUID,
    data: LogicalExecutionUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[LogicalExecutionRead]:
    """Update a specific execution."""
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
    response_model=ResponseEnvelope[LogicalExecutionRead],
    status_code=status.HTTP_200_OK,
    summary="Delete an execution",
    description=(
        "Delete an execution. Behaviour depends on ``origin``:\n\n"
        "- ``imported|merged|split``: soft-delete (``deleted=true``), returns 200 "
        "with execution body. BRT link is preserved so re-import cannot "
        "resurrect it.\n"
        "- ``manual``: hard-delete (row removed), returns 204 No Content.\n"
        "- Already deleted: returns 409 Conflict.\n\n"
        "The parent trade is re-aggregated after every delete."
    ),
    responses={
        200: {"description": "Soft-deleted (imported/merged/split execution)"},
        204: {"description": "Hard-deleted (manual execution)"},
        404: {"description": "Execution not found"},
        409: {"description": "Execution is already soft-deleted"},
    },
)
async def delete_execution(
    execution_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[LogicalExecutionRead]:
    """Delete an execution — soft or hard depending on origin.

    Returns 200 with body for soft-delete, 204 No Content for hard-delete.
    """
    try:
        result = await service.delete_execution(
            execution_id=execution_id, user_id=user.id
        )
    except ExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found.",
        ) from exc
    except ExecutionValidationError as exc:
        # Already deleted → 409 Conflict
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if result is None:
        # Hard-delete of manual execution → 204 No Content
        from fastapi import Response

        return Response(status_code=status.HTTP_204_NO_CONTENT)  # type: ignore[return-value]

    return ResponseEnvelope(data=LogicalExecutionRead.model_validate(result))


@router.post(
    "/executions/{execution_id}/restore",
    response_model=ResponseEnvelope[LogicalExecutionRead],
    status_code=status.HTTP_200_OK,
    summary="Restore a soft-deleted execution",
    description=(
        "Restore a soft-deleted execution by setting ``deleted=false``. "
        "Triggers re-aggregation of the parent trade. "
        "Returns 400 Bad Request if the execution is not soft-deleted."
    ),
    responses={
        200: {"description": "Execution restored successfully"},
        400: {"description": "Execution is not deleted"},
        404: {"description": "Execution not found"},
    },
)
async def restore_execution(
    execution_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[LogicalExecutionRead]:
    """Restore a previously soft-deleted execution."""
    try:
        execution = await service.restore_execution(
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
    return ResponseEnvelope(data=LogicalExecutionRead.model_validate(execution))


@router.post(
    "/executions/{execution_id}/split",
    response_model=ResponseEnvelope[SplitExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="Split an execution into two",
    description=(
        "Split one execution into two child executions. The original execution is "
        "soft-deleted (``deleted=true``) and two new executions with "
        "``origin='split'`` and ``parent_id=original.id`` are created. "
        "The quantities must sum to the original execution's quantity."
    ),
    responses={
        200: {"description": "Split completed successfully"},
        400: {"description": "Invalid split parameters or execution cannot be split"},
        404: {"description": "Execution not found"},
    },
)
async def split_execution(
    execution_id: uuid.UUID,
    data: SplitExecutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[SplitExecutionResponse]:
    """Split an execution into two child executions."""
    try:
        result = await service.split_execution(
            execution_id=execution_id, user_id=user.id, data=data
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
    return ResponseEnvelope(data=result)


@router.post(
    "/executions/merge",
    response_model=ResponseEnvelope[MergeExecutionsResponse],
    status_code=status.HTTP_200_OK,
    summary="Merge two or more executions into one",
    description=(
        "Merge two or more executions into a single execution. "
        "All source executions are soft-deleted (``deleted=true``). "
        "A new execution is created with ``origin='merged'`` and "
        "``parent_id=primary.id``. "
        "All sources must belong to the same trade, share the same symbol "
        "and direction, and must not already be deleted."
    ),
    responses={
        200: {"description": "Merge completed successfully"},
        400: {"description": "Invalid merge parameters or executions cannot be merged"},
        404: {"description": "One or more executions not found"},
    },
)
async def merge_executions(
    data: MergeExecutionsRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ExecutionService, Depends(_get_service)],
) -> ResponseEnvelope[MergeExecutionsResponse]:
    """Merge two or more executions into one merged execution."""
    try:
        result = await service.merge_executions(user_id=user.id, data=data)
    except ExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ExecutionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ResponseEnvelope(data=result)


@router.post(
    "/executions/{execution_id}/reassign",
    response_model=ResponseEnvelope[ReassignExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="Reassign an execution to another trade",
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
    summary="Detach an execution into a new trade",
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
