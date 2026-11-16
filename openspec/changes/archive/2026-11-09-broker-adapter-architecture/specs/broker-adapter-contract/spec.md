## ADDED Requirements

### Requirement: Broker adapters are registered by key and declare capabilities
The system SHALL maintain a single broker adapter registry. Each broker integration SHALL be exactly one adapter identified by a unique broker key (`ibkr`, `schwab`) and mapped to exactly one `AccountType`. An adapter SHALL declare which of the following capabilities it supports: file import (with its accepted file extensions), remote sync, connection/authentication, and account binding. Capabilities an adapter does not declare SHALL be rejected at the call site with the same error semantics as today (e.g. sync on a `MANUAL` account → configuration error; upload of a disallowed extension → HTTP 422).

#### Scenario: Resolving the adapter for an account
- **WHEN** an import or sync is requested for an account of type `IBKR`
- **THEN** the registry SHALL resolve the `ibkr` adapter

#### Scenario: Account type without adapter
- **WHEN** a file upload is requested for a `MANUAL` account
- **THEN** the request SHALL be rejected with HTTP 422 and no data SHALL be written

#### Scenario: Disallowed file extension
- **WHEN** a `.csv` file is uploaded to an `IBKR` account whose adapter only accepts `.xml`
- **THEN** the request SHALL be rejected with HTTP 422 listing the accepted extensions

#### Scenario: Registry is the single source of truth
- **WHEN** a new adapter is registered
- **THEN** the upload endpoint's allowed extensions and the sync dispatch SHALL pick it up without editing route handlers, `ImportService` or `BrokerService`

### Requirement: Import pipeline is broker-agnostic
`ImportService.import_trades()` SHALL obtain a canonical import batch (raw executions, corporate actions, warnings) exclusively from the resolved adapter and SHALL NOT contain any conditional logic on the broker key or account type. Broker-specific behavior SHALL be expressed only through adapter capabilities or adapter-declared policy flags. It SHALL remain the single terminus for every ingestion path (file upload, remote sync, JSON body import).

#### Scenario: No broker branching in the pipeline
- **WHEN** the import service source is inspected (enforced by a unit test)
- **THEN** it SHALL NOT reference `BrokerType.IBKR`, `BrokerType.SCHWAB`, `AccountType.IBKR` or `AccountType.SCHWAB`

#### Scenario: Parser warnings travel in the batch
- **WHEN** an adapter skips a malformed execution during parsing
- **THEN** the warning SHALL be part of the returned batch and SHALL appear in `ImportResult.warnings` with the same text as before this change

### Requirement: Account binding is an adapter capability
When an adapter declares account binding, the pipeline SHALL invoke it before parsing, passing the payload and the target account. The capability SHALL select the payload subset belonging to the account and MAY bind an unset broker account number to the account, emitting the existing audit event.

#### Scenario: Schwab single-account auto-bind
- **WHEN** a Schwab payload with exactly one account entry is imported into a Schwab account with no `account_number`
- **THEN** the account's `account_number` SHALL be set from the payload and the existing account-number-bound audit event SHALL be emitted

#### Scenario: Schwab account mismatch
- **WHEN** a Schwab payload contains no entry matching the target account's `account_number`
- **THEN** the import SHALL fail with the same error and HTTP status as before this change

### Requirement: Adapter policy controls the pending-protected-close self-heal
The zero-insert self-heal (forcing a projection rebuild when an open protected trade has an absorbable unlinked execution) SHALL be enabled per adapter via a policy flag. The flag SHALL be enabled for the `schwab` adapter and disabled for `ibkr`.

#### Scenario: Schwab zero-insert with pending protected close
- **WHEN** a Schwab import inserts no new raw rows and an open protected trade has an absorbable unlinked execution
- **THEN** the projection SHALL be rebuilt, as before this change

#### Scenario: IBKR zero-insert stays a fast no-op
- **WHEN** an IBKR import inserts no new raw rows
- **THEN** the self-heal query SHALL NOT run and the import SHALL return the no-op result

### Requirement: Remote sync delegates fetch to the adapter and import to the pipeline
`BrokerService.sync_account` SHALL resolve the account's adapter, require the remote-sync capability, let the adapter fetch the broker payload unchanged, and pass that payload to `ImportService.import_trades()` with the same adapter key. Adapters SHALL NOT parse, aggregate, deduplicate or persist trades during fetch.

#### Scenario: IBKR Flex sync
- **WHEN** an IBKR account with a configured Flex token is synced with `from_date`
- **THEN** the IBKR adapter SHALL fetch the Flex XML and the result SHALL be identical to uploading that XML file

#### Scenario: Connection operations dispatch through the adapter
- **WHEN** a connection test or a Schwab OAuth authorize/complete/callback/status/disconnect call is made
- **THEN** the operation SHALL be served by the adapter's connection capability with unchanged endpoints, request and response schemas

### Requirement: Refactor preserves import behavior
The refactor SHALL NOT change observable import results. A golden-master suite captured before the refactor SHALL pass unchanged after it.

#### Scenario: Golden master for IBKR and Schwab fixtures
- **WHEN** each IBKR and Schwab test fixture is imported into a fresh account before and after the refactor
- **THEN** the normalized raw transactions, logical executions, trades (incl. combo groupings and open/closed state) and `ImportResult` counts and warnings SHALL be identical

#### Scenario: Re-import idempotency is preserved
- **WHEN** the same fixture is imported twice
- **THEN** the second import SHALL insert zero raw transactions and leave trades unchanged, as before the refactor

#### Scenario: Protected trades are preserved
- **WHEN** a fixture is re-imported after metadata (notes, tags, playbook) was attached to an open and a closed trade
- **THEN** protection outcomes reported in `ImportResult` and the persisted metadata SHALL be identical to the pre-refactor behavior
