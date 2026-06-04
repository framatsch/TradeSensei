## Requirements

### Requirement: Save Checkin Filters
The system SHALL allow users to save their current check-in filter configuration (date range, regime, target indices, has media) under a custom name.

#### Scenario: User saves a new checkin filter view
- **WHEN** the user configures filters and clicks "Save View"
- **THEN** the system persists the filter configuration to the database and makes it available for future selection

### Requirement: Update Saved Checkin Filters
The system SHALL allow users to update an existing saved checkin filter configuration.

#### Scenario: User updates an existing checkin filter view
- **WHEN** the user modifies filters while a saved view is active and clicks "Save"
- **THEN** the system updates the filter configuration for that saved view in the database

### Requirement: Consistent Filter UI Paradigm
The system SHALL use a consistent filter bar UI paradigm across Trades, Workspaces, and Check-ins.

#### Scenario: UI Paradigm Consistency
- **GIVEN** a filter bar
- **THEN** it SHALL be a rounded card with a header and an expandable body
- **AND** the header's left side SHALL contain the expand/collapse toggle and the saved view selector (using a native `<select>`)
- **AND** the header's right side SHALL contain the action buttons (Save View, Update, Rename, Delete, Clear Filters) depending on the active state.
### Requirement: Delete Saved Checkin Filters
The system SHALL allow users to delete a saved check-in filter.

#### Scenario: User deletes a checkin filter view
- **WHEN** the user selects "Delete" on a saved view
- **THEN** the system removes the saved view from the database and reverts to the default check-in view
