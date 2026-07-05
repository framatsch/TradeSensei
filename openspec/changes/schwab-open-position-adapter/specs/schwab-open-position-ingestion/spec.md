## ADDED Requirements

### Requirement: Parse Schwab positions[] into open-position raw records
The system SHALL parse the `positions[]` array of the **account-matched** wrapped entry (the same entry selected by `schwab-json-import`'s account-number matching) and convert each holding into a `BrokerRawTransactionCreate` flagged as an open-position snapshot (`is_open_position = true`), per the `open-position-seeding` contract. The parser SHALL NOT set the execution origin or create logical executions directly, and SHALL NOT seed positions from any non-selected account entry.

#### Scenario: Only the account-matched entry's positions are seeded
- **WHEN** the wrapped file contains multiple `accounts[]` entries and account-number matching selects one
- **THEN** only that selected entry's `positions[]` SHALL be seeded as open lots
- **THEN** positions belonging to non-selected account entries SHALL NOT be seeded

#### Scenario: Raw id is broker-prefixed; user scoping is added by the service
- **WHEN** the parser emits a position raw record
- **THEN** its `id` SHALL be `"schwab:openpos:{accountNumber}:{symbol}:{longQuantity}"` (broker-prefixed, no user id)
- **THEN** the import service SHALL prepend `"{user_id}:"` before persistence (same convention as transaction records), yielding a per-user-unique idempotency key

#### Scenario: Entry with both long and short quantity emits two records
- **WHEN** a `positions[]` entry reports both a positive `longQuantity` and a positive `shortQuantity`
- **THEN** the parser SHALL emit two records: one LONG (from `longQuantity`) and one SHORT (from `shortQuantity`), each with its own deterministic id

#### Scenario: Position entry is emitted as a contract-flagged raw record
- **WHEN** the wrapped file contains a `positions[]` entry with a positive `longQuantity`
- **THEN** the parser SHALL emit a `BrokerRawTransactionCreate` with `is_open_position = true`, direction LONG, quantity = `longQuantity`
- **THEN** the parser SHALL NOT itself assign `origin` or `pnl` (the shared layer sets `origin = "open_position"`, `pnl = None`)

#### Scenario: Deterministic idempotency id
- **WHEN** a `positions[]` entry is parsed
- **THEN** the raw record `id` SHALL be `"schwab:openpos:{accountNumber}:{symbol}:{longQuantity}"` (or `{shortQuantity}` for short holdings)
- **WHEN** the same file is imported again
- **THEN** the id SHALL be identical and the raw upsert SHALL skip the duplicate

#### Scenario: executed_at uses the file dateRange.start instant
- **WHEN** a `positions[]` entry is parsed
- **THEN** the `executed_at` field SHALL be set from the file's top-level `dateRange.start` in UTC
- **THEN** the value SHALL precede any closing transaction within the same `dateRange`, so the snapshot opening leg sorts before its close

#### Scenario: Price and direction mapping
- **WHEN** a `positions[]` entry has a positive `longQuantity`
- **THEN** the price SHALL be `averageLongPrice`, falling back to `averagePrice` when absent
- **WHEN** a `positions[]` entry has a positive `shortQuantity`
- **THEN** the parser SHALL emit a SHORT record with quantity = `shortQuantity` and price = `averagePrice`

#### Scenario: Equity position mapping
- **WHEN** a `positions[]` entry has `instrument.assetType = "EQUITY"`
- **THEN** the emitted record SHALL have `asset_class = EQUITY`, `multiplier = 1`, and `symbol = instrument.symbol`

#### Scenario: Option position mapping
- **WHEN** a `positions[]` entry has `instrument.assetType = "OPTION"`
- **THEN** the emitted record SHALL have `asset_class = OPTION`, `multiplier = 100`, and `symbol = instrument.symbol` (the OCC option symbol, unchanged)

#### Scenario: Other asset types are skipped (positions only)
- **WHEN** a `positions[]` entry's `instrument.assetType` is neither `EQUITY` nor `OPTION`
- **THEN** the parser SHALL skip the entry and append a warning
- **THEN** this skip-on-unknown behaviour applies to position snapshots only and does NOT change the existing transaction-path behaviour (`schwab-json-import`'s "unknown assetType defaults to EQUITY"), which is deliberately left untouched

#### Scenario: Empty positions[] is a no-op
- **WHEN** an account entry has an empty `positions[]` array
- **THEN** the parser SHALL emit no open-position raw records and no warning

### Requirement: Schwab open positions reconcile via the shared contract
The system SHALL rely on the `open-position-seeding` contract for open-lot creation, idempotency, and reconciliation of Schwab open positions. Because Schwab positions carry no shared id, reconciliation SHALL use the contract's snapshot-replace rule. The FIFO aggregator identifies the instrument by `(symbol, conid, asset_class)` with `conid = None` for Schwab; the adapter adds no reconciliation code of its own.

#### Scenario: Position becomes an open lot
- **WHEN** a Schwab `positions[]` entry is imported and no closing transaction exists yet
- **THEN** the FIFO aggregator SHALL produce an open `Trade` (no `closed_at`, no `exit_price`) visible in the journal

#### Scenario: Later closing transaction closes the open lot
- **WHEN** a subsequent import contains a `TRADE` transaction for the same instrument `(symbol, conid=None, asset_class)` in the opposite direction to a position previously seeded from `positions[]`
- **THEN** the aggregator SHALL match them into one `Trade` with `opened_at` and `closed_at` populated

#### Scenario: Snapshot quantity change replaces the stale lot
- **WHEN** a prior import seeded a Schwab `open_position` leg for an instrument at one quantity
- **WHEN** a later import's `positions[]` reports the same instrument at a different quantity (or omits it)
- **THEN** the contract's snapshot-replace rule SHALL remove the stale `open_position` leg and seed the current snapshot
- **THEN** at most one `open_position` lot per instrument SHALL remain

#### Scenario: Real opening execution supersedes the snapshot leg
- **WHEN** a subsequent import contains a real `imported` opening execution for the same instrument `(symbol, conid=None, asset_class)` as a snapshot-seeded `open_position` leg
- **THEN** the contract's snapshot-replace rule SHALL drop the `open_position` leg in favour of the `imported` leg
- **THEN** exactly one open lot SHALL remain for that instrument
