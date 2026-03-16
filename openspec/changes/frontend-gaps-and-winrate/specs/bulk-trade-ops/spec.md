## ADDED Requirements

### Requirement: User can select multiple trades in the trade list
The system SHALL display a checkbox column in the trade table. Checking individual
rows selects those trades. A header checkbox selects or deselects all visible trades.

#### Scenario: Select individual trade
- **WHEN** user checks the checkbox on a trade row
- **THEN** that trade is added to the selection
- **AND** a bulk action bar appears at the bottom of the page

#### Scenario: Select all visible trades
- **WHEN** user clicks the header checkbox
- **THEN** all trades currently visible in the table are selected
- **AND** the bulk action bar shows the count of selected trades

#### Scenario: Deselect all
- **WHEN** user unchecks the header checkbox while all rows are selected
- **THEN** all selections are cleared and the bulk action bar disappears

---

### Requirement: User can bulk delete selected trades
The system SHALL allow the user to delete all selected trades at once via a
"Delete" action in the bulk action bar, with a confirmation dialog.

#### Scenario: Bulk delete with confirmation
- **WHEN** user selects trades, clicks "Delete", and confirms the dialog
- **THEN** all selected trades are deleted
- **AND** the trade list refreshes without the deleted trades

#### Scenario: Cancel bulk delete
- **WHEN** user clicks "Delete" but cancels the confirmation
- **THEN** no trades are deleted

---

### Requirement: User can bulk assign a tag to selected trades
The system SHALL allow the user to assign one tag to all selected trades via a
tag picker in the bulk action bar.

#### Scenario: Bulk assign tag
- **WHEN** user selects trades, picks a tag from the bulk action bar's tag selector, and confirms
- **THEN** the selected tag is added to all selected trades
- **AND** trades that already had the tag are unaffected

---

### Requirement: User can bulk assign a playbook to selected trades
The system SHALL allow the user to assign one playbook to all selected trades via
a playbook picker in the bulk action bar.

#### Scenario: Bulk assign playbook
- **WHEN** user selects trades and picks a playbook from the bulk action bar
- **THEN** all selected trades are updated to reference that playbook
