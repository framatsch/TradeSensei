## MODIFIED Requirements

### Requirement: Playbook Table Column Sorting
The system SHALL allow users to sort playbooks in the overview (`PlaybookList`) both via clickable column headers ("Name", "Created", "Status") in the tablet/desktop table (`md+`) and via a compact sort `<select>` dropdown (`aria-label="Sort playbooks"`) in the mobile card view (`< md`).

#### Scenario: Sorting by name ascending and descending
- **WHEN** a user clicks the "Name" column header on tablet/desktop or selects `Name: A → Z` / `Name: Z → A` in the mobile sort select
- **THEN** playbooks are sorted alphabetically by name in the selected direction
- **AND** clicking the column header again on tablet/desktop reverses the sort order (descending)
- **AND** a sort indicator icon shows the current column and direction

#### Scenario: Sorting by creation date
- **WHEN** a user clicks the "Created" column header on tablet/desktop or selects `Created: newest` / `Created: oldest` in the mobile sort select
- **THEN** playbooks are sorted by their `created_at` timestamp in ascending or descending order

#### Scenario: Sorting by status on mobile or desktop
- **WHEN** a user clicks the "Status" column header on tablet/desktop or selects `Status: Active first` / `Status: Inactive first` in the mobile sort select
- **THEN** playbooks are sorted by their `is_active` boolean state in the requested order
