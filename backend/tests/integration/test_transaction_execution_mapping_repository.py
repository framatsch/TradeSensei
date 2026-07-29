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

"""Integration tests for TransactionExecutionMappingRepository.

This is the highest-priority file (currently at 0% coverage), so any tests
here contribute significantly to overall coverage.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.logical_execution import LogicalExecution
from app.models.transaction_execution_mapping import TransactionExecutionMapping
from app.models.user import User
from app.repositories.transaction_execution_mapping_repository import (
    TransactionExecutionMappingRepository,
)

pytestmark = pytest.mark.asyncio


async def _make_user(session: AsyncSession) -> User:
    user = User(username=f"u_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex}@test.com", hashed_password="x")
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _make_raw_transaction(session: AsyncSession, user_id: uuid.UUID, raw_id: str) -> BrokerRawTransaction:
    raw = BrokerRawTransaction(
        id=raw_id,
        user_id=user_id,
        broker_type="ibkr",
        symbol="AAPL",
        asset_class="EQUITY",
        direction="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        executed_at=datetime(2024, 1, 10, 9, 30, tzinfo=UTC),
    )
    session.add(raw)
    await session.flush()
    await session.refresh(raw)
    return raw


async def _make_logical_execution(session: AsyncSession, user_id: uuid.UUID) -> LogicalExecution:
    from app.models.trade import AssetClass, Direction

    le = LogicalExecution(
        user_id=user_id,
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        direction=Direction.LONG,
        quantity=Decimal("10"),
        price=Decimal("100"),
        executed_at=datetime(2024, 1, 10, 9, 30, tzinfo=UTC),
        origin="imported",
    )
    session.add(le)
    await session.flush()
    await session.refresh(le)
    return le


async def _make_mapping(
    session: AsyncSession, raw_transaction_id: str, logical_execution_id: uuid.UUID
) -> TransactionExecutionMapping:
    mapping = TransactionExecutionMapping(
        raw_transaction_id=raw_transaction_id,
        logical_execution_id=logical_execution_id,
    )
    session.add(mapping)
    await session.flush()
    return mapping


@pytest.mark.integration
async def test_exists_for_raw_transaction_true(db_session: AsyncSession):
    """exists_for_raw_transaction returns True when mapping exists."""
    user = await _make_user(db_session)
    raw_id = f"ibkr:test_{uuid.uuid4().hex[:8]}"
    raw = await _make_raw_transaction(db_session, user.id, raw_id)
    le = await _make_logical_execution(db_session, user.id)
    await _make_mapping(db_session, raw.id, le.id)

    repo = TransactionExecutionMappingRepository(db_session)
    result = await repo.exists_for_raw_transaction(raw.id)
    assert result is True


@pytest.mark.integration
async def test_exists_for_raw_transaction_false(db_session: AsyncSession):
    """exists_for_raw_transaction returns False when no mapping exists."""
    repo = TransactionExecutionMappingRepository(db_session)
    result = await repo.exists_for_raw_transaction("ibkr:nonexistent_raw_id")
    assert result is False


@pytest.mark.integration
async def test_list_execution_ids_for_raw_empty(db_session: AsyncSession):
    """list_execution_ids_for_raw returns empty list when no mapping exists."""
    repo = TransactionExecutionMappingRepository(db_session)
    result = await repo.list_execution_ids_for_raw("ibkr:no_such_raw")
    assert result == []


@pytest.mark.integration
async def test_list_execution_ids_for_raw_single(db_session: AsyncSession):
    """list_execution_ids_for_raw returns correct execution IDs."""
    user = await _make_user(db_session)
    raw_id = f"ibkr:list_test_{uuid.uuid4().hex[:8]}"
    raw = await _make_raw_transaction(db_session, user.id, raw_id)
    le = await _make_logical_execution(db_session, user.id)
    await _make_mapping(db_session, raw.id, le.id)

    repo = TransactionExecutionMappingRepository(db_session)
    result = await repo.list_execution_ids_for_raw(raw.id)
    assert len(result) == 1
    assert result[0] == le.id


@pytest.mark.integration
async def test_list_execution_ids_for_raw_multiple(db_session: AsyncSession):
    """list_execution_ids_for_raw returns all mapped execution IDs."""
    user = await _make_user(db_session)
    raw_id = f"ibkr:multi_{uuid.uuid4().hex[:8]}"
    raw = await _make_raw_transaction(db_session, user.id, raw_id)
    le1 = await _make_logical_execution(db_session, user.id)
    le2 = await _make_logical_execution(db_session, user.id)
    await _make_mapping(db_session, raw.id, le1.id)
    await _make_mapping(db_session, raw.id, le2.id)

    repo = TransactionExecutionMappingRepository(db_session)
    result = await repo.list_execution_ids_for_raw(raw.id)
    assert len(result) == 2
    assert le1.id in result
    assert le2.id in result


@pytest.mark.integration
async def test_repr(db_session: AsyncSession):
    """__repr__ of TransactionExecutionMapping returns useful debug string."""
    user = await _make_user(db_session)
    raw_id = f"ibkr:repr_{uuid.uuid4().hex[:8]}"
    raw = await _make_raw_transaction(db_session, user.id, raw_id)
    le = await _make_logical_execution(db_session, user.id)
    mapping = await _make_mapping(db_session, raw.id, le.id)

    repr_str = repr(mapping)
    assert "TransactionExecutionMapping" in repr_str
    assert raw.id in repr_str
