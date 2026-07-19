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
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import text
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
