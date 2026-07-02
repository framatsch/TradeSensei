## ADDED Requirements

### Requirement: Parse OpenPosition elements from IBKR Flex XML
The system SHALL parse `<OpenPosition>` elements from an IBKR Flex Query XML report and convert each one into a `BrokerRawTransaction` record.

#### Scenario: OpenPosition with transactionID is parsed
- **WHEN** an IBKR Flex XML report contains an `<OpenPosition>` element with a `transactionID` attribute
- **THEN** the parser SHALL emit a `BrokerRawTransactionCreate` with `id = "ibkr:{transactionID}"`

#### Scenario: OpenPosition without transactionID uses composite fallback key
- **WHEN** an `<OpenPosition>` element lacks a `transactionID` attribute
- **THEN** the parser SHALL emit a `BrokerRawTransactionCreate` with a deterministic composite ID of the form `"ibkr:{symbol}:{yyyymmddHHMMSS}:{quantity}"`

#### Scenario: OpenPosition executed_at uses openDate
- **WHEN** an `<OpenPosition>` element is parsed
- **THEN** the `executed_at` field of the resulting `BrokerRawTransactionCreate` SHALL be set from the `openDate` attribute in UTC

#### Scenario: OpenPosition price is derived from costBasis
- **WHEN** an `<OpenPosition>` element carries `costBasis`, `position` (quantity), and `multiplier` attributes
- **THEN** the price SHALL be computed as `abs(costBasis) / (abs(position) * multiplier)`

#### Scenario: CASH asset category OpenPositions are skipped
- **WHEN** an `<OpenPosition>` element has `assetCategory = "CASH"`
- **THEN** the parser SHALL skip the element without emitting a warning

#### Scenario: OpenPosition with missing symbol is skipped with warning
- **WHEN** an `<OpenPosition>` element lacks a `symbol` attribute
- **THEN** the parser SHALL skip the element and append a warning to `IBKRXMLParser.warnings`

### Requirement: OpenPosition raw transactions become open-position LogicalExecutions
The system SHALL create `LogicalExecution` records with `origin = "open_position"` for each newly-inserted `BrokerRawTransaction` derived from an `<OpenPosition>` element.

#### Scenario: LogicalExecution origin is open_position
- **WHEN** a `BrokerRawTransaction` derived from an `<OpenPosition>` element is inserted
- **THEN** the corresponding `LogicalExecution` SHALL have `origin = "open_position"`

#### Scenario: Open-position execution is an opening leg
- **WHEN** a `LogicalExecution` with `origin = "open_position"` is created
- **THEN** its `pnl` field SHALL be `None` (no realised P&L — position is still open)

### Requirement: Open-position ingestion is idempotent
The system SHALL not create duplicate `LogicalExecution` records when the same open position appears in multiple successive Flex reports.

#### Scenario: Re-import of same open position does not create a duplicate
- **WHEN** an IBKR sync or file import contains an `<OpenPosition>` element whose `transactionID` matches an already-existing `BrokerRawTransaction`
- **THEN** the `bulk_upsert` step SHALL silently skip the raw record and no new `LogicalExecution` SHALL be created

#### Scenario: OpenPosition and Trade with same transactionID coexist without duplication
- **WHEN** a subsequent import contains a `<Trade>` element whose `transactionID` matches an existing `open_position`-origin `BrokerRawTransaction`
- **THEN** the existing raw transaction record SHALL be reused (upsert no-op) and no second opening `LogicalExecution` SHALL be created

### Requirement: Closing a previously-imported open position merges into a round-trip trade
The system SHALL correctly aggregate an `open_position` opening leg with a subsequent `imported` closing leg into a single completed `Trade` record.

#### Scenario: Open position closing leg imported in subsequent sync
- **WHEN** a new IBKR sync contains a `<Trade>` that closes a position previously ingested as an `open_position` execution
- **THEN** the FIFO aggregator SHALL match the `open_position` opening leg with the new closing leg
- **THEN** the resulting `Trade` record SHALL have both `opened_at` and `closed_at` populated

#### Scenario: Open lot visible in journal before close
- **WHEN** an `open_position` execution has been imported but no closing leg exists yet
- **THEN** the FIFO aggregator SHALL produce an open `Trade` (no `closed_at`, no `exit_price`)
- **THEN** that trade SHALL be visible in the journal as an open position
