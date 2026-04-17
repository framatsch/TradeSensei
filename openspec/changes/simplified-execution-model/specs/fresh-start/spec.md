## Requirements

### Requirement: Fresh start wipes trades and executions for an account

The system SHALL provide a fresh-start import mode that deletes all `Trade` and `LogicalExecution` rows for a given account within a single DB transaction before processing a new import file. `BrokerRawTransaction` rows are never deleted.

#### Scenario: Fresh start deletes trades and executions, keeps BRTs
- **WHEN** `POST /imports/{account_id}/fresh-start` is called with an import file
- **THEN** all `LogicalExecution` rows for the account are deleted
- **AND** all `Trade` rows for the account are deleted
- **AND** all `BrokerRawTransaction` rows for the account remain unchanged
- **AND** the import file is then processed, creating new executions and trades from the existing BRTs

#### Scenario: Fresh start rolls back on import error
- **WHEN** `POST /imports/{account_id}/fresh-start` is called and the import processing fails
- **THEN** the entire operation (deletions + import) is rolled back
- **AND** the account data is restored to its pre-fresh-start state
- **AND** the response is an appropriate error status (422 or 500)

#### Scenario: After fresh start, re-import creates new executions
- **WHEN** a fresh start completed successfully and the same file is re-imported via the normal import endpoint
- **THEN** new executions and trades are created from the BRT rows
- **AND** suppressed BRTs are still skipped

#### Scenario: Fresh start confirmation requires explicit user acknowledgement
- **WHEN** the user initiates a fresh start from the import dialog
- **THEN** a confirmation step is shown with the message: "I understand this will delete all trades and executions for this account"
- **AND** the fresh-start endpoint is only called after the user explicitly confirms
- **AND** no request is made if the user dismisses the dialog
