## ADDED Requirements

### Requirement: User can edit trade fields inline
The trade detail page SHALL provide an "Edit" toggle button that switches the read-only display into an editable form. The form MUST cover all mutable trade fields: symbol, direction, asset class, quantity, entry price, exit price, stop loss (clearable), take profit (clearable), opened_at, closed_at, commission, currency, and PnL override.

#### Scenario: User opens edit mode
- **WHEN** user clicks the "Edit" button on a trade detail page
- **THEN** all mutable fields become editable inputs pre-filled with current values

#### Scenario: User saves changes
- **WHEN** user edits one or more fields and clicks "Save"
- **THEN** a PATCH request is sent to `/trades/{id}` with only the changed fields
- **AND** the page returns to read-only mode displaying the updated values

#### Scenario: User cancels editing
- **WHEN** user clicks "Cancel" while in edit mode
- **THEN** all fields revert to their original values and the form closes without making any API call

#### Scenario: Save with validation error
- **WHEN** user submits the form with an invalid value (e.g., exit price negative)
- **THEN** an inline error message is shown next to the invalid field
- **AND** no API call is made

### Requirement: User can assign tags to a trade
The edit form SHALL include a multi-select tag picker that shows all available tags and allows adding or removing tags from a trade.

#### Scenario: Add tag to trade
- **WHEN** user selects a tag in the tag picker and saves
- **THEN** the trade is saved with the new tag included in its tag list

#### Scenario: Remove tag from trade
- **WHEN** user deselects a tag that was previously on the trade and saves
- **THEN** the trade is saved without that tag

### Requirement: User can assign a playbook to a trade
The edit form SHALL include a single-select playbook dropdown populated from `/playbooks`. Selecting "None" SHALL clear the playbook assignment.

#### Scenario: Assign playbook
- **WHEN** user picks a playbook from the dropdown and saves
- **THEN** the trade's `playbook_id` is updated and the playbook name is shown on the detail page

#### Scenario: Clear playbook
- **WHEN** user selects "None" in the playbook dropdown and saves
- **THEN** the trade's `playbook_id` is set to null

### Requirement: User can clear optional numeric fields
Stop loss and take profit fields SHALL each have a "Clear" action that explicitly sets the value to null (not merely empty string).

#### Scenario: Clear stop loss
- **WHEN** user clicks "Clear" next to the stop loss field and saves
- **THEN** PATCH request sends `stop_loss: null`
- **AND** the field is shown as "—" (not set) on the detail page after save

### Requirement: Playbook name is resolved on trade detail
The trade detail page SHALL display the playbook's human-readable name (not its UUID) when a playbook is assigned.

#### Scenario: Trade with playbook shows name
- **WHEN** a trade has a `playbook_id`
- **THEN** the detail page displays the playbook's `name` field, not the raw UUID
