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

### Requirement: IBKR Flex Query Multiplier Extraction
The IBKR XML parser SHALL extract the `multiplier` attribute from `<Trade>` and `<Execution>` elements and assign it to the parsed raw transaction.

#### Scenario: Missing Multiplier
- **WHEN** an IBKR XML element does not contain a `multiplier` attribute
- **THEN** the parser SHALL default to 1

### Requirement: Ignore Broker PnL for Aggregation
The FIFO trade aggregator SHALL completely ignore any `pnl` (e.g. `fifoPnlRealized`) attached to `LogicalExecution` objects when calculating the aggregated `Trade` PnL.

#### Scenario: Batched Execution Match
- **WHEN** an execution matches multiple open lots with varying entry prices
- **THEN** the aggregator SHALL NOT split the broker's reported PnL
- **THEN** the aggregator SHALL dynamically calculate the Gross and Net PnL per match using exact execution prices and multipliers