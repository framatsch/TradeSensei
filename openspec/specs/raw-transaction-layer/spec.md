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
The system SHALL provide a mutable `LogicalExecution` table to store the application's view of executions, requiring a status flag indicating its lineage. Each `LogicalExecution` SHALL carry a nullable `source_id` string column that stores the primary key of the `BrokerRawTransaction` it was materialised from; for `origin='manual'` rows `source_id` MAY be `NULL` until the user links the row via the manual-to-broker link endpoint (see the `execution-overwrite-protection` capability).

#### Scenario: Creating a logical execution
- **WHEN** a logical execution is created
- **THEN** it MUST contain a status flag chosen from: `imported`, `manual`, `merged`, or `split`

#### Scenario: Imported execution carries the raw transaction id
- **WHEN** a logical execution is created by the import pipeline from a `BrokerRawTransaction`
- **THEN** its `source_id` SHALL equal the raw transaction's primary key

#### Scenario: Manual execution has no source id by default
- **WHEN** a user creates a `LogicalExecution` with `origin='manual'`
- **THEN** `source_id` SHALL be `NULL` unless the user subsequently links it via the manual-to-broker link endpoint
