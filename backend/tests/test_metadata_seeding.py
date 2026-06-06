# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Integration tests for default metadata seed repositories."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation_definition import AnnotationDefinition
from app.models.taxonomy import Taxonomy
from app.models.user import User
from app.repositories.annotation_definition_repository import AnnotationDefinitionRepository
from app.repositories.taxonomy_repository import TaxonomyRepository


async def _create_user(db_session: AsyncSession, suffix: str) -> User:
    user = User(
        username=f"seed_user_{suffix}",
        email=f"seed_user_{suffix}@example.com",
        hashed_password="seed-hash",
        provider="local",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.integration
async def test_taxonomy_seed_defaults_insert_expected_13_rows(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, uuid.uuid4().hex[:8])
    repo = TaxonomyRepository(db_session)

    await repo.seed_defaults(user.id)

    result = await db_session.execute(select(Taxonomy).where(Taxonomy.user_id == user.id))
    rows = list(result.scalars().all())
    assert len(rows) == 13

    by_name = {row.name: row for row in rows}
    expected = {
        "Bullish": ("checkins", "#22c55e", "trending-up"),
        "Bearish": ("checkins", "#ef4444", "trending-down"),
        "Sideways": ("checkins", "#f59e0b", "minus"),
        "Volatile": ("checkins", "#a855f7", "activity"),
        "FOMO": ("trades", "#ec4899", "alert-circle"),
        "Discipline": ("trades", "#3b82f6", "shield"),
        "High Conviction": ("trades", "#facc15", "zap"),
        "Breakout": ("checkins,trades", "#10b981", "arrow-up-right"),
        "Mean Reversion": ("checkins,trades", "#6366f1", "repeat"),
        "Momentum": ("checkins,trades", "#f97316", "rocket"),
        "Trend Following": ("checkins,trades", "#06b6d4", "trending-up"),
        "Stop Loss": ("trades", "#ef4444", "octagon"),
        "Textbook Trade": ("trades", "#fbbf24", "award"),
    }
    assert set(by_name.keys()) == set(expected.keys())
    for name, (scope, color_hex, icon_identifier) in expected.items():
        row = by_name[name]
        assert row.scope == scope
        assert row.color_hex == color_hex
        assert row.icon_identifier == icon_identifier


@pytest.mark.integration
async def test_annotation_seed_defaults_insert_expected_5_rows(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, uuid.uuid4().hex[:8])
    repo = AnnotationDefinitionRepository(db_session)

    await repo.seed_defaults(user.id)

    result = await db_session.execute(
        select(AnnotationDefinition).where(AnnotationDefinition.user_id == user.id)
    )
    rows = list(result.scalars().all())
    assert len(rows) == 5

    by_name = {row.name: row for row in rows}
    expected = {
        "Mood Level": ("int", "checkins", {"min": 1, "max": 10}, "smile"),
        "Focus": ("int", "checkins", {"min": 1, "max": 10}, "target"),
        "Rule Followed": ("bool", "trades", {}, "check-square"),
        "Setup Quality": (
            "string_enum",
            "trades",
            {"options": ["A+", "B", "C"]},
            "award",
        ),
        "Market Regime": (
            "string_enum",
            "checkins",
            {"options": ["Bull", "Bear", "Chop", "Sideways"]},
            "trending-up",
        ),
    }
    assert set(by_name.keys()) == set(expected.keys())
    for name, (kind, scope, scale_labels, icon_identifier) in expected.items():
        row = by_name[name]
        assert row.type == kind
        assert row.scope == scope
        assert row.scale_labels == scale_labels
        assert row.icon_identifier == icon_identifier


@pytest.mark.integration
async def test_seed_defaults_is_idempotent_for_same_user(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, uuid.uuid4().hex[:8])
    taxonomy_repo = TaxonomyRepository(db_session)
    annotation_repo = AnnotationDefinitionRepository(db_session)

    await taxonomy_repo.seed_defaults(user.id)
    await taxonomy_repo.seed_defaults(user.id)
    await annotation_repo.seed_defaults(user.id)
    await annotation_repo.seed_defaults(user.id)

    taxonomy_rows = await db_session.execute(
        select(Taxonomy).where(Taxonomy.user_id == user.id)
    )
    annotation_rows = await db_session.execute(
        select(AnnotationDefinition).where(AnnotationDefinition.user_id == user.id)
    )
    assert len(list(taxonomy_rows.scalars().all())) == 13
    assert len(list(annotation_rows.scalars().all())) == 5


@pytest.mark.integration
async def test_registration_completes_even_when_seeding_fails(client: AsyncClient) -> None:
    """Registration must succeed even if metadata seeding raises an exception."""
    uid = uuid.uuid4().hex[:8]

    with patch(
        "app.repositories.taxonomy_repository.TaxonomyRepository.seed_defaults",
        new_callable=AsyncMock,
        side_effect=RuntimeError("simulated seeding failure"),
    ):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": f"seed_fail_{uid}",
                "email": f"seed_fail_{uid}@example.com",
                "password": "SeedFail@99",
            },
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["username"] == f"seed_fail_{uid}"
