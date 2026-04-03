## ADDED Requirements

### Requirement: Raw Data Ingestion
The parser SHALL persist imported data as `BrokerRawTransaction` records instead of converting them directly into intermediary aggregation objects.

#### Scenario: IBKR XML Import
- **WHEN** an IBKR XML flex query is imported
- **THEN** the system SHALL create `BrokerRawTransaction` records for each `<Execution>` node
- **THEN** the system SHALL NOT aggregate them into `Trade` entities during the parser phase

### Requirement: Logical Execution Translation
A dedicated service SHALL translate newly imported `BrokerRawTransaction` records into `LogicalExecution` entries.

#### Scenario: Translating initial imports
- **WHEN** raw transactions are successfully persisted
- **THEN** the system SHALL create corresponding `LogicalExecution` entries with the `imported` status flag
- **THEN** the system SHALL link them via `TransactionExecutionMapping`
