## ADDED Requirements

### Requirement: Parse OpenPosition elements from IBKR Flex XML
The system SHALL parse `<OpenPosition>` elements from an IBKR Flex Query XML report and convert each one into a `BrokerRawTransactionCreate` flagged as an open-position snapshot (`is_open_position = true`), per the `open-position-seeding` contract. The parser SHALL NOT set the execution origin or create logical executions directly; the shared layer maps the flag to `origin = "open_position"`.

#### Scenario: OpenPosition is emitted as a contract-flagged raw record
- **WHEN** an IBKR Flex XML report contains an `<OpenPosition>` element
- **THEN** the parser SHALL emit a `BrokerRawTransactionCreate` with `is_open_position = true`
- **THEN** the parser SHALL NOT itself assign `origin` or `pnl` (the shared layer sets `origin = "open_position"`, `pnl = None`)

#### Scenario: OpenPosition with transactionID uses the shared-id scheme
- **WHEN** an `<OpenPosition>` element has a `transactionID` attribute
- **THEN** the raw record `id` SHALL be `"ibkr:{transactionID}"` (matching the eventual opening `<Trade>` id for exact reconciliation)

#### Scenario: OpenPosition without transactionID uses composite fallback key
- **WHEN** an `<OpenPosition>` element lacks a `transactionID` attribute
- **THEN** the raw record `id` SHALL be a deterministic composite of the form `"ibkr:{symbol}:{yyyymmddHHMMSS}:{quantity}"`

#### Scenario: OpenPosition executed_at uses openDate
- **WHEN** an `<OpenPosition>` element is parsed
- **THEN** the `executed_at` field SHALL be set from the `openDate` attribute in UTC

#### Scenario: OpenPosition price is derived from costBasis
- **WHEN** an `<OpenPosition>` element carries `costBasis`, `position`, and `multiplier` attributes
- **THEN** the price SHALL be computed as `abs(costBasis) / (abs(position) * multiplier)`

#### Scenario: CASH asset category OpenPositions are skipped
- **WHEN** an `<OpenPosition>` element has `assetCategory = "CASH"`
- **THEN** the parser SHALL skip the element without emitting a warning

#### Scenario: OpenPosition with missing symbol is skipped with warning
- **WHEN** an `<OpenPosition>` element lacks a `symbol` attribute
- **THEN** the parser SHALL skip the element and append a warning to `IBKRXMLParser.warnings`

### Requirement: IBKR open positions reconcile via the shared contract
The system SHALL rely on the `open-position-seeding` contract for open-lot creation, idempotency, and reconciliation of IBKR open positions — no IBKR-specific open-position domain logic.

#### Scenario: Open position becomes an open lot
- **WHEN** an IBKR `<OpenPosition>` raw record is imported and no closing leg exists yet
- **THEN** the FIFO aggregator SHALL produce an open `Trade` (no `closed_at`, no `exit_price`) visible in the journal

#### Scenario: Later closing Trade closes the open lot
- **WHEN** a subsequent import contains a `<Trade>` that closes a position previously ingested as an `open_position` leg
- **THEN** the aggregator SHALL match them into one `Trade` with both `opened_at` and `closed_at` populated

#### Scenario: Real opening Trade collapses with the snapshot (exact reconciliation)
- **WHEN** a subsequent import contains the opening `<Trade>` whose `transactionID` equals the snapshot's `transactionID`
- **THEN** the raw upsert SHALL treat it as a duplicate and no second opening `LogicalExecution` SHALL be created
