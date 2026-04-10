from unittest.mock import AsyncMock

import pytest

from app.services.execution import ExecutionService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def service(repo):
    return ExecutionService(repo)


@pytest.mark.asyncio
async def test_reassign_execution_happy_path(service, repo):
    pass


@pytest.mark.asyncio
async def test_reassign_execution_symbol_mismatch(service, repo):
    pass


@pytest.mark.asyncio
async def test_reassign_execution_account_mismatch(service, repo):
    pass


@pytest.mark.asyncio
async def test_reassign_execution_source_trade_deleted_when_empty(service, repo):
    pass


@pytest.mark.asyncio
async def test_detach_execution_happy_path(service, repo):
    pass


@pytest.mark.asyncio
async def test_detach_execution_cannot_detach_last(service, repo):
    pass


@pytest.mark.asyncio
async def test_detach_execution_new_trade_aggregated(service, repo):
    pass
