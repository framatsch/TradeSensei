## ADDED Requirements

### Requirement: User can manage portfolios from Settings
The Settings Hub SHALL provide a **Portfolios** tab that allows an authenticated user to create,
edit, and delete their portfolios without leaving the settings context.

#### Scenario: Create a portfolio
- **WHEN** the user fills in a portfolio name, selects a base currency, toggles live/paper, optionally picks a colour, and submits the form
- **THEN** the system calls `POST /api/v1/portfolios` and the new portfolio appears in the list

#### Scenario: Create portfolio — duplicate name rejected
- **WHEN** the user submits a portfolio name that already exists for their account
- **THEN** the form shows an inline error "A portfolio with this name already exists" and does not navigate away

#### Scenario: Edit a portfolio name and colour
- **WHEN** the user clicks Edit on a portfolio, changes the name or colour, and saves
- **THEN** the system calls `PATCH /api/v1/portfolios/{id}` with the updated fields

#### Scenario: Base currency is locked after first trade
- **WHEN** the portfolio has at least one trade (backend `has_trades` returns true)
- **THEN** the base currency field is disabled and a tooltip reads "Currency cannot be changed once trades exist"

#### Scenario: Base currency is editable for empty portfolio
- **WHEN** the portfolio has no trades
- **THEN** the base currency select is enabled and all supported currencies are listed

#### Scenario: Delete portfolio — blocked while accounts exist
- **WHEN** the user clicks Delete on a portfolio that has accounts linked to it
- **THEN** the system returns HTTP 409 and the UI shows "Remove all accounts before deleting this portfolio"

#### Scenario: Delete portfolio — allowed when empty
- **WHEN** the portfolio has no linked accounts and the user confirms deletion
- **THEN** the system calls `DELETE /api/v1/portfolios/{id}` and the portfolio is removed from the list

### Requirement: Danger Zone — portfolio data wipe
The Portfolios tab SHALL include a Danger Zone section that allows a user to wipe all trade
data from a portfolio while preserving broker credentials, suppressed raw transactions, and
portfolio configuration.

#### Scenario: Wipe confirmed — user types portfolio name
- **WHEN** the user opens the "Wipe Portfolio Data" dialog, types the exact portfolio name in the confirmation field, and clicks Confirm
- **THEN** the system calls `POST /api/v1/imports/{account_id}/fresh-start` for each account in the portfolio sequentially (no file upload required — only the `acknowledged=true` form field)
- **AND** each account shows a success or error indicator when its request completes

#### Scenario: Wipe aborted — name mismatch
- **WHEN** the user types a portfolio name that does not match exactly (case-sensitive)
- **THEN** the Confirm button remains disabled

#### Scenario: Wipe partial failure
- **WHEN** one or more accounts fail during the sequential wipe
- **THEN** the UI shows a summary: "{n} of {total} accounts wiped successfully; {m} failed" with per-account error messages

#### Scenario: Wipe dialog closed mid-flow
- **WHEN** the user closes the dialog after some but not all accounts have been wiped
- **THEN** the already-wiped accounts remain empty; no automatic rollback is performed; the UI reflects the partial state on next open
