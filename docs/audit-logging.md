# Audit Logging

## Overview

Audit logs capture security-relevant events and API actions for troubleshooting and
compliance. Logs are emitted as structured JSON to stdout by the audit middleware
and include user context, request metadata, and action names.

## Fields

Each audit log entry includes the following fields:

- `timestamp`: ISO 8601 UTC timestamp with microseconds (e.g., `2026-04-19T13:58:33.598476Z`).
- `level`: Log level, always `INFO` for audit events.
- `logger`: Logger name, always `audit`.
- `action`: Action name in `<resource>.<verb>` format.
- `user_id`: Authenticated user UUID (null if unauthenticated).
- `email_hash`: SHA256 hash of normalized email (lowercase, trimmed).
- `resource_type`: Resource name (e.g., `trade`, `account`).
- `resource_id`: Resource identifier (string UUID or integer), optional.
- `parent_resource_type`: Parent resource for nested paths, optional.
- `parent_resource_id`: Parent resource identifier, optional.
- `ip_address`: Client IP from the direct connection.
- `forwarded_for`: IP from `X-Forwarded-For` when proxied.
- `user_agent`: User agent string.
- `request_id`: UUID v4 correlation identifier.
- `status_code`: HTTP status code.
- `method`: HTTP method.
- `path`: Request path.
- `metadata`: Optional safe metadata (counts, flags, error summaries).

## Error logging patterns

Error responses use `error.<category>` actions:

- `error.not_found` (404)
- `error.forbidden` (403)
- `error.validation` (422)
- `error.internal` (500)
- `error.database` (SQLAlchemy errors)
- `error.unhandled` (uncaught exceptions)

When errors occur, the audit middleware logs:

- `exception_type`
- `exception_message`
- `stack_trace`

Avoid including sensitive values in the metadata payload.

## Automatic vs manual audit events

Automatic audit coverage:

- POST/PUT/PATCH/DELETE endpoints are logged by middleware.
- GET endpoints are logged only when `LOG_LEVEL=DEBUG`.

Manual audit events are required for complex operations (bulk actions, imports,
merges, restores) when you need to include metadata such as counts or IDs.

Example manual event (service-layer):

```python
audit = AuditEventService()
audit.create_audit_event(
    action="import.completed",
    user_id=user_id,
    email=email,
    resource_type="import",
    resource_id=import_id,
    ip_address=ip_address,
    user_agent=user_agent,
    request_id=request_id,
    status_code=200,
    method="POST",
    path="/api/v1/imports/upload",
    metadata={"records_imported": count},
)
```

## Sensitive data exclusion

Never log P&L, commissions, prices, quantities, strategy notes, playbook names,
tag names, passwords, tokens, or API secrets. Only log safe identifiers and
hashed emails.
