## ADDED Requirements

### Requirement: Trade row selection via checkboxes
The trade table SHALL display a checkbox column as the first column. Each row SHALL have a checkbox to select/deselect that trade. The column header SHALL contain a "select all" checkbox with three states: unchecked (none selected), checked (all on current page selected), indeterminate (some selected).

#### Scenario: Select individual trade
- **WHEN** user checks the checkbox on a trade row
- **THEN** that trade is added to the selected set and its row is visually highlighted

#### Scenario: Select all on current page
- **WHEN** user checks the header checkbox
- **THEN** all trades on the current page are selected

#### Scenario: Deselect all
- **WHEN** user unchecks the header checkbox while all are selected
- **THEN** all trades are deselected

#### Scenario: Partial selection shows indeterminate state
- **WHEN** some but not all trades on the page are selected
- **THEN** the header checkbox displays in indeterminate state

#### Scenario: Selection is scoped to current page only
- **WHEN** user navigates to a different page
- **THEN** the selection is cleared

### Requirement: Bulk action toolbar appears on selection
When at least one trade is selected, a bulk action toolbar SHALL appear above the trade table. The toolbar SHALL display: the count of selected trades, a "Assign Tags" button, a "Remove Tags" button, a "Assign Playbook" button, and a "Delete" button. When no trades are selected, the toolbar SHALL be hidden.

#### Scenario: Toolbar appears when trades are selected
- **WHEN** user selects one or more trades
- **THEN** the bulk action toolbar becomes visible with the correct selected count

#### Scenario: Toolbar disappears when selection is cleared
- **WHEN** user deselects all trades
- **THEN** the bulk action toolbar is hidden

### Requirement: Bulk delete trades
The system SHALL provide a `POST /api/v1/trades/bulk/delete` endpoint. The request body SHALL contain `trade_ids` (list of UUIDs, 1–100 items). The endpoint SHALL delete only trades owned by the authenticated user. It SHALL return `{ "deleted_count": N }` with status 200. Trades not found or not owned by the user SHALL be silently skipped.

#### Scenario: Bulk delete owned trades
- **WHEN** authenticated user sends `POST /api/v1/trades/bulk/delete` with `{"trade_ids": ["id1","id2"]}`
- **THEN** both trades are deleted and response is `{"deleted_count": 2}`

#### Scenario: Bulk delete with mixed ownership
- **WHEN** request includes IDs where some belong to the user and some do not
- **THEN** only the user's trades are deleted; others are silently skipped; `deleted_count` reflects actual deletions

#### Scenario: Empty trade_ids list returns 422
- **WHEN** client sends `POST /api/v1/trades/bulk/delete` with `{"trade_ids": []}`
- **THEN** response status is 422

#### Scenario: Frontend shows confirmation before bulk delete
- **WHEN** user clicks the "Delete" button in the bulk action toolbar
- **THEN** a confirmation modal appears showing the count of trades to be deleted before executing

#### Scenario: After bulk delete, selection is cleared and list reloads
- **WHEN** bulk delete completes successfully
- **THEN** the selection is cleared and the trade list is refreshed

### Requirement: Bulk assign tags to trades (additive)
The system SHALL provide a `POST /api/v1/trades/bulk/assign-tags` endpoint. The request body SHALL contain:
- `trade_ids` (list of UUIDs, 1–100)
- `tag_ids` (list of UUIDs, 1–20)
- `mode`: `"add"` or `"remove"`

In `"add"` mode: specified tags SHALL be added to each trade's tag set without removing existing tags (ON CONFLICT DO NOTHING). In `"remove"` mode: specified tags SHALL be removed from each trade's tag set. Tags belonging to other users SHALL be rejected with 403. Response: `{ "updated_count": N }`.

#### Scenario: Add tags to multiple trades
- **WHEN** user sends `POST /api/v1/trades/bulk/assign-tags` with `mode: "add"`, 3 trade IDs, and 2 tag IDs
- **THEN** each of the 3 trades has the 2 tags added (existing tags preserved) and response is `{"updated_count": 3}`

#### Scenario: Add tag that already exists on a trade is idempotent
- **WHEN** a trade already has the specified tag and mode is "add"
- **THEN** no duplicate is created; operation succeeds

#### Scenario: Remove tags from multiple trades
- **WHEN** user sends `POST /api/v1/trades/bulk/assign-tags` with `mode: "remove"`, 2 trade IDs, and 1 tag ID
- **THEN** that tag is removed from both trades; `updated_count` is 2

#### Scenario: Tag not owned by user returns 403
- **WHEN** request includes a `tag_id` that belongs to a different user
- **THEN** response status is 403

#### Scenario: Frontend bulk tag modal shows tag multi-select
- **WHEN** user clicks "Assign Tags" or "Remove Tags" in the bulk action toolbar
- **THEN** a modal opens with a multi-select list of the user's tags and a confirm button

### Requirement: Bulk assign playbook to trades
The system SHALL provide a `POST /api/v1/trades/bulk/assign-playbook` endpoint. The request body SHALL contain:
- `trade_ids` (list of UUIDs, 1–100)
- `playbook_id` (UUID or null — null unassigns the playbook)

The endpoint SHALL only operate on trades owned by the authenticated user. Response: `{ "updated_count": N }`.

#### Scenario: Assign playbook to multiple trades
- **WHEN** user sends `POST /api/v1/trades/bulk/assign-playbook` with 5 trade IDs and a valid playbook UUID
- **THEN** all 5 trades have `playbook_id` set to that UUID and response is `{"updated_count": 5}`

#### Scenario: Unassign playbook from multiple trades
- **WHEN** user sends `POST /api/v1/trades/bulk/assign-playbook` with `playbook_id: null`
- **THEN** `playbook_id` is set to NULL on all specified trades

#### Scenario: Playbook not owned by user returns 403
- **WHEN** `playbook_id` belongs to a different user
- **THEN** response status is 403

#### Scenario: Frontend bulk playbook modal shows playbook dropdown
- **WHEN** user clicks "Assign Playbook" in the bulk action toolbar
- **THEN** a modal opens with a dropdown of the user's playbooks and a "None (unassign)" option
