## ADDED Requirements

### Requirement: Trade rows are selectable
Each row in the trade table SHALL have a checkbox in the first column. A header checkbox SHALL select or deselect all visible rows on the current page.

#### Scenario: User selects individual rows
- **WHEN** user checks the checkbox on a trade row
- **THEN** that row is highlighted and added to the selection set

#### Scenario: Select all on page
- **WHEN** user checks the header checkbox
- **THEN** all rows on the current page are selected

#### Scenario: Deselect all
- **WHEN** user unchecks the header checkbox while all are selected
- **THEN** all rows are deselected

### Requirement: Bulk action toolbar appears on selection
When one or more trades are selected, a toolbar SHALL appear above the table showing the number of selected trades and the available bulk actions: "Delete", "Assign Tag", and "Assign Playbook".

#### Scenario: Toolbar appears
- **WHEN** at least one trade row is checked
- **THEN** the bulk action toolbar becomes visible with the count of selected trades

#### Scenario: Toolbar disappears
- **WHEN** all checkboxes are unchecked
- **THEN** the bulk action toolbar is hidden

### Requirement: User can bulk delete trades
The "Delete" bulk action SHALL prompt a confirmation dialog before deleting.

#### Scenario: Bulk delete confirmed
- **WHEN** user clicks "Delete" in the toolbar and confirms the dialog
- **THEN** a DELETE request is sent to `/trades/bulk` with the selected trade IDs
- **AND** the deleted trades disappear from the table
- **AND** the selection is cleared

#### Scenario: Bulk delete cancelled
- **WHEN** user clicks "Delete" but cancels the confirmation dialog
- **THEN** no API call is made and the selection remains

### Requirement: User can bulk assign a tag to trades
The "Assign Tag" bulk action SHALL open a tag picker. Selecting a tag assigns it to all selected trades.

#### Scenario: Bulk assign tag
- **WHEN** user clicks "Assign Tag", picks a tag, and confirms
- **THEN** a PATCH request is sent to `/trades/bulk/tags` with the selected IDs and chosen tag ID
- **AND** each affected trade row updates to show the new tag

### Requirement: User can bulk assign a playbook to trades
The "Assign Playbook" bulk action SHALL open a playbook picker. Selecting a playbook assigns it to all selected trades.

#### Scenario: Bulk assign playbook
- **WHEN** user clicks "Assign Playbook", picks a playbook, and confirms
- **THEN** a PATCH request is sent to `/trades/bulk/playbook` with the selected IDs and chosen playbook ID
- **AND** each affected trade's playbook column updates
