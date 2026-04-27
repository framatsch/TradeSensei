## ADDED Requirements

### Requirement: Direction is editable in the execution leg inline editor
The system SHALL allow users to change the `direction` (LONG / SHORT) of an execution leg via a two-state toggle in the inline edit form. Submitting the change SHALL send a `PATCH /api/v1/executions/{id}` request with `{"direction": "<new_value>"}` and re-aggregate the parent trade.

#### Scenario: User switches direction from LONG to SHORT
- **WHEN** the user enters edit mode on an execution leg and clicks the SHORT toggle button
- **THEN** the SHORT button appears selected (primary style) and the LONG button appears unselected

#### Scenario: Direction change is persisted on save
- **WHEN** the user selects a different direction and clicks the save checkmark
- **THEN** the API receives `PATCH /executions/{id}` with `direction` set to the new value
- **THEN** the execution row updates to reflect the new direction badge

#### Scenario: Direction change is discarded on cancel
- **WHEN** the user selects a different direction and clicks the cancel (X) button
- **THEN** the direction reverts to the original value and no API call is made

---

### Requirement: Execution timestamp is editable in the inline editor
The system SHALL allow users to edit the `executed_at` field of an execution leg via a datetime picker in the inline edit form. The stored value SHALL be UTC ISO-8601; the picker SHALL display local time but convert to UTC before sending to the API.

#### Scenario: Datetime picker pre-fills with current executed_at
- **WHEN** the user enters edit mode on an execution leg
- **THEN** the datetime input is pre-filled with the execution's `executed_at` converted to the browser's local time

#### Scenario: Timestamp change is sent as UTC ISO-8601
- **WHEN** the user modifies the datetime input and saves
- **THEN** the API receives `PATCH /executions/{id}` with `executed_at` as a UTC ISO-8601 string (ending in `Z` or with `+00:00` offset)

#### Scenario: Empty timestamp input blocks save
- **WHEN** the user clears the datetime input and attempts to save
- **THEN** the save button is disabled (or the field is highlighted as required) and no API call is made

---

### Requirement: P&L is editable in the inline editor
The system SHALL allow users to set or clear the `pnl` field of an execution leg via a numeric input in the inline edit form. An empty input SHALL send `pnl: null` to the API.

#### Scenario: P&L field pre-fills from current value
- **WHEN** the user enters edit mode on an execution leg that has a non-null `pnl`
- **THEN** the P&L input is pre-filled with the existing value

#### Scenario: P&L field is empty for legs with null pnl
- **WHEN** the user enters edit mode on an execution leg with `pnl = null`
- **THEN** the P&L input is empty (not "0")

#### Scenario: Clearing the P&L sends null to the API
- **WHEN** the user clears the P&L input and saves
- **THEN** the API receives `PATCH /executions/{id}` with `pnl: null`

---

### Requirement: ExecutionLegsTable shows a retry action on API error
The system SHALL display a "Retry" button in the `ExecutionLegsTable` error state that calls `refetch()` on the React Query execution list. A short diagnostic hint message SHALL be shown alongside (e.g. "Could not reach the server. Check that the backend is running.").

#### Scenario: Error state shows retry button
- **WHEN** the `GET /trades/{id}/executions` call fails (network error or 5xx)
- **THEN** the table body shows the error message and a "Retry" button instead of static text

#### Scenario: Retry button refetches executions
- **WHEN** the user clicks "Retry" and the backend is now reachable
- **THEN** the execution list loads and the table renders normally

---

### Requirement: Aggregated trade fields are not settable via TradeUpdate
The system SHALL remove `pnl`, `net_pnl`, `commission`, `quantity`, `entry_price`, `exit_price`, `opened_at`, and `closed_at` from the `TradeUpdate` request schema. These fields are denormalized caches of execution-leg data and SHALL only be updated via re-aggregation triggered by leg mutations. The `TradeRead` response schema SHALL continue to include all fields as read-only.

#### Scenario: Sending aggregated fields in TradeUpdate is ignored or rejected
- **WHEN** a client sends `PATCH /api/v1/trades/{id}` with `{"pnl": 500}`
- **THEN** the API returns a 422 validation error (field not accepted) or silently ignores the field

#### Scenario: Trade edit form shows aggregated fields as read-only
- **WHEN** a user opens the trade edit form
- **THEN** `entry_price`, `exit_price`, `pnl`, `commission`, `quantity`, `opened_at`, `closed_at` are displayed as read-only text (not editable inputs)

#### Scenario: Changing a leg updates the cached trade fields
- **WHEN** a user edits the `price` of an entry execution leg and saves
- **THEN** `trade.entry_price` (VWAP) is updated by re-aggregation without any direct trade edit

---

### Requirement: Playwright tests cover all execution leg editor interactions
The system SHALL have Playwright E2E tests that verify the full inline editor workflow for execution legs, the retry error state, the read-only aggregated fields in the trade edit form, and the backend startup migration log. Tests use `seedState.editExecutionTestTradeId` — a dedicated seeded trade with two legs — to avoid interference with read-only tests that use `executionTradeId`.

#### Scenario: TC-094 — Edit mode shows all six editable fields
- **WHEN** a user navigates to the edit-execution test trade and clicks the overflow menu → Edit on the first leg
- **THEN** inputs for direction toggle, datetime, price, quantity, commission, and pnl are all visible in the table row

#### Scenario: TC-095 — Direction change persists after save
- **WHEN** a user enters edit mode on a LONG leg, clicks the SHORT toggle, and saves
- **THEN** the row's Side badge changes to SHORT and the edit inputs close

#### Scenario: TC-096 — Timestamp change persists after save
- **WHEN** a user enters edit mode, changes the datetime input to a new value, and saves
- **THEN** the Date cell in the row updates to reflect the new timestamp

#### Scenario: TC-097 — P&L change updates Execution Summary
- **WHEN** a user enters edit mode on a leg, sets pnl to a non-null value, and saves
- **THEN** the ExecutionSummaryCard's P&L figure reflects the new aggregated value

#### Scenario: TC-098 — Cancel reverts all field edits
- **WHEN** a user enters edit mode, changes direction and price, then clicks Cancel
- **THEN** the row displays the original direction badge and price, and no API call is made

#### Scenario: TC-099 — Error state shows Retry button
- **WHEN** the execution legs API returns an error (simulated via network intercept / route abort)
- **THEN** the ExecutionLegsTable body shows a Retry button and a hint message instead of "Failed to load executions."
- **WHEN** the user clicks Retry and the route is restored
- **THEN** the table loads the execution rows successfully

#### Scenario: TC-100 — Trade edit form does not show inputs for aggregated fields
- **WHEN** a user opens the trade edit form (pencil icon) for any trade
- **THEN** there are no `<input>` elements for `pnl`, `net_pnl`, `entry_price`, `exit_price`, `quantity`, `commission`, `opened_at`, or `closed_at`
- **THEN** the values for these fields appear as read-only text

---

### Requirement: ExecutionSummaryCard shows multiplier and notional value for non-equity instruments
The system SHALL display the contract `multiplier` and the computed notional value (`entry_price × quantity × multiplier`) in the `ExecutionSummaryCard` when the trade's multiplier is greater than 1. For equity trades (multiplier = 1) the card SHALL remain unchanged. The raw VWAP price labels SHALL be renamed to clarify they are per-unit prices.

#### Scenario: Option trade shows multiplier and notional entry
- **WHEN** a user opens the trade detail page for an OPTION trade with `multiplier = 100`, `entry_price = 5.00`, `quantity = 1`
- **THEN** the ExecutionSummaryCard shows a `Multiplier` tile with value `100×`
- **THEN** a `Notional Entry` tile shows `$500.00` (= 5.00 × 1 × 100)
- **THEN** the entry price label reads `Entry Price (per unit)` instead of `VWAP Entry`

#### Scenario: Option trade with closed position shows notional exit
- **WHEN** an OPTION trade has `exit_price = 3.00`, `quantity = 1`, `multiplier = 100`
- **THEN** a `Notional Exit` tile shows `$300.00` (= 3.00 × 1 × 100)

#### Scenario: TC-101 — Equity trade shows no multiplier tile
- **WHEN** a user opens the trade detail page for an EQUITY trade (multiplier = 1)
- **THEN** no `Multiplier` or `Notional Entry` tile is present in the ExecutionSummaryCard

#### Scenario: TC-102 — Option trade legs table shows multiplier column
- **WHEN** a user opens the trade detail page for an OPTION trade
- **THEN** the execution legs table has a `Mult.` column showing `100` for option legs
- **THEN** a notional value is shown per leg

---

### Requirement: Backend startup logs applied migration revision
The system SHALL log the applied Alembic revision head at INFO level after running startup migrations. The log entry SHALL include the revision ID and the label "(head)" if the DB is at the latest revision in the migration chain.

#### Scenario: Successful startup with all migrations applied
- **WHEN** the backend starts and all migrations are already at head
- **THEN** the startup log contains a line like `Database at revision 3bbca280b48e (head) — no pending migrations`

#### Scenario: Pending migrations applied on startup
- **WHEN** the backend starts and one or more migrations are pending
- **THEN** the startup log contains the revision before and after the upgrade, e.g. `Upgraded database from 4e095dd6e4c5 to 3bbca280b48e (head)`
