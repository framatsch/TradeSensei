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

### Requirement: Broker-neutral execution grouping and position-effect fields
Each `BrokerRawTransaction` SHALL carry three broker-neutral fields populated by the broker adapter at parse time: `order_id` (nullable string; the broker's order-level grouping key used for combo detection), `net_cash` (nullable decimal; signed cash effect of the execution as reported or derived by the adapter), and `is_mixed_execution` (boolean, default `false`; true when one execution both closes and opens a position, i.e. a position flip). The import pipeline, combo builder and logical-execution creation SHALL read these fields and SHALL NOT read broker-specific keys from `raw_data` for these purposes.

#### Scenario: IBKR execution populates the neutral fields
- **WHEN** the IBKR adapter parses a `<Trade>` element with `brokerageOrderID="123"`, `netCash="-512.30"` and `openCloseIndicator="C;O"`
- **THEN** the resulting raw transaction SHALL have `order_id="123"`, `net_cash=-512.30` and `is_mixed_execution=true`

#### Scenario: Broker without order grouping
- **WHEN** an adapter parses an execution for which the broker supplies no order-level grouping key
- **THEN** `order_id` and `net_cash` SHALL be `NULL` and the execution SHALL NOT participate in combo grouping, exactly as before this change

#### Scenario: Logical execution inherits the mixed flag from the column
- **WHEN** a `LogicalExecution` is materialised from a raw transaction with `is_mixed_execution=true`
- **THEN** the logical execution's `is_mixed_execution` SHALL be `true`, regardless of the contents of `raw_data`

#### Scenario: Existing rows are backfilled
- **WHEN** the migration introducing the fields runs against existing raw transactions
- **THEN** `order_id` SHALL equal `raw_data->>'brokerageOrderID'`, `net_cash` SHALL equal `raw_data->>'netCash'` cast to decimal, and `is_mixed_execution` SHALL be true exactly when `upper(raw_data->>'openCloseIndicator')` contains `C;O` or `O;C`
- **THEN** a subsequent zero-change re-import SHALL produce the same trades, executions and combo groupings as before the migration

