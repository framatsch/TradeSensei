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

"""Unit tests for split-aware methods in ExecutionRepository."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.execution import ExecutionRepository


def _repo_with_session() -> tuple[ExecutionRepository, AsyncMock]:
    session = AsyncMock()
    repo = ExecutionRepository(session)
    return repo, session


@pytest.mark.unit
async def test_update_trade_id_updates_single_execution() -> None:
    repo, session = _repo_with_session()
    session.execute.return_value = MagicMock(rowcount=1)

    ok = await repo.update_trade_id(uuid.uuid4(), uuid.uuid4())

    assert ok is True
    session.execute.assert_awaited_once()
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_update_trade_id_returns_false_for_missing_execution() -> None:
    repo, session = _repo_with_session()
    session.execute.return_value = MagicMock(rowcount=0)

    ok = await repo.update_trade_id(uuid.uuid4(), uuid.uuid4())

    assert ok is False


@pytest.mark.unit
async def test_get_by_parent_id_returns_children() -> None:
    repo, session = _repo_with_session()
    child1 = MagicMock()
    child2 = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [child1, child2]
    session.execute.return_value = MagicMock(scalars=lambda: scalars)

    result = await repo.get_by_parent_id(uuid.uuid4())

    assert result == [child1, child2]


@pytest.mark.unit
async def test_find_orphaned_children_filters_split_without_trade() -> None:
    repo, session = _repo_with_session()
    orphan = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [orphan]
    session.execute.return_value = MagicMock(scalars=lambda: scalars)

    result = await repo.find_orphaned_children(uuid.uuid4(), uuid.uuid4())

    assert result == [orphan]


@pytest.mark.unit
async def test_bulk_update_trade_ids_groups_updates() -> None:
    repo, session = _repo_with_session()
    session.execute.return_value = MagicMock(rowcount=2)
    session.identity_map = {}
    trade_id = uuid.uuid4()

    count = await repo.bulk_update_trade_ids(
        [
            (uuid.uuid4(), trade_id),
            (uuid.uuid4(), trade_id),
        ]
    )

    assert count == 2
    session.flush.assert_awaited_once()


@pytest.mark.unit
async def test_bulk_update_trade_ids_batches_large_group() -> None:
    repo, session = _repo_with_session()
    session.execute.side_effect = [
        MagicMock(rowcount=500),
        MagicMock(rowcount=500),
        MagicMock(rowcount=1),
    ]
    session.identity_map = {}
    trade_id = uuid.uuid4()
    pairs = [(uuid.uuid4(), trade_id) for _ in range(1001)]

    count = await repo.bulk_update_trade_ids(pairs)

    assert count == 1001
    assert session.execute.await_count == 3


@pytest.mark.unit
async def test_bulk_update_trade_ids_empty_returns_zero() -> None:
    repo, session = _repo_with_session()

    count = await repo.bulk_update_trade_ids([])

    assert count == 0
    session.execute.assert_not_called()


@pytest.mark.unit
async def test_concurrent_update_trade_id_calls_safe() -> None:
    repo, session = _repo_with_session()
    session.execute.return_value = MagicMock(rowcount=1)

    await asyncio.gather(
        repo.update_trade_id(uuid.uuid4(), uuid.uuid4()),
        repo.update_trade_id(uuid.uuid4(), uuid.uuid4()),
        repo.update_trade_id(uuid.uuid4(), uuid.uuid4()),
    )

    assert session.execute.await_count == 3


@pytest.mark.unit
def test_iter_batches_splits_input_by_batch_size() -> None:
    ids = [uuid.uuid4() for _ in range(5)]

    batches = list(ExecutionRepository.iter_batches(ids, batch_size=2))

    assert batches == [ids[:2], ids[2:4], ids[4:5]]


@pytest.mark.unit
def test_iter_batches_rejects_non_positive_batch_size() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        list(ExecutionRepository.iter_batches([uuid.uuid4()], batch_size=0))
