"""Unit tests for BrokerService — all DB and HTTP calls are mocked.

Tests cover the Schwab OAuth PKCE flow, token storage, disconnect, status
query, and trade synchronisation including deduplication logic.  No real
database or HTTP connections are made.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BrokerConnectionNotFoundError
from app.models.trade import AssetClass, Direction
from app.schemas.broker import BrokerStatusResponse, SchwabSyncResult
from app.schemas.trade import TradeCreate
from app.services import broker_service as bs_module
from app.services.broker_service import BrokerService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trade_create(broker_order_id: str | None = "ord-1") -> TradeCreate:
    """Build a minimal :class:`TradeCreate` for test fixtures.

    Args:
        broker_order_id: The broker order identifier. Defaults to ``"ord-1"``.

    Returns:
        A :class:`TradeCreate` with sensible defaults.
    """
    now = datetime.now(tz=UTC)
    return TradeCreate(
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("10"),
        entry_price=Decimal("150"),
        exit_price=Decimal("150"),
        opened_at=now,
        closed_at=now,
        currency="USD",
        broker_order_id=broker_order_id,
    )


def _mock_connection(
    last_sync_at: datetime | None = None,
    expires_in_seconds: int = 3600,
) -> MagicMock:
    """Build a mock BrokerConnection ORM instance.

    Args:
        last_sync_at: Value for the ``last_sync_at`` attribute.
        expires_in_seconds: How many seconds from now the token expires.
            Positive means not yet expired; use a small value (e.g. 60) to
            simulate an expiring token.

    Returns:
        A :class:`MagicMock` that looks like a :class:`BrokerConnection`.
    """
    conn = MagicMock()
    conn.access_token = "encrypted-access"
    conn.refresh_token = "encrypted-refresh"
    conn.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
    conn.last_sync_at = last_sync_at
    return conn


def _build_service(
    mock_session: AsyncMock,
) -> tuple[BrokerService, MagicMock, MagicMock]:
    """Construct a BrokerService with mocked repository and HTTP client.

    Returns:
        A tuple of ``(service, mock_repo_instance, mock_client_instance)``.
    """
    mock_repo = MagicMock()
    mock_client = MagicMock()

    with (
        patch(
            "app.services.broker_service.BrokerConnectionRepository",
            return_value=mock_repo,
        ),
        patch("app.services.broker_service.SchwabClient", return_value=mock_client),
    ):
        svc = BrokerService(mock_session)

    # Overwrite the internal attributes directly so subsequent calls use our mocks
    svc._repo = mock_repo  # type: ignore[attr-defined]
    svc._client = mock_client  # type: ignore[attr-defined]
    return svc, mock_repo, mock_client


# ---------------------------------------------------------------------------
# Tests: get_schwab_connect_url
# ---------------------------------------------------------------------------


async def test_get_schwab_connect_url_returns_url_and_stores_state() -> None:
    """get_schwab_connect_url() returns a URL and stores state in _pending_states.

    After calling the method, ``_pending_states`` should contain one entry
    keyed by the generated state token, mapping to ``(user_id, code_verifier)``.
    """
    bs_module._pending_states.clear()
    mock_session = AsyncMock()
    svc, _, mock_client = _build_service(mock_session)

    user_id = uuid.uuid4()
    mock_client.get_authorization_url.return_value = (
        "https://schwab.example/auth?code=x"
    )

    url = await svc.get_schwab_connect_url(user_id)

    assert url == "https://schwab.example/auth?code=x"
    assert len(bs_module._pending_states) == 1
    stored_user_id, verifier = next(iter(bs_module._pending_states.values()))
    assert stored_user_id == user_id
    assert isinstance(verifier, str) and len(verifier) > 0

    bs_module._pending_states.clear()


# ---------------------------------------------------------------------------
# Tests: handle_schwab_callback
# ---------------------------------------------------------------------------


async def test_handle_schwab_callback_success() -> None:
    """handle_schwab_callback() exchanges the code, encrypts tokens, and commits.

    The state is popped from _pending_states after a successful callback
    so it cannot be replayed.
    """
    bs_module._pending_states.clear()
    user_id = uuid.uuid4()
    state = "test-state-abc"
    bs_module._pending_states[state] = (user_id, "verifier-123")

    mock_session = AsyncMock()
    svc, mock_repo, mock_client = _build_service(mock_session)

    mock_client.exchange_code = AsyncMock(
        return_value={
            "access_token": "raw-access",
            "refresh_token": "raw-refresh",
            "expires_in": 1800,
        }
    )
    mock_repo.upsert = AsyncMock()

    with (
        patch(
            "app.services.broker_service.encrypt_token", return_value="encrypted"
        ) as mock_enc,
    ):
        await svc.handle_schwab_callback(code="auth-code-xyz", state=state)

    # State was consumed
    assert state not in bs_module._pending_states

    # exchange_code called with correct args
    mock_client.exchange_code.assert_called_once_with(
        code="auth-code-xyz",
        code_verifier="verifier-123",
    )

    # encrypt_token called twice (access + refresh)
    assert mock_enc.call_count == 2

    # upsert persisted the connection
    mock_repo.upsert.assert_called_once()
    call_kwargs: dict[str, Any] = mock_repo.upsert.call_args.kwargs
    assert call_kwargs["user_id"] == user_id
    assert call_kwargs["broker"] == "schwab"

    # Session committed
    mock_session.commit.assert_called_once()


async def test_handle_schwab_callback_invalid_state_raises() -> None:
    """handle_schwab_callback() raises ValueError for an unknown state token.

    This guards against CSRF attacks and replayed state parameters.
    """
    bs_module._pending_states.clear()
    mock_session = AsyncMock()
    svc, _, _ = _build_service(mock_session)

    with pytest.raises(ValueError, match="Unknown or expired OAuth state"):
        await svc.handle_schwab_callback(code="code", state="nonexistent-state")


# ---------------------------------------------------------------------------
# Tests: disconnect_schwab
# ---------------------------------------------------------------------------


async def test_disconnect_schwab_success() -> None:
    """disconnect_schwab() deletes the connection and commits.

    When a Schwab connection exists for the user, it is removed via the
    repository and the session is committed.
    """
    mock_session = AsyncMock()
    svc, mock_repo, _ = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=_mock_connection())
    mock_repo.delete = AsyncMock()

    await svc.disconnect_schwab(user_id)

    mock_repo.delete.assert_called_once_with(user_id=user_id, broker="schwab")
    mock_session.commit.assert_called_once()


async def test_disconnect_schwab_not_found_raises() -> None:
    """disconnect_schwab() raises BrokerConnectionNotFoundError when not connected.

    If the user has no stored Schwab connection, the service raises rather
    than silently succeeding.
    """
    mock_session = AsyncMock()
    svc, mock_repo, _ = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=None)

    with pytest.raises(BrokerConnectionNotFoundError):
        await svc.disconnect_schwab(user_id)


# ---------------------------------------------------------------------------
# Tests: get_schwab_status
# ---------------------------------------------------------------------------


async def test_get_schwab_status_connected() -> None:
    """get_schwab_status() returns connected=True and the last_sync_at timestamp.

    When a stored connection exists, the status reflects the connection
    metadata rather than returning a disconnected placeholder.
    """
    mock_session = AsyncMock()
    svc, mock_repo, _ = _build_service(mock_session)
    user_id = uuid.uuid4()

    last_sync = datetime(2024, 3, 1, 12, 0, 0, tzinfo=UTC)
    mock_repo.get_by_user_broker = AsyncMock(
        return_value=_mock_connection(last_sync_at=last_sync)
    )

    status: BrokerStatusResponse = await svc.get_schwab_status(user_id)

    assert status.connected is True
    assert status.last_sync_at == last_sync


async def test_get_schwab_status_not_connected() -> None:
    """get_schwab_status() returns connected=False when no connection is stored.

    The method never raises for a missing connection — it returns a clean
    disconnected status instead.
    """
    mock_session = AsyncMock()
    svc, mock_repo, _ = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=None)

    status: BrokerStatusResponse = await svc.get_schwab_status(user_id)

    assert status.connected is False
    assert status.last_sync_at is None


# ---------------------------------------------------------------------------
# Tests: sync_schwab_trades
# ---------------------------------------------------------------------------


async def test_sync_schwab_not_connected_raises() -> None:
    """sync_schwab_trades() raises BrokerConnectionNotFoundError when not connected.

    The sync cannot proceed without stored tokens; the caller should redirect
    the user to the connect flow.
    """
    mock_session = AsyncMock()
    svc, mock_repo, _ = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=None)

    with pytest.raises(BrokerConnectionNotFoundError):
        await svc.sync_schwab_trades(user_id)


async def test_sync_schwab_imports_new_trades() -> None:
    """sync_schwab_trades() imports orders that are not already in the database.

    Two orders are returned by the mocked Schwab client.  Neither exists in
    the database, so both should be imported and the result counts should
    reflect two new trades.
    """
    mock_session = AsyncMock()
    svc, mock_repo, mock_client = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=_mock_connection())
    mock_repo.upsert = AsyncMock()
    mock_repo.update_last_sync = AsyncMock()

    # Two normalised trades returned by the mocked normalizer
    trade_1 = _make_trade_create("ord-1")
    trade_2 = _make_trade_create("ord-2")

    mock_client.get_orders = AsyncMock(
        return_value=[{"orderId": "ord-1"}, {"orderId": "ord-2"}]
    )

    # DB returns no existing broker_order_ids (nothing skipped)
    mock_execute_result = MagicMock()
    mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.flush = AsyncMock()

    with (
        patch("app.services.broker_service.decrypt_token", return_value="raw-token"),
        patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            side_effect=[trade_1, trade_2],
        ),
    ):
        result: SchwabSyncResult = await svc.sync_schwab_trades(user_id, days=7)

    assert result.imported_count == 2
    assert result.skipped_count == 0
    assert result.errors == []

    mock_repo.update_last_sync.assert_called_once_with(user_id=user_id, broker="schwab")
    mock_session.commit.assert_called_once()


async def test_sync_schwab_deduplicates_existing_trades() -> None:
    """sync_schwab_trades() skips orders whose broker_order_id is already in the DB.

    When the database already contains a trade with the same broker_order_id,
    the sync increments skipped_count instead of importing a duplicate.
    """
    mock_session = AsyncMock()
    svc, mock_repo, mock_client = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=_mock_connection())
    mock_repo.upsert = AsyncMock()
    mock_repo.update_last_sync = AsyncMock()

    trade_1 = _make_trade_create("ord-already-exists")
    mock_client.get_orders = AsyncMock(return_value=[{"orderId": "ord-already-exists"}])

    # DB returns the existing broker_order_id
    mock_execute_result = MagicMock()
    mock_execute_result.__iter__ = MagicMock(
        return_value=iter([("ord-already-exists",)])
    )
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.flush = AsyncMock()

    with (
        patch("app.services.broker_service.decrypt_token", return_value="raw-token"),
        patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            return_value=trade_1,
        ),
    ):
        result: SchwabSyncResult = await svc.sync_schwab_trades(user_id)

    assert result.imported_count == 0
    assert result.skipped_count == 1


async def test_sync_schwab_skips_unnormalisable_orders() -> None:
    """sync_schwab_trades() counts skipped orders when normalize() returns None.

    Orders that the normalizer cannot process (wrong status, missing fields,
    etc.) are counted as skipped and do not raise an exception.
    """
    mock_session = AsyncMock()
    svc, mock_repo, mock_client = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=_mock_connection())
    mock_repo.upsert = AsyncMock()
    mock_repo.update_last_sync = AsyncMock()

    mock_client.get_orders = AsyncMock(return_value=[{"orderId": "ord-skip"}])

    mock_execute_result = MagicMock()
    mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.flush = AsyncMock()

    with (
        patch("app.services.broker_service.decrypt_token", return_value="raw-token"),
        patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            return_value=None,
        ),
    ):
        result: SchwabSyncResult = await svc.sync_schwab_trades(user_id)

    assert result.imported_count == 0
    assert result.skipped_count == 1


async def test_sync_schwab_records_normalisation_errors() -> None:
    """sync_schwab_trades() records errors for orders that raise during normalisation.

    If normalize() raises an exception for an order, the error is captured
    in the result's ``errors`` list and the sync continues with remaining orders.
    """
    mock_session = AsyncMock()
    svc, mock_repo, mock_client = _build_service(mock_session)
    user_id = uuid.uuid4()

    mock_repo.get_by_user_broker = AsyncMock(return_value=_mock_connection())
    mock_repo.upsert = AsyncMock()
    mock_repo.update_last_sync = AsyncMock()

    mock_client.get_orders = AsyncMock(return_value=[{"orderId": "bad-order"}])

    mock_execute_result = MagicMock()
    mock_execute_result.__iter__ = MagicMock(return_value=iter([]))
    mock_session.execute = AsyncMock(return_value=mock_execute_result)
    mock_session.flush = AsyncMock()

    with (
        patch("app.services.broker_service.decrypt_token", return_value="raw-token"),
        patch(
            "app.services.broker_service.SchwabOrderNormalizer.normalize",
            side_effect=ValueError("unexpected field"),
        ),
    ):
        result: SchwabSyncResult = await svc.sync_schwab_trades(user_id)

    assert result.imported_count == 0
    assert len(result.errors) == 1
    assert "bad-order" in result.errors[0]
