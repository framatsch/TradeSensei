"""Unit tests for analytics-related Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.analytics import DashboardFilterConfig


def test_dashboard_filter_config_rejects_inverted_date_range() -> None:
    """date_from later than date_to must fail validation."""
    with pytest.raises(ValidationError):
        DashboardFilterConfig(
            date_from="2026-02-01",
            date_to="2026-01-01",
        )


def test_dashboard_filter_config_requires_normalize_to_in_normalized_mode() -> None:
    """NORMALIZED mode requires a target currency."""
    with pytest.raises(ValidationError):
        DashboardFilterConfig(currency_mode="NORMALIZED")


def test_dashboard_filter_config_defaults_to_native_mode() -> None:
    """currency_mode defaults to NATIVE when omitted."""
    model = DashboardFilterConfig()
    assert model.currency_mode == "NATIVE"
