import re

with open('backend/app/api/v1/trades.py', 'r') as f:
    content = f.read()

endpoint = """
@router.patch("/{trade_id}/modelbook", response_model=ResponseEnvelope[TradeRead])
async def update_trade_modelbook(
    trade_id: uuid.UUID,
    payload: ModelBookPatchRequest,
    service: Annotated[TradeService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[TradeRead]:
    \"\"\"Star or unstar a trade for the Model Book.\"\"\"
    try:
        trade = await service.update_modelbook_flag(
            trade_id,
            payload.is_modelbook,
            current_user.id,
        )
        return ResponseEnvelope[TradeRead](data=trade)
    except TradeNotFoundError:
        _raise_not_found()
"""

if "update_trade_modelbook" not in content:
    # Need to add ModelBookPatchRequest to imports if not there
    if "ModelBookPatchRequest" not in content:
        content = content.replace("from app.schemas.trade import", "from app.schemas.model_book import ModelBookPatchRequest\nfrom app.schemas.trade import")
        
    content = content + "\n" + endpoint
    with open('backend/app/api/v1/trades.py', 'w') as f:
        f.write(content)
