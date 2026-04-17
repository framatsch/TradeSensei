## ADDED Requirements

### Requirement: Cross-user resource access returns 404

The system SHALL return `404 Not Found` — never `403 Forbidden` — when an
authenticated user requests a resource belonging to a different user. This
prevents existence leakage: a 403 would confirm the resource exists; a 404
does not.

Applies to every user-scoped resource: trades, executions, accounts,
playbooks, tags, notes, screenshots, broker raw transactions.

#### Scenario: GET another user's trade returns 404
- **WHEN** User A calls `GET /api/v1/trades/{id}` where `id` belongs to User B
- **THEN** response is `404 Not Found`
- **AND** response body does not reveal that the trade exists

#### Scenario: PATCH another user's trade returns 404
- **WHEN** User A calls `PATCH /api/v1/trades/{id}` where `id` belongs to User B
- **THEN** response is `404 Not Found`
- **AND** the trade is not modified

#### Scenario: DELETE another user's trade returns 404
- **WHEN** User A calls `DELETE /api/v1/trades/{id}` where `id` belongs to User B
- **THEN** response is `404 Not Found`
- **AND** the trade is not deleted

#### Scenario: List endpoints return only own resources
- **WHEN** User A calls `GET /api/v1/trades`
- **THEN** the response contains only trades where `user_id = User A`
- **AND** no trade belonging to User B appears regardless of filters or cursor

#### Scenario: Same rule applies to all resource types
- **WHEN** User A attempts GET/PATCH/DELETE on any resource owned by User B
  (execution, account, playbook, tag, note, screenshot, broker transaction)
- **THEN** response is `404 Not Found`
- **AND** no data belonging to User B is returned or mutated

---

### Requirement: Repository methods structurally require `user_id`

Every repository method that retrieves or mutates a single resource by ID
SHALL declare `user_id: int` as a required parameter with no default value.
The SQL WHERE clause SHALL always include `AND <table>.user_id = :uid`.

#### Scenario: Missing user_id is a compile-time error
- **WHEN** a developer calls `trade_repo.get_by_id(trade_id)` without `user_id`
- **THEN** Python raises `TypeError: missing required argument 'user_id'`
- **AND** no database query is executed

#### Scenario: Repository returns None for wrong user
- **WHEN** `trade_repo.get_by_id(trade_id=X, user_id=user_b_id)` is called
- **AND** trade X belongs to `user_a`
- **THEN** repository returns `None`
- **AND** the executed SQL includes `AND user_id = :uid`

---

### Requirement: PostgreSQL Row-Level Security isolates data at DB layer

All user-scoped tables SHALL have RLS enabled. The policy restricts rows to
`user_id = current_setting('app.current_user_id')`. Even if application code
omits a `user_id` filter, the database returns only the current user's rows.

#### Scenario: Raw SQL without user filter is blocked by RLS
- **WHEN** application code executes `SELECT * FROM trades` without WHERE
- **AND** `app.current_user_id` is set to User A's ID
- **THEN** only User A's trades are returned

#### Scenario: RLS context is scoped to the transaction
- **WHEN** an authenticated request begins
- **THEN** `SET LOCAL app.current_user_id = :uid` is executed at transaction start
- **AND** the setting is automatically cleared when the connection returns to pool

#### Scenario: Migrations bypass RLS
- **WHEN** an Alembic migration runs
- **THEN** it uses a role with `BYPASSRLS` privilege
- **AND** can read and write all rows

#### Scenario: Shared reference tables have no RLS
- **WHEN** application code queries `fx_rates` or `corporate_actions`
- **THEN** RLS is not applied (these tables have no `user_id` column)

---

### Requirement: User-facing resource IDs are UUIDs

All tables addressed directly via the API SHALL use `UUID DEFAULT gen_random_uuid()`
as primary key. Sequential integer IDs SHALL NOT appear in any API response
for user-facing resources.

#### Scenario: Trade IDs are non-guessable UUIDs
- **WHEN** `GET /api/v1/trades` is called
- **THEN** each trade's `id` is a UUID (e.g. `"550e8400-e29b-41d4-a716-446655440000"`)
- **AND** the ID is not a sequential integer

#### Scenario: Integer IDs return 422 or 404 — not trade data
- **WHEN** `GET /api/v1/trades/1` is called (integer, not UUID)
- **THEN** response is `422 Unprocessable Entity` (invalid UUID format) or `404 Not Found`
- **AND** no trade data is returned

---

### Requirement: Every resource endpoint has an ownership test

The test suite SHALL include an ownership test for each user-scoped resource.
Each test SHALL use an `other_user` fixture and assert `status_code == 404`
for GET, PATCH, and DELETE against a resource belonging to that other user.

#### Scenario: Ownership tests exist and pass for all resources
- **WHEN** the CI test suite runs
- **THEN** ownership tests exist for: Trade, Execution, Account, Playbook,
  Tag, Note, Screenshot, BrokerRawTransaction
- **AND** all GET/PATCH/DELETE ownership tests assert `status_code == 404`
- **AND** all tests are included in the CI pipeline and must pass before merge
