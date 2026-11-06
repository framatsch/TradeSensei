## MODIFIED Requirements

### Requirement: Playbook Overview List Status Column Toggle
The system SHALL make the status indicator in the playbook overview (`PlaybookList`) — both in the `Status` column of the tablet/desktop table (`md+`) and on each playbook card in the mobile card list (`< md`) — an interactive control allowing users to toggle a playbook between active and inactive in 1 click/tap without navigating into the playbook detail view.

#### Scenario: Toggling active status from the table row or mobile card
- **WHEN** a user clicks or taps the status badge/toggle button of an active playbook in the overview table or mobile card list
- **THEN** the system issues a PATCH request setting `is_active` to `false`
- **AND** the UI updates optimistically to reflect the inactive state without navigating away from the list

#### Scenario: Toggling inactive status from the table row or mobile card
- **WHEN** a user clicks or taps the status badge/toggle button of an inactive playbook in the overview table or mobile card list
- **THEN** the system issues a PATCH request setting `is_active` to `true`
- **AND** the UI updates optimistically to reflect the active state without navigating away from the list

### Requirement: Removal of Delete Action from Playbook Overview Table
The system SHALL NOT display a delete button or confirmation dialog in the playbook overview table rows (`md+`) or mobile playbook cards (`< md`) in `PlaybookList`.

#### Scenario: Overview table rows and mobile cards display Edit only
- **WHEN** a user views any playbook row in the tablet/desktop table or any playbook card in the mobile list
- **THEN** the item actions display the "Edit" action button (`?edit=true`)
- **AND** no "Delete" or trash can icon is rendered in the overview item

#### Scenario: Delete remains accessible in the editor
- **WHEN** a user navigates to the playbook editor view (`PlaybookEditorClient`)
- **THEN** the permanent "Delete" action button remains available with its confirmation dialog
