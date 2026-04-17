## ADDED Requirements

### Requirement: AGENTS.md documents audit logging policy

The AGENTS.md file SHALL include a dedicated section documenting the audit logging policy and requirements for all code changes. This section SHALL instruct backend-engineer and frontend-engineer agents to automatically add audit logging for new features.

#### Scenario: Backend engineer reads audit policy
- **WHEN** backend-engineer agent implements a new API endpoint
- **THEN** agent reads AGENTS.md audit policy and adds appropriate audit logging to route handler or uses existing middleware

#### Scenario: Frontend engineer reads audit policy
- **WHEN** frontend-engineer agent adds new UI feature that calls backend API
- **THEN** agent verifies backend endpoint has audit logging (via middleware) and documents expected audit events

---

### Requirement: Audit policy specifies automatic coverage

The AGENTS.md audit policy SHALL specify that all new API endpoints (POST, PUT, PATCH, DELETE) are automatically covered by audit middleware. The policy SHALL clarify when manual audit events are needed (complex operations, bulk actions, special business logic).

#### Scenario: Standard CRUD endpoint uses automatic logging
- **WHEN** backend-engineer creates `POST /api/v1/tags` endpoint
- **THEN** agent documents that middleware automatically logs `tag.created` action (no manual logging needed)

#### Scenario: Complex operation requires manual audit event
- **WHEN** backend-engineer creates `POST /api/v1/trades/bulk-delete` endpoint
- **THEN** agent adds manual audit event with `metadata={"deleted_count": N}` in route handler

---

### Requirement: Audit policy defines sensitive data exclusion

The AGENTS.md audit policy SHALL list fields that MUST NOT be logged: P&L, commissions, prices, quantities, strategy notes, playbook names, tag names, passwords, tokens, API secrets. Agents SHALL verify new code does not log these fields.

#### Scenario: Backend engineer excludes P&L from logs
- **WHEN** backend-engineer implements trade calculation endpoint
- **THEN** agent verifies audit event logs `trade_id` but NOT `realized_pnl` or `unrealized_pnl`

#### Scenario: Backend engineer excludes passwords from auth logs
- **WHEN** backend-engineer modifies password reset endpoint
- **THEN** agent verifies audit event logs `user_id` and `email_hash` but NOT plaintext password

---

### Requirement: Audit policy requires error logging

The AGENTS.md audit policy SHALL require that all new code includes appropriate error handling with structured logging for exceptions. Agents SHALL add try/except blocks with logger.error() calls for critical operations.

#### Scenario: Backend engineer adds error logging to import function
- **WHEN** backend-engineer implements new import parser
- **THEN** agent adds try/except with `logger.error("Import failed", extra={"user_id": ..., "file_name": ..., "error": str(e)})` 

#### Scenario: Backend engineer logs validation errors
- **WHEN** backend-engineer adds custom validation logic
- **THEN** agent adds logging for validation failures with field names and error messages (but not sensitive field values)

---

### Requirement: Audit policy includes code review checklist

The AGENTS.md audit policy SHALL include a checklist for code-reviewer agent to verify audit logging compliance. The checklist SHALL cover: endpoint coverage, sensitive data exclusion, error logging, action naming conventions.

#### Scenario: Code reviewer verifies new endpoint has audit logging
- **WHEN** code-reviewer agent reviews PR with new `POST /api/v1/screenshots` endpoint
- **THEN** agent verifies middleware will log `screenshot.created` action (automatic coverage confirmed)

#### Scenario: Code reviewer catches sensitive data in logs
- **WHEN** code-reviewer agent reviews PR that logs `commission` field
- **THEN** agent flags violation of audit policy and requests removal

#### Scenario: Code reviewer verifies error handling
- **WHEN** code-reviewer agent reviews PR with new database operation
- **THEN** agent verifies try/except block exists with appropriate `logger.error()` call

---

### Requirement: Audit policy documents action naming conventions

The AGENTS.md audit policy SHALL document the action naming convention: `<resource>.<verb>` format (e.g., `trade.created`, `account.deleted`, `import.completed`). The policy SHALL list standard verbs: created, updated, deleted, merged, split, restored, completed, failed.

#### Scenario: Backend engineer follows naming convention
- **WHEN** backend-engineer implements execution restore endpoint
- **THEN** agent names audit action `execution.restored` (not `restore_execution` or `ExecutionRestored`)

#### Scenario: Backend engineer uses correct verb for bulk operation
- **WHEN** backend-engineer implements batch import completion handler
- **THEN** agent names audit action `import.completed` with `metadata={"records_imported": N}`

---

### Requirement: Audit policy links to implementation examples

The AGENTS.md audit policy SHALL link to example code showing correct audit logging implementation. Examples SHALL cover: standard CRUD (automatic middleware), manual audit events (complex operations), error logging, sensitive data filtering.

#### Scenario: Backend engineer references middleware example
- **WHEN** backend-engineer creates new CRUD endpoint
- **THEN** agent reads linked example showing that no manual logging is needed (middleware handles it)

#### Scenario: Backend engineer references manual audit example
- **WHEN** backend-engineer implements trade merge operation
- **THEN** agent reads linked example showing how to log with `metadata={"source_trade_ids": [...]}`
