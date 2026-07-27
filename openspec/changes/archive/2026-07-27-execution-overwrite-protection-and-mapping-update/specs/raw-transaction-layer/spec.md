## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Transaction Execution Mapping
**Reason**: The `transaction_execution_mappings` junction table was scaffolded during the isolated-raw-layer-architecture change but never populated by the import pipeline. The codebase deliberately simplified to a direct 1:1 link expressed by `LogicalExecution.source_id → BrokerRawTransaction.id`, with `BrokerRawTransaction.suppressed` handling exclusion semantics. This spec requirement has caused ongoing spec-vs-code drift (see `logical_execution_service.get_logical_for_raw` which returns `[]` and explicitly documents that the mapping table is not used).

**Migration**: No data migration is required — the junction table has always been empty in practice. Consumers that referenced the requirement SHALL use `LogicalExecution.source_id` to trace a logical execution back to its raw transaction, and SHALL use `BrokerRawTransaction.suppressed` to determine whether a raw transaction is excluded from future imports. The `TransactionExecutionMapping` ORM model and the empty backing table MAY be removed in a separate cleanup change; they are out of scope here.
