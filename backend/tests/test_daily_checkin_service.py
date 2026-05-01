"""Unit tests for daily check-in service validation logic."""

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.daily_checkin import FieldTypeEnum
from app.services.daily_checkin_service import DailyCheckinService


class _Phase:
    def __init__(self, name: str) -> None:
        self.name = name


class _Field:
    def __init__(self, field_name: str, field_type: FieldTypeEnum) -> None:
        self.field_name = field_name
        self.field_type = field_type


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_market_phase_accepts_null(mock_session: object) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    await service._validate_market_phase(uuid.uuid4(), None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_market_phase_rejects_unknown(mock_session: object) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._phase_repo.list_by_user = AsyncMock(return_value=[_Phase("bullish")])  # type: ignore[attr-defined]

    with pytest.raises(HTTPException) as exc:
        await service._validate_market_phase(uuid.uuid4(), "bearish")
    assert exc.value.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_market_phase_rejects_inactive(mock_session: object) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._phase_repo.list_by_user = AsyncMock(return_value=[])  # type: ignore[attr-defined]

    with pytest.raises(HTTPException) as exc:
        await service._validate_market_phase(uuid.uuid4(), "bullish")
    assert exc.value.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_market_phase_accepts_active(mock_session: object) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._phase_repo.list_by_user = AsyncMock(return_value=[_Phase("bullish")])  # type: ignore[attr-defined]

    await service._validate_market_phase(uuid.uuid4(), "bullish")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_custom_metrics_type_and_unknown_errors(
    mock_session: object,
) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._field_repo.list_by_user = AsyncMock(  # type: ignore[attr-defined]
        return_value=[
            _Field("mood-level", FieldTypeEnum.INTEGER),
            _Field("rule-followed", FieldTypeEnum.BOOLEAN),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service._validate_custom_metrics(
            uuid.uuid4(),
            {"unknown": 1, "rule-followed": 1},
        )
    assert exc.value.status_code == 422
    details = exc.value.detail
    assert isinstance(details, list)
    assert any("unknown" in message for message in details)
    assert any("expected boolean" in message for message in details)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_custom_metrics_accepts_valid_values(
    mock_session: object,
) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._field_repo.list_by_user = AsyncMock(  # type: ignore[attr-defined]
        return_value=[
            _Field("mood-level", FieldTypeEnum.INTEGER),
            _Field("rule-followed", FieldTypeEnum.BOOLEAN),
        ]
    )

    await service._validate_custom_metrics(
        uuid.uuid4(),
        {"mood-level": 7, "rule-followed": True},
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_custom_metrics_rejects_inactive_field(
    mock_session: object,
) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._field_repo.list_by_user = AsyncMock(  # type: ignore[attr-defined]
        return_value=[_Field("mood-level", FieldTypeEnum.INTEGER)]
    )

    with pytest.raises(HTTPException) as exc:
        await service._validate_custom_metrics(
            uuid.uuid4(),
            {"focus": 8},
        )
    assert exc.value.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_custom_metrics_accepts_empty_payload(
    mock_session: object,
) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._field_repo.list_by_user = AsyncMock(return_value=[])  # type: ignore[attr-defined]

    await service._validate_custom_metrics(uuid.uuid4(), {})


@pytest.mark.unit
def test_validate_screenshot_urls_without_storage_rejects_nonempty(
    mock_session: object,
) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]

    from app.core.config import settings

    original = settings.storage_public_url
    settings.storage_public_url = None
    try:
        with pytest.raises(HTTPException) as exc:
            service._validate_screenshot_urls(["https://x/y.png"])
        assert exc.value.status_code == 422
    finally:
        settings.storage_public_url = original


@pytest.mark.unit
def test_validate_screenshot_urls_with_storage_prefix(mock_session: object) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]

    from app.core.config import settings

    original = settings.storage_public_url
    settings.storage_public_url = "https://storage.example.com"
    try:
        service._validate_screenshot_urls(
            ["https://storage.example.com/path/image.png"]
        )
        with pytest.raises(HTTPException):
            service._validate_screenshot_urls(["https://evil.example.com/image.png"])
    finally:
        settings.storage_public_url = original


@pytest.mark.unit
def test_validate_screenshot_urls_without_storage_accepts_empty_list(
    mock_session: object,
) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]

    from app.core.config import settings

    original = settings.storage_public_url
    settings.storage_public_url = None
    try:
        service._validate_screenshot_urls([])
    finally:
        settings.storage_public_url = original


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_checkins_returns_cursor_envelope(mock_session: object) -> None:
    service = DailyCheckinService(mock_session)  # type: ignore[arg-type]
    service._repo.list_by_user = AsyncMock(return_value=([], None, 0))  # type: ignore[attr-defined]

    response = await service.list_checkins(
        user_id=uuid.uuid4(),
        from_date=date(2026, 1, 1),
    )
    assert response.total == 0
    assert response.items == []
    assert response.next_cursor is None
