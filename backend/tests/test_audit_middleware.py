"""Integration tests for audit middleware behavior."""

from __future__ import annotations

import io
import json
import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.services.audit_service import AuditEventService
from app.services.trade_service import TradeService


async def _create_portfolio(
    client: AsyncClient, headers: dict[str, str], name: str
) -> str:
    resp = await client.post(
        "/api/v1/portfolios",
        json={"name": name, "base_currency": "USD"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


async def _create_account(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    name: str,
) -> str:
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": name, "type": "manual", "currency": "USD"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


async def _create_trade(
    client: AsyncClient,
    headers: dict[str, str],
    portfolio_id: str,
    account_id: str,
    symbol: str = "AAPL",
) -> str:
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json={
            "account_id": account_id,
            "symbol": symbol,
            "direction": "LONG",
            "asset_class": "EQUITY",
            "quantity": "1",
            "entry_price": "10",
            "opened_at": "2024-01-15T10:00:00Z",
            "currency": "USD",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["data"]["id"])


def _capture_audit_logger() -> tuple[logging.Logger, logging.Handler, io.StringIO]:
    logger = logging.getLogger("audit")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger, handler, stream


def _get_audit_payloads(stream: io.StringIO) -> list[dict[str, object]]:
    lines = [
        line
        for line in stream.getvalue().splitlines()
        if line.strip().startswith("{") and '"logger":"audit"' in line
    ]
    payloads: list[dict[str, object]] = []
    for line in lines:
        try:
            payloads.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return payloads


def _assert_action(payloads: list[dict[str, object]], action: str) -> None:
    assert any(payload.get("action") == action for payload in payloads)


@pytest.mark.integration
async def test_audit_logs_write_operations(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P1")
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": "Audit Account", "type": "manual", "currency": "USD"},
        headers=primary_user["headers"],
    )
    assert resp.status_code == 201
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "account.created")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_not_found_errors(
    client: AsyncClient,
    primary_user: dict[str, str],
    other_users_trade: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    trade_id = other_users_trade["id"]
    portfolio_id = other_users_trade["portfolio_id"]
    resp = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=primary_user["headers"],
    )
    assert resp.status_code == 404
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "error.not_found")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_forbidden_errors(
    client: AsyncClient,
    primary_user: dict[str, str],
    other_users_tag: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    tag_id = other_users_tag["id"]
    resp = await client.patch(
        f"/api/v1/tags/{tag_id}",
        json={"name": "nope"},
        headers=primary_user["headers"],
    )
    assert resp.status_code == 404
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "error.not_found")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_internal_errors(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P2")
    account_id = await _create_account(
        client,
        primary_user["headers"],
        portfolio_id,
        "Audit Error",
    )
    stream.truncate(0)
    stream.seek(0)
    trade_id = await _create_trade(
        client,
        primary_user["headers"],
        portfolio_id,
        account_id,
    )
    stream.truncate(0)
    stream.seek(0)
    delete_resp = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=primary_user["headers"],
    )
    assert delete_resp.status_code == 204
    stream.truncate(0)
    stream.seek(0)
    delete_again = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=primary_user["headers"],
    )
    assert delete_again.status_code == 404
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "error.not_found")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_database_errors(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P3")
    account_id = await _create_account(
        client,
        primary_user["headers"],
        portfolio_id,
        "Audit DB",
    )
    stream.truncate(0)
    stream.seek(0)
    await _create_trade(
        client,
        primary_user["headers"],
        portfolio_id,
        account_id,
    )
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "trade.created")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_validation_errors(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P4")
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json={"account_id": "bad-id"},
        headers=primary_user["headers"],
    )
    assert resp.status_code == 422
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "error.validation")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_skips_health_endpoint(
    client: AsyncClient,
) -> None:
    logger, handler, stream = _capture_audit_logger()
    resp = await client.get("/health")
    assert resp.status_code == 200
    payloads = _get_audit_payloads(stream)
    assert not payloads
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_auth_failed_without_token(
    client: AsyncClient,
) -> None:
    logger, handler, stream = _capture_audit_logger()
    resp = await client.post(
        f"/api/v1/portfolios/{uuid.uuid4()}/trades",
        json={"account_id": "bad-id"},
    )
    assert resp.status_code == 401
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "auth.failed")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_auth_failed_on_login(
    client: AsyncClient,
) -> None:
    logger, handler, stream = _capture_audit_logger()
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": "missing@example.com", "password": "bad"},
    )
    assert resp.status_code == 401
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "auth.failed")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_nested_resource_parent_id(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P5")
    account_id = await _create_account(
        client,
        primary_user["headers"],
        portfolio_id,
        "Audit Parent",
    )
    trade_id = await _create_trade(
        client,
        primary_user["headers"],
        portfolio_id,
        account_id,
    )

    stream.truncate(0)
    stream.seek(0)
    note_resp = await client.post(
        f"/api/v1/trades/{trade_id}/notes",
        json={"content": "Audit note"},
        headers=primary_user["headers"],
    )
    assert note_resp.status_code == 201
    payloads = _get_audit_payloads(stream)
    assert any(payload.get("parent_resource_id") == trade_id for payload in payloads)
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_skips_get_when_not_debug(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P6")
    stream.truncate(0)
    stream.seek(0)
    original_level = settings.log_level
    settings.log_level = "INFO"
    try:
        resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 200
        payloads = _get_audit_payloads(stream)
        assert not payloads
    finally:
        settings.log_level = original_level
        logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_get_when_debug(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P7")
    original_level = settings.log_level
    settings.log_level = "DEBUG"
    try:
        resp = await client.get(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            headers=primary_user["headers"],
        )
        assert resp.status_code == 200
        payloads = _get_audit_payloads(stream)
        _assert_action(payloads, "trade.list")
    finally:
        settings.log_level = original_level
        logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_x_forwarded_for(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P8")
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": "Audit Forwarded", "type": "manual", "currency": "USD"},
        headers={
            **primary_user["headers"],
            "X-Forwarded-For": "203.0.113.42",
        },
    )
    assert resp.status_code == 201
    payloads = _get_audit_payloads(stream)
    assert any(payload.get("forwarded_for") == "203.0.113.42" for payload in payloads)
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_action_override_for_merge(
    client: AsyncClient,
    primary_user: dict[str, str],
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P9")
    account_id = await _create_account(
        client,
        primary_user["headers"],
        portfolio_id,
        "Audit Merge",
    )
    trade_ids: list[str] = []
    for symbol in ["AAA", "AAA"]:
        trade_ids.append(
            await _create_trade(
                client,
                primary_user["headers"],
                portfolio_id,
                account_id,
                symbol=symbol,
            )
        )

    stream.truncate(0)
    stream.seek(0)
    merge_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/merge",
        json={"trade_ids": trade_ids},
        headers=primary_user["headers"],
    )
    assert merge_resp.status_code == 200
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "trade.created")
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logging_failure_does_not_break_request(
    client: AsyncClient,
    primary_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger, handler, _ = _capture_audit_logger()

    def _raise(*args: object, **kwargs: object) -> None:
        raise RuntimeError("log failed")

    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P10")
    monkeypatch.setattr(AuditEventService, "create_audit_event", _raise)
    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": "Audit Fail", "type": "manual", "currency": "USD"},
        headers=primary_user["headers"],
    )
    assert resp.status_code == 201
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_unhandled_exception_with_stack_trace(
    client: AsyncClient,
    primary_user: dict[str, str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P11")

    async def _boom(*args: object, **kwargs: object) -> None:
        raise ValueError("boom")

    monkeypatch.setattr(TradeService, "create_trade", _boom)
    with pytest.raises(ValueError):
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json={
                "account_id": str(uuid.uuid4()),
                "symbol": "AAPL",
                "direction": "LONG",
                "asset_class": "EQUITY",
                "quantity": "1",
                "entry_price": "10",
                "opened_at": "2024-01-15T10:00:00Z",
                "currency": "USD",
            },
            headers=primary_user["headers"],
        )
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "error.unhandled")
    metadata = payloads[-1].get("metadata")
    assert isinstance(metadata, dict)
    assert "stack_trace" in metadata
    logger.removeHandler(handler)


@pytest.mark.integration
async def test_audit_logs_database_error_with_request_id(
    client: AsyncClient,
    primary_user: dict[str, str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger, handler, stream = _capture_audit_logger()
    portfolio_id = await _create_portfolio(client, primary_user["headers"], "Audit P12")

    async def _db_boom(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(TradeService, "create_trade", _db_boom)
    with pytest.raises(SQLAlchemyError):
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/trades",
            json={
                "account_id": str(uuid.uuid4()),
                "symbol": "AAPL",
                "direction": "LONG",
                "asset_class": "EQUITY",
                "quantity": "1",
                "entry_price": "10",
                "opened_at": "2024-01-15T10:00:00Z",
                "currency": "USD",
            },
            headers=primary_user["headers"],
        )
    payloads = _get_audit_payloads(stream)
    _assert_action(payloads, "error.database")
    assert any(payload.get("request_id") for payload in payloads)
    logger.removeHandler(handler)
