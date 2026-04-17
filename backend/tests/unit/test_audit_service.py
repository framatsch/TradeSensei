"""Unit tests for AuditEventService utilities."""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.audit_service import (
    AuditEventService,
    format_timestamp,
    generate_request_id,
    hash_email,
)


def test_hash_email_normalizes_case() -> None:
    assert hash_email("Test@Example.COM") == hash_email("test@example.com")


def test_hash_email_known_value() -> None:
    assert (
        hash_email("test@example.com")
        == "973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"
    )


def test_format_timestamp_utc_microseconds() -> None:
    value = datetime(2026, 4, 19, 10, 30, 0, 123456, tzinfo=UTC)
    assert format_timestamp(value) == "2026-04-19T10:30:00.123456Z"


def test_generate_request_id_is_uuid() -> None:
    request_id = generate_request_id()
    assert len(request_id) == 36


def test_sensitive_filtering_in_metadata() -> None:
    service = AuditEventService()
    payload = service.create_audit_event(
        action="trade.created",
        user_id=None,
        email=None,
        resource_type="trade",
        resource_id="123",
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id="req-1",
        status_code=201,
        method="POST",
        path="/api/v1/trades",
        metadata={"pnl": "100", "notes": "secret", "ok": "keep"},
    )
    metadata = payload.get("metadata")
    assert metadata == {"ok": "keep"}
