## Requirements

### Requirement: Re-import respects user-deleted executions

The system SHALL use `BrokerRawTransaction` (BRT) rows as the deduplication anchor. When a BRT exists and its linked execution has `deleted=true`, the import MUST skip that transaction without recreating the execution.

#### Scenario: Normal import creates BRT and execution
- **WHEN** an import file contains a transaction with no existing BRT matching its `composite_id`
- **THEN** a new BRT row is created
- **AND** a new `LogicalExecution` is created with `origin='imported'`, `deleted=false`

#### Scenario: Re-import of unchanged execution is idempotent
- **WHEN** a re-import file contains a transaction whose BRT already exists and the linked execution has `deleted=false`
- **THEN** neither the BRT nor the execution is modified

#### Scenario: Re-import respects soft-deleted execution
- **WHEN** a re-import file contains a transaction whose BRT already exists and the linked execution has `deleted=true`
- **THEN** the import skips the transaction — no new execution is created
- **AND** the existing deleted execution is not modified

#### Scenario: Re-import after full trade deletion
- **WHEN** a trade was deleted (all child executions set to `deleted=true`) and the same import file is re-imported
- **THEN** all transactions belonging to that trade are skipped
- **AND** no new executions or trade are created

#### Scenario: Re-import after fresh start
- **WHEN** a fresh-start import was performed (all `LogicalExecution` + `Trade` rows deleted, BRTs intact) and the same file is re-imported
- **THEN** new executions and trades are created from the existing BRT rows
- **AND** previously suppressed BRTs are still skipped

---

### Requirement: Broker transactions can be permanently suppressed

The system SHALL allow users to suppress a `BrokerRawTransaction` (set `suppressed=true`), causing all future imports to skip that transaction unconditionally, regardless of execution state.

#### Scenario: Suppressed BRT is skipped on import
- **WHEN** a BRT has `suppressed=true`
- **THEN** any import containing the matching `composite_id` skips the transaction
- **AND** no execution is created or modified

#### Scenario: User can suppress a BRT via API
- **WHEN** `PATCH /broker-raw-transactions/{id}/suppress` is called with `suppressed=true`
- **THEN** the BRT row is updated with `suppressed=true`
- **AND** subsequent imports skip this transaction

#### Scenario: User can unsuppress a BRT
- **WHEN** `PATCH /broker-raw-transactions/{id}/suppress` is called with `suppressed=false`
- **THEN** the BRT row is updated with `suppressed=false`
- **AND** subsequent imports process the transaction normally (creating an execution if none exists)
