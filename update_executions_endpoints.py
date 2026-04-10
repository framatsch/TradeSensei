import re

with open("backend/app/api/v1/executions.py", "r") as f:
    content = f.read()

new_endpoints = """
from pydantic import BaseModel
from app.schemas.trade import TradeRead

class ReassignExecutionRequest(BaseModel):
    target_trade_id: uuid.UUID

@router.post(
    "/executions/{execution_id}/reassign",
    response_model=LogicalExecutionRead,
    status_code=status.HTTP_200_OK,
)
async def reassign_execution(
    execution_id: uuid.UUID,
    data: ReassignExecutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LogicalExecutionRead:
    \"\"\"Reassign an execution to another trade.\"\"\"
    service = ExecutionService(session)
    execution = await service.reassign_execution(
        execution_id=execution_id, target_trade_id=data.target_trade_id, user_id=user.id
    )
    return LogicalExecutionRead.model_validate(execution)

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
    \"\"\"Detach an execution from its current trade into a new trade.\"\"\"
    service = ExecutionService(session)
    trade = await service.detach_execution(execution_id=execution_id, user_id=user.id)
    return TradeRead.model_validate(trade)
"""

content += "\n" + new_endpoints

with open("backend/app/api/v1/executions.py", "w") as f:
    f.write(content)
