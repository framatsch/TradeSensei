## ADDED Requirements

### Requirement: Playbook Editor Active / Inactive Toggle Flag
The system SHALL display an "Active / Inactive" toggle control in the playbook editor view (`PlaybookEditorClient`).

#### Scenario: Toggling active status to inactive in editor
- **WHEN** a user flips the "Active / Inactive" toggle for an active playbook to inactive
- **THEN** the system issues a PATCH request updating `is_active` to `false`
- **AND** the editor displays the status as "Inactive"

#### Scenario: Toggling inactive status to active in editor
- **WHEN** a user flips the "Active / Inactive" toggle for an inactive playbook to active
- **THEN** the system issues a PATCH request updating `is_active` to `true`
- **AND** the editor displays the status as "Active"

### Requirement: Playbook Overview List Status Column Toggle
The system SHALL make the `Status` column in the playbook overview table (`PlaybookList`) an interactive control allowing users to toggle a playbook between active and inactive in 1 click.

#### Scenario: Toggling active status from the table row
- **WHEN** a user clicks the status badge or toggle button in the "Status" column of an active playbook
- **THEN** the system issues a PATCH request setting `is_active` to `false`
- **AND** the UI updates optimistically to reflect the inactive state

#### Scenario: Toggling inactive status from the table row
- **WHEN** a user clicks the status badge or toggle button in the "Status" column of an inactive playbook
- **THEN** the system issues a PATCH request setting `is_active` to `true`
- **AND** the UI updates optimistically to reflect the active state

### Requirement: Removal of Delete Action from Playbook Overview Table
The system SHALL NOT display a delete button or confirmation dialog in the playbook overview table rows (`PlaybookList`).

#### Scenario: Overview table actions column displays Edit only
- **WHEN** a user views any row in the playbook overview table
- **THEN** the row actions cell displays the "Edit" action button
- **AND** no "Delete" or trash can icon is rendered in the row

#### Scenario: Delete remains accessible in the editor
- **WHEN** a user navigates to the playbook editor view (`PlaybookEditorClient`)
- **THEN** the permanent "Delete" action button remains available with its confirmation dialog

### Requirement: Trade Assignment Selectors Filter Inactive Playbooks
The system SHALL filter playbook selection dropdowns in trade qualitative metadata forms (`QualitativeMetadataPanel`) so that inactive playbooks are excluded from selectable options for new assignments, while preserving existing assignments.

#### Scenario: Inactive playbooks excluded from options for unassigned trades
- **WHEN** a user opens the trade metadata panel for a trade with no playbook assigned
- **THEN** only active playbooks are listed in the playbook dropdown options

#### Scenario: Existing inactive playbook assignment preserved and marked
- **WHEN** a user opens the trade metadata panel for a trade previously assigned to an inactive playbook
- **THEN** the assigned playbook remains selected and is visibly annotated as inactive (e.g., "Strategy Name (Inactive)")
