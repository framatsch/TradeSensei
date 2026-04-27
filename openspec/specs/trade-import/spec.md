## MODIFIED Requirements

### Requirement: Unified Import Dashboard
The system SHALL provide a unified `/dashboard/portfolios/{portfolioId}/import` page that adapts dynamically to the target account's capabilities. The page MUST resolve the portfolio context from the URL and restrict the account selector to accounts belonging to that portfolio.

#### Scenario: Selecting a MANUAL Account within a portfolio
- **WHEN** the user selects an account of type `MANUAL` within the portfolio context
- **THEN** the system SHALL display only the standard CSV upload dropzone

#### Scenario: Selecting an API-enabled Account (e.g. SCHWAB) within a portfolio
- **WHEN** the user selects an account of type `SCHWAB` within the portfolio context
- **THEN** the system SHALL display a prominent "Sync via API" button
- **THEN** the system SHALL also display a secondary option to upload CSV files manually

## ADDED Requirements

### Requirement: Import currency mismatch warning
The system SHALL compare the imported trade's `currency` field against the
portfolio's `base_currency`. When they differ, the system SHALL include a
`currency_mismatch` warning in the `ImportResult.warnings` list but SHALL NOT
block the import.

#### Scenario: Import with matching currency — no warning
- **WHEN** all imported trades have the same currency as the portfolio
  `base_currency`
- **THEN** the `ImportResult.warnings` list SHALL NOT contain a
  `currency_mismatch` entry

#### Scenario: Import with mismatching currency — warning emitted
- **WHEN** at least one imported trade has a currency that differs from the
  portfolio `base_currency`
- **THEN** the `ImportResult.warnings` list SHALL contain a
  `currency_mismatch` entry describing the number of affected trades
- **THEN** the import SHALL still succeed and all trades SHALL be persisted
