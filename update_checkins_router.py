import re

with open('backend/app/api/v1/checkins.py', 'r') as f:
    content = f.read()

endpoint = """
@router.patch("/{checkin_date}/modelbook", response_model=ResponseEnvelope[DailyCheckinResponse])
async def update_checkin_modelbook(
    checkin_date: dt.date,
    payload: ModelBookPatchRequest,
    service: Annotated[DailyCheckinService, Depends(_get_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResponseEnvelope[DailyCheckinResponse]:
    \"\"\"Star or unstar a daily check-in for the Model Book.\"\"\"
    try:
        checkin = await service.update_modelbook_flag(
            current_user.id,
            checkin_date,
            payload.is_modelbook,
        )
        return ResponseEnvelope[DailyCheckinResponse](data=checkin)
    except DailyCheckinNotFoundError:
        _raise_not_found()
"""

if "update_checkin_modelbook" not in content:
    if "ModelBookPatchRequest" not in content:
        content = content.replace("from app.schemas.daily_checkin import", "from app.schemas.model_book import ModelBookPatchRequest\nfrom app.schemas.daily_checkin import")
        
    content = content + "\n" + endpoint
    with open('backend/app/api/v1/checkins.py', 'w') as f:
        f.write(content)
