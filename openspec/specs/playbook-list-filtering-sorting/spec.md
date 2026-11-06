# playbook-list-filtering-sorting Specification

## Purpose
TBD - created by archiving change playbook-active-status-management. Update Purpose after archive.
## Requirements
### Requirement: Collapsible Playbook Filter Bar
The system SHALL provide an expandable/collapsible filter bar above the playbook overview list table (`PlaybookList`), mirroring the behavior and appearance of the Trading Log filter bar (`TradeFilterBar`).

#### Scenario: Expanding and collapsing the filter bar
- **WHEN** a user clicks the "Filter" toggle button
- **THEN** the filter panel toggles between expanded and collapsed state
- **AND** the chevron icon rotates to reflect the current open/closed state

#### Scenario: Displaying active filters counter badge
- **WHEN** one or more filters (e.g. status != default, tag selected, search query entered) are active
- **THEN** a badge showing the count of active filter criteria is displayed next to the "Filter" button label

### Requirement: Taxonomy Tag Filtering
The filter bar SHALL allow users to filter playbooks by one or more assigned taxonomy tags.

#### Scenario: Filtering by taxonomy tag
- **WHEN** a user selects one or more taxonomy tags in the filter bar
- **THEN** the playbook table displays only playbooks that have at least one of the selected tags assigned

#### Scenario: Clearing tag filters
- **WHEN** a user unselects all taxonomy tags
- **THEN** tag filtering is removed and playbooks are no longer constrained by tags

### Requirement: Playbook Text Search
The filter bar SHALL provide a text search input that filters playbooks by name or description.

#### Scenario: Searching by name keyword
- **WHEN** a user enters text into the playbook search field
- **THEN** the table immediately filters to show only playbooks whose name or description contains the search string (case-insensitive)

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

### Requirement: Filter Reset Action
The filter bar SHALL provide a "Clear all" or reset button when active filters exist.

#### Scenario: Resetting all filters
- **WHEN** a user clicks the "Clear all" button in the filter bar
- **THEN** all filter controls reset to their defaults (status to "Active", search cleared, tags cleared)
- **AND** the table refreshes to show the default active playbook list

