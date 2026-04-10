import re

with open("backend/app/api/v1/executions.py", "r") as f:
    content = f.read()

# Replace the response_model=LogicalExecutionRead to response_model=dict
new_func = """
@router.post(
    "/{execution_id}/reassign",
    status_code=status.HTTP_200_OK,
)
async def reassign_execution(
    execution_id: uuid.UUID,
    data: ReassignExecutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    \"\"\"Reassign an execution to another trade.\"\"\"
    service = ExecutionService(session)
    # execution service returns execution, let's just return a dict
    execution = await service.reassign_execution(
        execution_id=execution_id, target_trade_id=data.target_trade_id, user_id=user.id
    )
    return {"execution": LogicalExecutionRead.model_validate(execution).model_dump(), "message": "Execution reassigned."}
"""

content = re.sub(r'@router\.post\(\n    "/executions/\{execution_id\}/reassign",\n    response_model=LogicalExecutionRead,\n.*?return LogicalExecutionRead\.model_validate\(execution\)', new_func.strip(), content, flags=re.DOTALL)

with open("backend/app/api/v1/executions.py", "w") as f:
    f.write(content)
