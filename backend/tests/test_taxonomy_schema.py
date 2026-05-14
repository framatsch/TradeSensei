"""Unit tests for taxonomy schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.taxonomy import TaxonomyCreate, TaxonomyUpdate


@pytest.mark.unit
def test_hex_color_accepts_valid_format() -> None:
    payload = TaxonomyCreate(name="Setup", scope="trades", color_hex="#A3F4B1")
    assert payload.color_hex == "#A3F4B1"


@pytest.mark.unit
def test_hex_color_rejects_short_format() -> None:
    with pytest.raises(ValidationError):
        TaxonomyCreate(name="Setup", scope="trades", color_hex="#FFF")


@pytest.mark.unit
def test_hex_color_rejects_missing_hash() -> None:
    with pytest.raises(ValidationError):
        TaxonomyCreate(name="Setup", scope="trades", color_hex="A3F4B1")


@pytest.mark.unit
def test_taxonomy_update_hex_validator_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        TaxonomyUpdate(color_hex="#123")
