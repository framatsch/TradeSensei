# raw-transaction-layer Specification

## Purpose
TBD - created by archiving change isolated-raw-layer-architecture. Update Purpose after archive.
## Requirements
### Requirement: Raw Transaction Model
The system SHALL provide an immutable `BrokerRawTransaction` table to store exact, unmodified broker execution data using the broker execution ID as the primary key.

#### Scenario: Persisting an execution
- **WHEN** a raw execution is imported from the broker
- **THEN** the system SHALL save it to `BrokerRawTransaction` without modifying original quantities or prices

### Requirement: Logical Execution Model
The system SHALL provide a mutable `LogicalExecution` table to store the application's view of executions, requiring a status flag indicating its lineage.

#### Scenario: Creating a logical execution
- **WHEN** a logical execution is created
- **THEN** it MUST contain a status flag chosen from: `imported`, `manual`, `merged`, or `split`

### Requirement: Transaction Execution Mapping
The system SHALL provide a `TransactionExecutionMapping` junction table to support n:m relationships between `BrokerRawTransaction` and `LogicalExecution`.

#### Scenario: Mapping an imported execution
- **WHEN** an initial logical execution is created from a raw transaction
- **THEN** a mapping record SHALL be created linking the two 1:1

