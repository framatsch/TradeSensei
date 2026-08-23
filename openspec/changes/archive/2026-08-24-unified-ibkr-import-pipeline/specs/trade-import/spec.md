## ADDED Requirements

### Requirement: All broker ingestion terminates in the unified import service

Every path by which broker data enters the system — manual file upload, scheduled account sync, and direct broker API pull — SHALL terminate in `ImportService.import_trades()`. A broker-specific component MAY fetch a payload from a remote API, but SHALL NOT parse, aggregate, deduplicate, or persist trade data itself. No ingestion path may create a `Trade` row directly.

This exists because a parallel ingestion implementation silently misses every protection, invariant, and bug fix applied to the primary path. The IBKR Flex sync did exactly that and produced leg-less phantom trades in production while the primary path was demonstrably correct.

#### Scenario: Remote-fetch path delegates rather than persisting

- **WHEN** a broker sync retrieves a payload from a broker API
- **THEN** it SHALL pass the payload to `ImportService.import_trades()` with the matching `BrokerType`
- **THEN** it SHALL NOT call any trade or execution repository write method itself

#### Scenario: File upload and API sync are behaviourally identical

- **GIVEN** the same broker payload delivered once by file upload and once by API sync
- **WHEN** both are imported into the same account
- **THEN** the resulting trades, executions, and raw transactions SHALL be identical
- **THEN** the second ingestion SHALL be a no-op through raw-transaction idempotency

#### Scenario: No ingestion path creates a trade without executions

- **WHEN** any ingestion path creates a `Trade`
- **THEN** that trade SHALL have at least one linked `LogicalExecution`, or the execution SHALL be reported as unlinked per the execution-overwrite-protection capability

---

### Requirement: IBKR Flex import uses the raw-transaction pipeline

An import initiated through the IBKR Flex Web Service SHALL persist a `BrokerRawTransaction` per execution and a corresponding `LogicalExecution`, then build the trade projection through FIFO and combo aggregation — identical to an uploaded Flex Query XML file. Idempotency SHALL be keyed on the raw transaction `source_id` derived from the IBKR trade ID, not on `(symbol, opened_at)`.

#### Scenario: Flex import creates raw transactions and executions

- **WHEN** a Flex Query report is imported
- **THEN** a `BrokerRawTransaction` SHALL exist for each execution in the report
- **THEN** a `LogicalExecution` SHALL exist for each newly inserted raw transaction
- **THEN** every created trade SHALL have its executions linked

#### Scenario: Re-running a Flex import is idempotent

- **GIVEN** a Flex Query report already imported
- **WHEN** the same report is imported again
- **THEN** no duplicate raw transactions, executions, or trades SHALL be created
- **THEN** the zero-insert guard SHALL skip the projection rebuild

#### Scenario: Flex import result reports raw-pipeline outcomes

- **WHEN** a Flex import completes
- **THEN** `ImportResult` SHALL populate the raw-transaction and protection fields exactly as the file-upload path does
