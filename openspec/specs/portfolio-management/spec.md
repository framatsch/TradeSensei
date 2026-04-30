## ADDED Requirements

### Requirement: Portfolio creation
The system SHALL allow an authenticated user to create a portfolio by providing
a `name`, `base_currency` (ISO 4217, 3-letter), and an optional `color_hex`
(`#RRGGBB`). The portfolio MUST be owned by the requesting user. Portfolio
`name` MUST be unique per user.

#### Scenario: Create a valid portfolio
- **WHEN** a user submits `POST /api/v1/portfolios` with valid fields
- **THEN** the system SHALL persist the portfolio and return HTTP 201 with the
  created portfolio resource

#### Scenario: Duplicate name rejected
- **WHEN** a user submits `POST /api/v1/portfolios` with a name that already
  exists for that user
- **THEN** the system SHALL return HTTP 409 Conflict

#### Scenario: Invalid color_hex rejected
- **WHEN** a user submits `POST /api/v1/portfolios` with `color_hex` not
  matching `^#[0-9A-Fa-f]{6}$`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

#### Scenario: Invalid base_currency rejected
- **WHEN** a user submits `POST /api/v1/portfolios` with a `base_currency`
  value not in `['USD', 'EUR', 'GBP', 'CHF', 'JPY', 'AUD', 'CAD']`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

---

### Requirement: Portfolio listing
The system SHALL allow an authenticated user to list all portfolios they own
via `GET /api/v1/portfolios`. The response MUST include each portfolio's
`id`, `name`, `base_currency`, `is_paper`, `color_hex`, `created_at`, and
`updated_at`. Results MUST be ordered by `created_at` ascending.

#### Scenario: List portfolios for a user with portfolios
- **WHEN** a user calls `GET /api/v1/portfolios`
- **THEN** the system SHALL return only portfolios owned by that user

#### Scenario: List portfolios for a new user
- **WHEN** a user with no portfolios calls `GET /api/v1/portfolios`
- **THEN** the system SHALL return an empty list with HTTP 200

---

### Requirement: Portfolio retrieval
The system SHALL allow an authenticated user to retrieve a single portfolio by
its `id` via `GET /api/v1/portfolios/{portfolio_id}`.

#### Scenario: Own portfolio retrieved
- **WHEN** a user calls `GET /api/v1/portfolios/{portfolio_id}` for a portfolio
  they own
- **THEN** the system SHALL return the portfolio resource with HTTP 200

#### Scenario: Other user's portfolio not accessible
- **WHEN** a user calls `GET /api/v1/portfolios/{portfolio_id}` for a portfolio
  owned by another user
- **THEN** the system SHALL return HTTP 404

---

### Requirement: Portfolio update
The system SHALL allow an authenticated user to update a portfolio's `name`
and `color_hex` via `PATCH /api/v1/portfolios/{portfolio_id}`.
The system SHALL allow updating `base_currency` only when the portfolio has
no associated trades.

#### Scenario: Rename a portfolio
- **WHEN** a user patches `name` to a new unique value
- **THEN** the system SHALL persist the change and return the updated resource

#### Scenario: Change base_currency with no trades
- **WHEN** a user patches `base_currency` to a value in the allowlist on a portfolio with zero trades
- **THEN** the system SHALL persist the new currency

#### Scenario: Change base_currency with existing trades rejected
- **WHEN** a user patches `base_currency` on a portfolio that has at least
  one trade (via its accounts)
- **THEN** the system SHALL return HTTP 422 with a descriptive error message

#### Scenario: Rename to duplicate name rejected
- **WHEN** a user patches `name` to a value that matches an existing portfolio
  name for that user
- **THEN** the system SHALL return HTTP 409 Conflict

#### Scenario: base_currency outside allowlist rejected on update
- **WHEN** a user patches `base_currency` with a value not in `['USD', 'EUR', 'GBP', 'CHF', 'JPY', 'AUD', 'CAD']`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

---

### Requirement: Portfolio deletion
The system SHALL allow an authenticated user to delete a portfolio via
`DELETE /api/v1/portfolios/{portfolio_id}` only if the portfolio has no
linked accounts. There is no `force` or cascade option — accounts must be
removed first.

#### Scenario: Delete portfolio with no accounts
- **WHEN** a user calls `DELETE /api/v1/portfolios/{portfolio_id}` on a
  portfolio with zero linked accounts
- **THEN** the system SHALL delete the portfolio and return HTTP 204

#### Scenario: Delete portfolio with linked accounts rejected
- **WHEN** a user calls `DELETE /api/v1/portfolios/{portfolio_id}` on a
  portfolio that has one or more linked accounts
- **THEN** the system SHALL return HTTP 409 Conflict with a message stating
  the number of blocking accounts (e.g. "Portfolio has 3 linked accounts")

#### Scenario: No cascade or force option exists
- **WHEN** a user calls `DELETE /api/v1/portfolios/{portfolio_id}?force=true`
- **THEN** the system SHALL return HTTP 400 Bad Request (unknown query param)
  or ignore the param and still enforce the 409 if accounts exist

---

### Requirement: Default portfolio created on migration
The system SHALL ensure that every existing user has exactly one portfolio
(named `"Default Portfolio"`) after the Alembic migration runs, and that all
of that user's existing accounts are linked to it.

#### Scenario: Migration assigns all accounts to default portfolio
- **WHEN** the migration completes
- **THEN** every `Account` row SHALL have a non-null `portfolio_id` pointing
  to a portfolio owned by the same user

#### Scenario: No orphaned accounts post-migration
- **WHEN** the migration completes
- **THEN** no `Account` row SHALL have `portfolio_id IS NULL`
