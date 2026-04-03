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

## ADDED Requirements

### Requirement: Corporate actions applied during import
The `ImportService` SHALL load all `CorporateAction` records for the authenticated user before invoking the parser, and pass them to the aggregator so that split adjustments are applied during execution matching.

#### Scenario: Import with corporate actions present
- **WHEN** a user with one or more `CorporateAction` records triggers a file import
- **THEN** the `ImportService` SHALL pass those records to the aggregator
- **THEN** the resulting trades SHALL reflect split-adjusted quantities and prices

#### Scenario: Manually edited trade is not overwritten on re-import
- **WHEN** a trade has `is_manually_edited = true`
- **THEN** the `ImportService` SHALL NOT overwrite that trade during a subsequent import of the same broker file

### Requirement: Import warning on potential unregistered split
The system SHALL emit a warning in the import result when a closing execution's quantity does not match any open lot and no applicable `CorporateAction` is registered for that symbol.

#### Scenario: Unmatched closing execution with no split registered
- **WHEN** a closing execution arrives for a symbol with open lots, but the quantity cannot be matched (suggesting a split)
- **THEN** the import result `warnings` array SHALL contain a message such as "Possible unregistered split detected for SYMBOL. Consider adding a Corporate Action."
