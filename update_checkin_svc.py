import re
with open('backend/app/services/daily_checkin_service.py', 'r') as f:
    content = f.read()

method = """
    async def update_modelbook_flag(
        self, user_id: uuid.UUID, checkin_date: date, is_modelbook: bool
    ) -> DailyCheckinResponse:
        checkin = await self.repo.update_modelbook_flag(user_id, checkin_date, is_modelbook)
        if not checkin:
            raise CheckinNotFoundError()
        return DailyCheckinResponse.model_validate(checkin)
"""

if "update_modelbook_flag" not in content:
    content += method
    with open('backend/app/services/daily_checkin_service.py', 'w') as f:
        f.write(content)
