## ADDED Requirements

### Requirement: Service creates structured audit events

The audit event service SHALL create structured audit events in JSON format with standardized fields: `timestamp`, `level`, `logger`, `action`, `user_id`, `email_hash`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `request_id`, `status_code`, `method`, `path`.

#### Scenario: Audit event for trade creation
- **WHEN** service receives audit data for `trade.created` action
- **THEN** service creates JSON log with `action=trade.created`, `user_id=<uuid>`, `resource_type=trade`, `resource_id=123`, `timestamp=<ISO8601>`

#### Scenario: Audit event for account deletion
- **WHEN** service receives audit data for `account.deleted` action
- **THEN** service creates JSON log with `action=account.deleted`, `resource_type=account`, `resource_id=5`, `status_code=204`

---

### Requirement: Service hashes email addresses with SHA256

The audit event service SHALL hash user email addresses using SHA256 before logging. The service SHALL convert email to lowercase before hashing to ensure consistent hashes for the same email (case-insensitive).

#### Scenario: Email hashed consistently
- **WHEN** service logs event for user with email `test@example.com`
- **THEN** `email_hash` field contains SHA256 hex digest `973dfe463ec85785f5f95af5ba3906ee`

#### Scenario: Email case normalization
- **WHEN** service logs event for user with email `Test@Example.COM`
- **THEN** `email_hash` is identical to hash for `test@example.com` (lowercase normalization applied)

---

### Requirement: Service excludes sensitive data from logs

The audit event service SHALL NOT log sensitive financial data (P&L, commissions, prices, quantities) or user content (strategy notes, playbook names, tag names, passwords, tokens). The service SHALL only log metadata: action, resource IDs, user context, and timestamps.

#### Scenario: Trade creation logs metadata only
- **WHEN** service logs `trade.created` for trade with `realized_pnl=1234.56`, `symbol=AAPL`
- **THEN** audit log contains `trade_id` but NOT `realized_pnl` or `symbol`

#### Scenario: Password reset does not log password
- **WHEN** service logs `auth.password_reset` action
- **THEN** audit log contains `user_id` but NOT new password value

#### Scenario: Login does not log plaintext password
- **WHEN** service logs `auth.login` from form data
- **THEN** audit log contains `email_hash` but NOT plaintext password from form

---

### Requirement: Service generates RFC4122 UUID request IDs

The audit event service SHALL generate a unique request ID (UUID v4) for each HTTP request to enable correlation across logs. The request ID SHALL be included in every audit log entry for that request.

#### Scenario: Request ID correlates multiple log entries
- **WHEN** a single request triggers multiple audit events (e.g., import creates 10 trades)
- **THEN** all audit log entries share the same `request_id`

#### Scenario: Unique request IDs for concurrent requests
- **WHEN** two users simultaneously create trades
- **THEN** each request has a different `request_id`

---

### Requirement: Service outputs logs to stdout in JSON format

The audit event service SHALL write structured JSON logs to stdout (not stderr) for Loki ingestion. Each log entry SHALL be a single-line JSON object.

#### Scenario: JSON log written to stdout
- **WHEN** service creates audit event
- **THEN** log appears as single-line JSON in stdout stream

#### Scenario: Log contains all required fields
- **WHEN** service logs `trade.updated` event
- **THEN** JSON output contains keys: `timestamp`, `level`, `logger`, `action`, `user_id`, `email_hash`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `request_id`, `status_code`, `method`, `path`

---

### Requirement: Service formats timestamps as ISO 8601 with microseconds

The audit event service SHALL format all timestamps as ISO 8601 with UTC timezone and microsecond precision (e.g., `2026-04-19T10:30:00.123456Z`).

#### Scenario: Timestamp includes microseconds
- **WHEN** service creates audit event at `2026-04-19 10:30:00.123456 UTC`
- **THEN** `timestamp` field is `2026-04-19T10:30:00.123456Z`

#### Scenario: Timestamp is always UTC
- **WHEN** service runs in timezone `Europe/Berlin` (UTC+1)
- **THEN** `timestamp` is converted to UTC before logging (no timezone offset)

---

### Requirement: Service supports optional metadata fields

The audit event service SHALL support optional metadata fields for complex operations that don't fit the standard resource_type/resource_id pattern (e.g., bulk operations, merges). Optional fields: `parent_resource_id`, `parent_resource_type`, `metadata` (JSON object).

#### Scenario: Bulk import logs record count in metadata
- **WHEN** service logs `import.completed` with 150 records imported
- **THEN** audit log contains `metadata={"records_imported": 150}`

#### Scenario: Trade merge logs both trade IDs
- **WHEN** service logs `trade.merged` for trades 123 and 456
- **THEN** audit log contains `metadata={"source_trade_ids": [123, 456]}`

---

### Requirement: Service sets log level to INFO for audit events

The audit event service SHALL set log level to `INFO` for all audit events (not DEBUG or WARNING). This ensures audit logs are always captured in production (where `LOG_LEVEL=INFO` or higher).

#### Scenario: Audit event logged at INFO level
- **WHEN** service creates any audit event
- **THEN** JSON log has `level=INFO`

---

### Requirement: Service handles missing user context gracefully

The audit event service SHALL handle cases where user context is unavailable (e.g., unauthenticated requests like login) by setting `user_id=null` and extracting `email_hash` from request data if possible.

#### Scenario: Login request logs email hash without user_id
- **WHEN** service logs `auth.login` for unauthenticated request with email `test@example.com`
- **THEN** audit log has `user_id=null`, `email_hash=<sha256(test@example.com)>`

#### Scenario: Failed login logs email hash from form data
- **WHEN** service logs `auth.failed` for failed login attempt with email `bad@example.com`
- **THEN** audit log has `user_id=null`, `email_hash=<sha256(bad@example.com)>`
