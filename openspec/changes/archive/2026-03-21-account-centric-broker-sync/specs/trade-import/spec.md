## MODIFIED Requirements

### Requirement: Unified Import Dashboard
The system SHALL provide a unified `/dashboard/import` page that adapts dynamically to the target account's capabilities.

#### Scenario: Selecting a MANUAL Account
- **WHEN** the user selects an account of type `MANUAL`
- **THEN** the system SHALL display only the standard CSV upload dropzone

#### Scenario: Selecting an API-enabled Account (e.g. SCHWAB)
- **WHEN** the user selects an account of type `SCHWAB`
- **THEN** the system SHALL display a prominent "Sync via API" button
- **THEN** the system SHALL also display a secondary option to upload CSV files manually