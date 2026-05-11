"""Unit tests for daily check-in schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.daily_checkin import DailyCheckinCreate


def test_daily_checkin_news_links_rejects_invalid_url() -> None:
    """news_links must contain valid http(s) URLs."""
    with pytest.raises(ValidationError):
        DailyCheckinCreate(
            date="2026-01-05",
            news_links=["not a url"],
        )


def test_daily_checkin_news_links_max_10() -> None:
    """news_links accepts at most 10 entries."""
    with pytest.raises(ValidationError):
        DailyCheckinCreate(
            date="2026-01-05",
            news_links=[f"https://example.com/{idx}" for idx in range(11)],
        )
