## ADDED Requirements

### Requirement: Preset Date Selection
The system SHALL provide a mechanism to quickly select common timeframes for the import start date within the unified import dialog used for both Schwab and IBKR.
The available presets MUST include:
- Last 7 days
- Last 30 days
- Last 90 days
- Last 180 days
- Last 360 days
- Month to date (Seit Monatsanfang)
- Year to date (Seit Jahresanfang)

#### Scenario: User selects a preset timeframe
- **WHEN** the user selects "Last 30 days" from the presets dropdown
- **THEN** the date picker's start date is updated to the date exactly 30 days before today
- **AND** the end date remains unchanged (or is set to today if applicable)

#### Scenario: User selects Month to date
- **WHEN** the user selects "Month to date" from the presets dropdown
- **THEN** the date picker's start date is updated to the 1st day of the current month

#### Scenario: User selects Year to date
- **WHEN** the user selects "Year to date" from the presets dropdown
- **THEN** the date picker's start date is updated to January 1st of the current year
