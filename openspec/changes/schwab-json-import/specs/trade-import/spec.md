## MODIFIED Requirements

### Requirement: Unified Import Dashboard
The system SHALL provide a unified `/dashboard/import` page that adapts dynamically to the target account's capabilities.

#### Scenario: Selecting a MANUAL Account
- **WHEN** the user selects an account of type `MANUAL`
- **THEN** the system SHALL NOT display any file upload dropzone or import option
- **THEN** the system SHALL display an informational message indicating that manual accounts do not support broker imports

#### Scenario: Selecting a SCHWAB Account (file upload)
- **WHEN** the user selects an account of type `SCHWAB`
- **THEN** the system SHALL display a file upload dropzone with `accept=".json"` (JSON files only)
- **THEN** the system SHALL display a prominent "Sync via API" button as the primary action
- **THEN** the file dialog SHALL only offer `.json` files for selection (not `.csv`)

#### Scenario: Selecting an API-enabled Account (non-SCHWAB)
- **WHEN** the user selects an account of type other than `MANUAL` or `SCHWAB`
- **THEN** the system SHALL display a prominent "Sync via API" button
- **THEN** the system SHALL also display a secondary option to upload files manually
