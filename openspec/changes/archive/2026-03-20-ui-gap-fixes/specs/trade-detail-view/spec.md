## MODIFIED Requirements

### Requirement: Trade detail page displays trade information
The trade detail page at `/dashboard/trades/[id]` SHALL display all trade fields in read-only mode by default. It SHALL resolve `playbook_id` to the playbook's human-readable `name` for display. An "Edit" button SHALL be visible to switch to edit mode (see trade-editing spec for edit behavior).

#### Scenario: Page loads and shows trade fields
- **WHEN** user navigates to `/dashboard/trades/{id}`
- **THEN** all trade fields are shown in a structured read-only layout including symbol, direction, asset class, quantity, entry price, exit price, PnL, commission, opened_at, closed_at, stop loss, take profit, currency, and tags

#### Scenario: Playbook name is shown instead of UUID
- **WHEN** a trade has a `playbook_id`
- **THEN** the detail page displays the playbook's `name` field, not the raw UUID string

#### Scenario: Edit button is visible
- **WHEN** user is on the trade detail page in read-only mode
- **THEN** an "Edit" button is visible that switches the page to edit mode
