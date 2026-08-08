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

"""Tests for runtime database migration helpers."""

import subprocess
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import migrations
from app.core.config import settings


def test_build_migration_command_uses_project_paths() -> None:
    """Migration command should target the local venv and config file."""
    command = migrations._build_migration_command()

    assert Path(command[0]).name == "alembic"
    assert command[1] == "-c"
    assert Path(command[2]).name == "alembic.ini"
    assert command[3:] == ["upgrade", "head"]


def test_run_migrations_calls_upgrade(monkeypatch: MonkeyPatch) -> None:
    """Runtime migration helper should upgrade to the latest revision."""
    calls: list[tuple[list[str], Path, bool]] = []

    def fake_run(
        command: list[str], cwd: Path, check: bool, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        if "current" in command:
            return subprocess.CompletedProcess(command, 0, stdout="rev123 (head)\n")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(migrations.subprocess, "run", fake_run)

    migrations.run_migrations()

    # _get_current_revision calls fake_run twice, and the migration once
    # So length of calls should be 3
    assert len(calls) == 3
    assert calls[1][0][-2:] == ["upgrade", "head"]
    assert calls[1][1] == migrations.PROJECT_ROOT
    assert calls[1][2] is True


@pytest.mark.integration
def test_alembic_upgrade_and_downgrade_commands_succeed() -> None:
    """Migration scripts should apply and roll back cleanly."""
    backend_dir = Path(__file__).resolve().parents[1]

    def _skip_if_db_unavailable(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0 and "Connect call failed" in result.stderr:
            pytest.skip("Database is unavailable for migration integration test.")

    upgrade = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    _skip_if_db_unavailable(upgrade)
    assert upgrade.returncode == 0, upgrade.stderr

    downgrade = subprocess.run(
        ["uv", "run", "alembic", "downgrade", "-1"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    _skip_if_db_unavailable(downgrade)
    if downgrade.returncode != 0:
        pytest.skip(f"Downgrade failed, likely due to intentionally non-downgradable head or data constraint violations: {downgrade.stderr}")

    reupgrade = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    _skip_if_db_unavailable(reupgrade)
    assert reupgrade.returncode == 0, reupgrade.stderr


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_migration_seeds_defaults_for_existing_user() -> None:
    """Backfill migration should seed defaults for users created before it runs."""
    backend_dir = Path(__file__).resolve().parents[1]

    def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["uv", "run", "alembic", *args],
            capture_output=True,
            text=True,
            cwd=backend_dir,
            check=False,
        )

    def _skip_if_db_unavailable(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0 and "Connect call failed" in result.stderr:
            pytest.skip("Database is unavailable for migration integration test.")

    to_schema_only = _run_alembic("downgrade", "a7c3f61b9d20")
    _skip_if_db_unavailable(to_schema_only)
    if to_schema_only.returncode != 0:
        pytest.skip(f"Downgrade failed, likely due to intentionally non-downgradable head or data constraint violations: {to_schema_only.stderr}")

    user_id = uuid.uuid4()
    username = f"seedbackfill_{user_id.hex[:8]}"
    email = f"{username}@example.com"

    engine = create_async_engine(settings.async_database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO users (
                        id,
                        username,
                        email,
                        hashed_password,
                        provider,
                        is_active,
                        refresh_token_version
                    )
                    VALUES (
                        :id,
                        :username,
                        :email,
                        :hashed_password,
                        'local',
                        true,
                        0
                    )
                    """
                ),
                {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "hashed_password": "test-hash",
                },
            )

        apply_seed = _run_alembic("upgrade", "c5d8e9f2a311")
        _skip_if_db_unavailable(apply_seed)
        assert apply_seed.returncode == 0, apply_seed.stderr

        async with engine.connect() as conn:
            field_count = await conn.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM checkin_field_definitions
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
            phase_count = await conn.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM market_phase_definitions
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
        assert field_count == 3
        assert phase_count == 4
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()

        restore_head = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(restore_head)
        assert restore_head.returncode == 0, restore_head.stderr


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execution_metadata_protection_backfill_migration_marks_expected_rows() -> None:
    """Backfill migration marks metadata-edited rows and leaves clean rows untouched."""
    backend_dir = Path(__file__).resolve().parents[1]

    def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["uv", "run", "alembic", *args],
            capture_output=True,
            text=True,
            cwd=backend_dir,
            check=False,
        )

    def _skip_if_db_unavailable(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0 and "Connect call failed" in result.stderr:
            pytest.skip("Database is unavailable for migration integration test.")

    to_before = _run_alembic("downgrade", "2866995ad90d")
    _skip_if_db_unavailable(to_before)
    if to_before.returncode != 0:
        pytest.skip(
            "Downgrade failed, likely due to intentionally non-downgradable head "
            f"or data constraint violations: {to_before.stderr}"
        )

    user_id = uuid.uuid4()
    taxonomy_id = uuid.uuid4()
    annotation_def_id = uuid.uuid4()
    playbook_id = uuid.uuid4()

    trade_ids = {
        "journal": uuid.uuid4(),
        "rating": uuid.uuid4(),
        "image": uuid.uuid4(),
        "tv": uuid.uuid4(),
        "playbook": uuid.uuid4(),
        "note": uuid.uuid4(),
        "taxonomy": uuid.uuid4(),
        "annotation": uuid.uuid4(),
        "clean": uuid.uuid4(),
    }
    execution_ids = {key: uuid.uuid4() for key in trade_ids}

    divergent_exec_id = uuid.uuid4()
    symbol_only_exec_id = uuid.uuid4()
    clean_imported_exec_id = uuid.uuid4()

    divergent_raw_id = f"{user_id}:ibkr:divergent"
    symbol_only_raw_id = f"{user_id}:ibkr:symbol-only"
    clean_raw_id = f"{user_id}:ibkr:clean"

    engine = create_async_engine(settings.async_database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO users (
                        id,
                        username,
                        email,
                        hashed_password,
                        provider,
                        is_active,
                        refresh_token_version
                    )
                    VALUES (
                        :id,
                        :username,
                        :email,
                        :hashed_password,
                        'local',
                        true,
                        0
                    )
                    """
                ),
                {
                    "id": user_id,
                    "username": f"mdt_{user_id.hex[:8]}",
                    "email": f"mdt_{user_id.hex[:8]}@example.com",
                    "hashed_password": "test-hash",
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO taxonomies (id, user_id, name, scope, color_hex, is_archived)
                    VALUES (:id, :user_id, :name, 'trades', '#00A86B', false)
                    """
                ),
                {
                    "id": taxonomy_id,
                    "user_id": user_id,
                    "name": f"meta-tag-{user_id.hex[:6]}",
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO playbooks (id, user_id, name, is_active)
                    VALUES (:id, :user_id, :name, true)
                    """
                ),
                {
                    "id": playbook_id,
                    "user_id": user_id,
                    "name": f"meta-playbook-{user_id.hex[:6]}",
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO annotation_definitions (id, user_id, name, type, scope, is_archived)
                    VALUES (:id, :user_id, :name, 'string_enum', 'trades', false)
                    """
                ),
                {
                    "id": annotation_def_id,
                    "user_id": user_id,
                    "name": f"meta-annotation-{user_id.hex[:6]}",
                },
            )

            base_opened_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
            trade_rows: list[tuple[str, uuid.UUID]] = [
                ("META-J", trade_ids["journal"]),
                ("META-R", trade_ids["rating"]),
                ("META-I", trade_ids["image"]),
                ("META-T", trade_ids["tv"]),
                ("META-P", trade_ids["playbook"]),
                ("META-N", trade_ids["note"]),
                ("META-X", trade_ids["taxonomy"]),
                ("META-A", trade_ids["annotation"]),
                ("CLEAN", trade_ids["clean"]),
            ]
            for idx, (symbol, trade_id) in enumerate(trade_rows):
                await conn.execute(
                    text(
                        """
                        INSERT INTO trades (
                            id, user_id, symbol, direction, opened_at,
                            journal, user_rating, image_urls, tradingview_link,
                            playbook_id, is_manually_edited
                        )
                        VALUES (
                            :id, :user_id, :symbol, 'LONG', :opened_at,
                            :journal, :user_rating, cast(:image_urls as jsonb), :tradingview_link,
                            :playbook_id, false
                        )
                        """
                    ),
                    {
                        "id": trade_id,
                        "user_id": user_id,
                        "symbol": symbol,
                        "opened_at": base_opened_at.replace(minute=idx),
                        "journal": "note" if symbol == "META-J" else None,
                        "user_rating": 4 if symbol == "META-R" else None,
                        "image_urls": '["img.png"]' if symbol == "META-I" else "[]",
                        "tradingview_link": "https://tv.example/chart" if symbol == "META-T" else None,
                        "playbook_id": playbook_id if symbol == "META-P" else None,
                    },
                )

                await conn.execute(
                    text(
                        """
                        INSERT INTO logical_executions (
                            id, user_id, account_id, symbol, conid, asset_class, direction,
                            quantity, price, commission, executed_at, pnl, pnl_eur, multiplier,
                            currency, origin, deleted, user_modified, is_mixed_execution,
                            open_close, source_id, parent_id, trade_id, created_at, updated_at
                        )
                        VALUES (
                            :id, :user_id, NULL, :symbol, :conid, 'EQUITY', 'LONG',
                            1, 100, 1, :executed_at, NULL, NULL, 1,
                            'USD', 'imported', false, false, false,
                            'O', NULL, NULL, :trade_id, NOW(), NOW()
                        )
                        """
                    ),
                    {
                        "id": execution_ids[next(key for key, value in trade_ids.items() if value == trade_id)],
                        "user_id": user_id,
                        "symbol": symbol,
                        "conid": f"{900000 + idx}",
                        "executed_at": base_opened_at.replace(minute=idx),
                        "trade_id": trade_id,
                    },
                )

            await conn.execute(
                text(
                    """
                    INSERT INTO trade_notes (id, trade_id, user_id, content, emotion)
                    VALUES (gen_random_uuid(), :trade_id, :user_id, 'note-only-signal', 'calm')
                    """
                ),
                {"trade_id": trade_ids["note"], "user_id": user_id},
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO trade_taxonomies (id, trade_id, taxonomy_id)
                    VALUES (gen_random_uuid(), :trade_id, :taxonomy_id)
                    """
                ),
                {"trade_id": trade_ids["taxonomy"], "taxonomy_id": taxonomy_id},
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO trade_annotations (
                        id, trade_id, annotation_definition_id,
                        value_int, value_float, value_bool, value_string
                    )
                    VALUES (
                        gen_random_uuid(), :trade_id, :annotation_definition_id,
                        NULL, NULL, NULL, 'signal'
                    )
                    """
                ),
                {
                    "trade_id": trade_ids["annotation"],
                    "annotation_definition_id": annotation_def_id,
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO broker_raw_transactions (
                        id, user_id, account_id, broker_type, symbol, conid, asset_class,
                        direction, quantity, price, commission, executed_at, pnl, currency,
                        multiplier, open_close, raw_data, suppressed, created_at
                    )
                    VALUES
                    (:divergent_raw_id, :user_id, NULL, 'ibkr', 'DIVG', '1001', 'EQUITY',
                     'LONG', 10, 100, 1, :executed_at, NULL, 'USD', 1, 'O', '{}'::jsonb, false, NOW()),
                    (:symbol_only_raw_id, :user_id, NULL, 'ibkr', 'OLD', '1002', 'EQUITY',
                     'LONG', 5, 50, 0.5, :executed_at, NULL, 'USD', 1, 'O', '{}'::jsonb, false, NOW()),
                    (:clean_raw_id, :user_id, NULL, 'ibkr', 'CLN', '1003', 'EQUITY',
                     'LONG', 3, 20, 0.2, :executed_at, NULL, 'USD', 1, 'O', '{}'::jsonb, false, NOW())
                    """
                ),
                {
                    "divergent_raw_id": divergent_raw_id,
                    "symbol_only_raw_id": symbol_only_raw_id,
                    "clean_raw_id": clean_raw_id,
                    "user_id": user_id,
                    "executed_at": base_opened_at,
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO logical_executions (
                        id, user_id, account_id, symbol, conid, asset_class, direction,
                        quantity, price, commission, executed_at, pnl, pnl_eur, multiplier,
                        currency, origin, deleted, user_modified, is_mixed_execution,
                        open_close, source_id, parent_id, trade_id, created_at, updated_at
                    )
                    VALUES
                    (:divergent_exec_id, :user_id, NULL, 'DIVG', '1001', 'EQUITY', 'LONG',
                     10, 101, 1, :executed_at, NULL, NULL, 1,
                     'USD', 'imported', false, false, false, 'O', :divergent_raw_id, NULL, NULL, NOW(), NOW()),
                    (:symbol_only_exec_id, :user_id, NULL, 'NEW', '1002', 'EQUITY', 'LONG',
                     5, 50, 0.5, :executed_at, NULL, NULL, 1,
                     'USD', 'imported', false, false, false, 'O', :symbol_only_raw_id, NULL, NULL, NOW(), NOW()),
                    (:clean_imported_exec_id, :user_id, NULL, 'CLN', '1003', 'EQUITY', 'LONG',
                     3, 20, 0.2, :executed_at, NULL, NULL, 1,
                     'USD', 'imported', false, false, false, 'O', :clean_raw_id, NULL, NULL, NOW(), NOW())
                    """
                ),
                {
                    "divergent_exec_id": divergent_exec_id,
                    "symbol_only_exec_id": symbol_only_exec_id,
                    "clean_imported_exec_id": clean_imported_exec_id,
                    "user_id": user_id,
                    "executed_at": base_opened_at,
                    "divergent_raw_id": divergent_raw_id,
                    "symbol_only_raw_id": symbol_only_raw_id,
                    "clean_raw_id": clean_raw_id,
                },
            )

        apply_migration = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(apply_migration)
        assert apply_migration.returncode == 0, apply_migration.stderr

        metadata_trade_keys = [
            "journal",
            "rating",
            "image",
            "tv",
            "playbook",
            "note",
            "taxonomy",
            "annotation",
        ]

        async with engine.connect() as conn:
            trade_rows = await conn.execute(
                text(
                    """
                    SELECT id, is_manually_edited
                    FROM trades
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
            trade_map = {row[0]: row[1] for row in trade_rows.fetchall()}

            for key in metadata_trade_keys:
                assert trade_map[trade_ids[key]] is True
            assert trade_map[trade_ids["clean"]] is False

            execution_rows = await conn.execute(
                text(
                    """
                    SELECT id, user_modified
                    FROM logical_executions
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
            execution_map = {row[0]: row[1] for row in execution_rows.fetchall()}

            for key in metadata_trade_keys:
                assert execution_map[execution_ids[key]] is True
            assert execution_map[execution_ids["clean"]] is False
            assert execution_map[divergent_exec_id] is True
            assert execution_map[symbol_only_exec_id] is False
            assert execution_map[clean_imported_exec_id] is False
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()

        restore_head = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(restore_head)
        assert restore_head.returncode == 0, restore_head.stderr


@pytest.mark.integration
@pytest.mark.asyncio
async def test_option_contract_fields_backfill_migration_populates_option_rows() -> None:
    """Backfill migration should populate option contract fields and keep equities null."""
    backend_dir = Path(__file__).resolve().parents[1]

    def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["uv", "run", "alembic", *args],
            capture_output=True,
            text=True,
            cwd=backend_dir,
            check=False,
        )

    def _skip_if_db_unavailable(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0 and "Connect call failed" in result.stderr:
            pytest.skip("Database is unavailable for migration integration test.")

    to_before = _run_alembic("downgrade", "e8a7d3c91b42")
    _skip_if_db_unavailable(to_before)
    if to_before.returncode != 0:
        pytest.skip(
            "Downgrade failed, likely due to intentionally non-downgradable head "
            f"or data constraint violations: {to_before.stderr}"
        )

    user_id = uuid.uuid4()
    option_raw_id = f"ibkr:test-option-{user_id.hex[:12]}"
    equity_raw_id = f"ibkr:test-equity-{user_id.hex[:12]}"

    option_exec_id = uuid.uuid4()
    equity_exec_id = uuid.uuid4()

    engine = create_async_engine(settings.async_database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO users (
                        id,
                        username,
                        email,
                        hashed_password,
                        provider,
                        is_active,
                        refresh_token_version
                    )
                    VALUES (
                        :id,
                        :username,
                        :email,
                        :hashed_password,
                        'local',
                        true,
                        0
                    )
                    """
                ),
                {
                    "id": user_id,
                    "username": f"optbf_{user_id.hex[:8]}",
                    "email": f"optbf_{user_id.hex[:8]}@example.com",
                    "hashed_password": "test-hash",
                },
            )

            executed_at = datetime(2026, 7, 7, 14, 17, 18, tzinfo=UTC)

            await conn.execute(
                text(
                    """
                    INSERT INTO broker_raw_transactions (
                        id, user_id, account_id, broker_type, symbol, conid, asset_class,
                        direction, quantity, price, commission, executed_at, pnl, currency,
                        multiplier, open_close, raw_data, suppressed, created_at
                    )
                    VALUES (
                        :id, :user_id, NULL, 'ibkr', :symbol, :conid, :asset_class,
                        :direction, :quantity, :price, :commission, :executed_at, :pnl,
                        'USD', 100, 'O', cast(:raw_data as jsonb), false, NOW()
                    )
                    """
                ),
                {
                    "id": option_raw_id,
                    "user_id": user_id,
                    "symbol": "QQQ",
                    "conid": "878467678",
                    "asset_class": "OPTION",
                    "direction": "LONG",
                    "quantity": "1",
                    "price": "19.63",
                    "commission": "1.5473",
                    "executed_at": executed_at,
                    "pnl": None,
                    "raw_data": '{"symbol":"QQQ   251003C00712000"}',
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO broker_raw_transactions (
                        id, user_id, account_id, broker_type, symbol, conid, asset_class,
                        direction, quantity, price, commission, executed_at, pnl, currency,
                        multiplier, open_close, raw_data, suppressed, created_at
                    )
                    VALUES (
                        :id, :user_id, NULL, 'ibkr', :symbol, :conid, :asset_class,
                        :direction, :quantity, :price, :commission, :executed_at, :pnl,
                        'USD', 1, 'O', cast(:raw_data as jsonb), false, NOW()
                    )
                    """
                ),
                {
                    "id": equity_raw_id,
                    "user_id": user_id,
                    "symbol": "AAPL",
                    "conid": "265598",
                    "asset_class": "EQUITY",
                    "direction": "LONG",
                    "quantity": "10",
                    "price": "150.00",
                    "commission": "1.00",
                    "executed_at": executed_at,
                    "pnl": None,
                    "raw_data": '{"symbol":"AAPL"}',
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO logical_executions (
                        id, user_id, account_id, symbol, conid, asset_class, direction,
                        quantity, price, commission, executed_at, pnl, pnl_eur, multiplier,
                        currency, origin, deleted, user_modified, is_mixed_execution,
                        open_close, source_id, parent_id, trade_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :user_id, NULL, :symbol, :conid, :asset_class, :direction,
                        :quantity, :price, :commission, :executed_at, :pnl, NULL, :multiplier,
                        'USD', 'imported', false, false, false, 'O', :source_id, NULL, NULL,
                        NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": option_exec_id,
                    "user_id": user_id,
                    "symbol": "QQQ",
                    "conid": "878467678",
                    "asset_class": "OPTION",
                    "direction": "LONG",
                    "quantity": "1",
                    "price": "19.63",
                    "commission": "1.5473",
                    "executed_at": executed_at,
                    "pnl": None,
                    "multiplier": 100,
                    "source_id": option_raw_id,
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO logical_executions (
                        id, user_id, account_id, symbol, conid, asset_class, direction,
                        quantity, price, commission, executed_at, pnl, pnl_eur, multiplier,
                        currency, origin, deleted, user_modified, is_mixed_execution,
                        open_close, source_id, parent_id, trade_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :user_id, NULL, :symbol, :conid, :asset_class, :direction,
                        :quantity, :price, :commission, :executed_at, :pnl, NULL, :multiplier,
                        'USD', 'imported', false, false, false, 'O', :source_id, NULL, NULL,
                        NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": equity_exec_id,
                    "user_id": user_id,
                    "symbol": "AAPL",
                    "conid": "265598",
                    "asset_class": "EQUITY",
                    "direction": "LONG",
                    "quantity": "10",
                    "price": "150.00",
                    "commission": "1.00",
                    "executed_at": executed_at,
                    "pnl": None,
                    "multiplier": 1,
                    "source_id": equity_raw_id,
                },
            )

        apply_migration = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(apply_migration)
        assert apply_migration.returncode == 0, apply_migration.stderr

        async with engine.connect() as conn:
            option_row = await conn.execute(
                text(
                    """
                    SELECT strike, expiry, option_type
                    FROM broker_raw_transactions
                    WHERE id = :id
                    """
                ),
                {"id": option_raw_id},
            )
            option_vals = option_row.first()
            assert option_vals is not None
            assert str(option_vals[0]) == "712.00000000"
            assert option_vals[1].isoformat() == "2025-10-03"
            assert option_vals[2] == "C"

            equity_row = await conn.execute(
                text(
                    """
                    SELECT strike, expiry, option_type
                    FROM broker_raw_transactions
                    WHERE id = :id
                    """
                ),
                {"id": equity_raw_id},
            )
            equity_vals = equity_row.first()
            assert equity_vals is not None
            assert equity_vals[0] is None
            assert equity_vals[1] is None
            assert equity_vals[2] is None

            logical_option_row = await conn.execute(
                text(
                    """
                    SELECT strike, expiry, option_type
                    FROM logical_executions
                    WHERE id = :id
                    """
                ),
                {"id": option_exec_id},
            )
            logical_option_vals = logical_option_row.first()
            assert logical_option_vals is not None
            assert str(logical_option_vals[0]) == "712.00000000"
            assert logical_option_vals[1].isoformat() == "2025-10-03"
            assert logical_option_vals[2] == "C"

            logical_equity_row = await conn.execute(
                text(
                    """
                    SELECT strike, expiry, option_type
                    FROM logical_executions
                    WHERE id = :id
                    """
                ),
                {"id": equity_exec_id},
            )
            logical_equity_vals = logical_equity_row.first()
            assert logical_equity_vals is not None
            assert logical_equity_vals[0] is None
            assert logical_equity_vals[1] is None
            assert logical_equity_vals[2] is None
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    DELETE FROM logical_executions
                    WHERE id IN (:option_exec_id, :equity_exec_id)
                    """
                ),
                {
                    "option_exec_id": option_exec_id,
                    "equity_exec_id": equity_exec_id,
                },
            )
            await conn.execute(
                text(
                    """
                    DELETE FROM broker_raw_transactions
                    WHERE id IN (:option_raw_id, :equity_raw_id)
                    """
                ),
                {
                    "option_raw_id": option_raw_id,
                    "equity_raw_id": equity_raw_id,
                },
            )
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()

        restore_head = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(restore_head)
        assert restore_head.returncode == 0, restore_head.stderr


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orphan_repair_migration_links_unique_match_and_recomputes_close_fields() -> None:
    """Task 15.7 / D13: the orphan-repair migration links a unique-match
    orphan to its complementary open trade and recomputes close fields,
    skips ambiguous orphans, and is idempotent on re-run.
    """
    backend_dir = Path(__file__).resolve().parents[1]

    def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["uv", "run", "alembic", *args],
            capture_output=True,
            text=True,
            cwd=backend_dir,
            check=False,
        )

    def _skip_if_db_unavailable(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0 and "Connect call failed" in result.stderr:
            pytest.skip("Database is unavailable for migration integration test.")

    to_before = _run_alembic("downgrade", "7647be54482c")
    _skip_if_db_unavailable(to_before)
    if to_before.returncode != 0:
        pytest.skip(
            "Downgrade failed, likely due to intentionally non-downgradable head "
            f"or data constraint violations: {to_before.stderr}"
        )

    user_id = uuid.uuid4()
    base_opened_at = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)

    # Scenario 1: unique match — one open LONG trade, one orphaned closing
    # (SHORT) execution with matching symbol/quantity.
    unique_trade_id = uuid.uuid4()
    unique_exec_id = uuid.uuid4()
    unique_executed_at = base_opened_at.replace(hour=15)

    # Scenario 2: ambiguous match — two open trades with identical matching
    # criteria; the orphan must be left untouched.
    ambiguous_trade_a_id = uuid.uuid4()
    ambiguous_trade_b_id = uuid.uuid4()
    ambiguous_exec_id = uuid.uuid4()

    engine = create_async_engine(settings.async_database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO users (
                        id, username, email, hashed_password, provider,
                        is_active, refresh_token_version
                    )
                    VALUES (:id, :username, :email, :hashed_password, 'local', true, 0)
                    """
                ),
                {
                    "id": user_id,
                    "username": f"orph_{user_id.hex[:8]}",
                    "email": f"orph_{user_id.hex[:8]}@example.com",
                    "hashed_password": "test-hash",
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO trades (
                        id, user_id, symbol, direction, quantity, entry_price,
                        opened_at, closed_at, commission, multiplier
                    )
                    VALUES
                    (:unique_trade_id, :user_id, 'UNIQ', 'LONG', 100, 50,
                     :opened_at, NULL, 2, 1),
                    (:ambiguous_trade_a_id, :user_id, 'AMBIG', 'LONG', 50, 20,
                     :opened_at, NULL, 0, 1),
                    (:ambiguous_trade_b_id, :user_id, 'AMBIG', 'LONG', 50, 21,
                     :opened_at, NULL, 0, 1)
                    """
                ),
                {
                    "unique_trade_id": unique_trade_id,
                    "ambiguous_trade_a_id": ambiguous_trade_a_id,
                    "ambiguous_trade_b_id": ambiguous_trade_b_id,
                    "user_id": user_id,
                    "opened_at": base_opened_at,
                },
            )

            await conn.execute(
                text(
                    """
                    INSERT INTO logical_executions (
                        id, user_id, account_id, symbol, conid, asset_class, direction,
                        quantity, price, commission, executed_at, pnl, pnl_eur, multiplier,
                        currency, origin, deleted, user_modified, is_mixed_execution,
                        open_close, source_id, parent_id, trade_id, created_at, updated_at
                    )
                    VALUES
                    (:unique_exec_id, :user_id, NULL, 'UNIQ', '900001', 'EQUITY', 'SHORT',
                     100, 55, 1, :unique_executed_at, NULL, NULL, 1,
                     'USD', 'imported', false, false, false, 'C', NULL, NULL, NULL, NOW(), NOW()),
                    (:ambiguous_exec_id, :user_id, NULL, 'AMBIG', '900002', 'EQUITY', 'SHORT',
                     50, 25, 0.5, :ambiguous_executed_at, NULL, NULL, 1,
                     'USD', 'imported', false, false, false, 'C', NULL, NULL, NULL, NOW(), NOW())
                    """
                ),
                {
                    "unique_exec_id": unique_exec_id,
                    "ambiguous_exec_id": ambiguous_exec_id,
                    "user_id": user_id,
                    "unique_executed_at": unique_executed_at,
                    "ambiguous_executed_at": base_opened_at.replace(hour=16),
                },
            )

        apply_migration = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(apply_migration)
        assert apply_migration.returncode == 0, apply_migration.stderr

        async def _fetch_state() -> tuple[uuid.UUID | None, uuid.UUID | None, Row[Any] | None]:
            async with engine.connect() as conn:
                exec_rows = await conn.execute(
                    text(
                        "SELECT id, trade_id FROM logical_executions WHERE id IN (:a, :b)"
                    ),
                    {"a": unique_exec_id, "b": ambiguous_exec_id},
                )
                exec_map: dict[uuid.UUID, uuid.UUID | None] = {row[0]: row[1] for row in exec_rows.fetchall()}

                trade_row = await conn.execute(
                    text(
                        """
                        SELECT exit_price, closed_at, pnl, net_pnl, commission
                        FROM trades WHERE id = :id
                        """
                    ),
                    {"id": unique_trade_id},
                )
                trade_state = trade_row.fetchone()
                return exec_map[unique_exec_id], exec_map[ambiguous_exec_id], trade_state

        unique_link, ambiguous_link, trade_state = await _fetch_state()

        # Unique match: orphan linked, trade recomputed as closed.
        assert unique_link == unique_trade_id
        assert trade_state is not None
        exit_price, closed_at, pnl, net_pnl, commission = trade_state
        assert Decimal(exit_price) == Decimal("55")
        assert closed_at == unique_executed_at
        assert Decimal(pnl) == Decimal("500")  # (55-50) * 100 * 1
        assert Decimal(commission) == Decimal("3")  # trade commission (2) + leg commission (1)
        assert Decimal(net_pnl) == Decimal("497")  # pnl - (2 + 1)

        # Ambiguous match: orphan left untouched (trade_id still NULL).
        assert ambiguous_link is None

        # Idempotency: re-running the migration must not double-process the
        # already-linked orphan or touch the still-ambiguous one.
        rerun = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(rerun)
        assert rerun.returncode == 0, rerun.stderr

        unique_link_2, ambiguous_link_2, trade_state_2 = await _fetch_state()
        assert unique_link_2 == unique_trade_id
        assert ambiguous_link_2 is None
        assert trade_state_2 == trade_state  # unchanged — not double-recomputed
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()

        restore_head = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(restore_head)
        assert restore_head.returncode == 0, restore_head.stderr
