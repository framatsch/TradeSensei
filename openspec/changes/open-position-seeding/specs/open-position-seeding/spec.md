## ADDED Requirements

### Requirement: Broker position snapshots seed open-lot opening legs
The system SHALL convert a broker-reported open holding (a position snapshot) into an opening `LogicalExecution` with `origin = "open_position"` and `pnl = None`, so that the FIFO aggregator produces an open-lot `Trade` (no `exit_price`, no `closed_at`). This behaviour SHALL be broker-neutral: the domain semantics do not depend on which broker produced the snapshot.

#### Scenario: Open-position raw record becomes an open_position logical execution
- **WHEN** the import pipeline processes a `BrokerRawTransactionCreate` flagged as a position snapshot (`is_open_position = true`)
- **THEN** the resulting `LogicalExecution` SHALL have `origin = "open_position"`
- **THEN** the resulting `LogicalExecution` SHALL have `pnl = None`

#### Scenario: Open-position leg produces an open trade
- **WHEN** an `open_position` opening `LogicalExecution` exists and no matching closing leg has been imported
- **THEN** the FIFO aggregator SHALL produce a `Trade` with no `closed_at` and no `exit_price`
- **THEN** that trade SHALL be visible in the journal as an open position

#### Scenario: Regular imported executions are unaffected
- **WHEN** the import pipeline processes a `BrokerRawTransactionCreate` that is not flagged as a position snapshot (`is_open_position = false` or unset)
- **THEN** the resulting `LogicalExecution` SHALL have `origin = "imported"`

### Requirement: Adapter boundary for position snapshots
The system SHALL keep broker-specific parsing separate from the shared open-position domain semantics. Broker parsers SHALL be responsible for emitting position snapshots as `BrokerRawTransactionCreate` records with a deterministic, per-user-unique raw `id` and a timezone-aware UTC `executed_at`; the shared import/logical layer SHALL be responsible for mapping the flag to `origin = "open_position"`.

Any broker import that supports open positions SHALL implement this contract: it MUST express open holdings via the broker-neutral `is_open_position` flag and the shared `origin = "open_position"` value, and MUST NOT introduce a broker-specific model, origin value, or code path for open positions. This applies to current adapters (IBKR, Schwab) and any future broker adapter.

#### Scenario: Parser marks a snapshot record with a neutral flag
- **WHEN** a broker parser emits a raw record derived from a position snapshot
- **THEN** it SHALL set the broker-neutral `is_open_position` flag on the `BrokerRawTransactionCreate`
- **THEN** it SHALL NOT require any broker-specific branching in `LogicalExecutionService` to obtain the `open_position` origin

#### Scenario: A new broker adapter reuses the shared contract
- **WHEN** a new broker import adds support for open positions
- **THEN** it SHALL reuse the `is_open_position` flag and `origin = "open_position"` value
- **THEN** it SHALL NOT define a broker-specific origin, model, or open-position code path

#### Scenario: Snapshot record carries a deterministic idempotency id
- **WHEN** the same position snapshot is imported more than once
- **THEN** the raw record's `id` SHALL be identical across imports
- **THEN** the raw-transaction upsert SHALL silently skip the duplicate and no second opening `LogicalExecution` SHALL be created

### Requirement: Open-position ingestion is idempotent
The system SHALL NOT create duplicate opening `LogicalExecution` records when the same open position appears in multiple successive imports.

#### Scenario: Re-import of the same open position is a no-op
- **WHEN** an import contains a position snapshot whose raw `id` matches an already-existing `BrokerRawTransaction`
- **THEN** the upsert SHALL skip the raw record and no new `LogicalExecution` SHALL be created

### Requirement: Snapshot lots reconcile with the broker's own executions
The system SHALL converge a snapshot-seeded open lot and the broker's own later closing execution onto a single round-trip `Trade`, and SHALL NOT leave two open lots for one real position when both a snapshot opening leg and a real opening execution exist. Matching relies on the FIFO aggregator's instrument key `(symbol, conid, asset_class)`; `direction` and `quantity` govern open/close pairing within that instrument's queue, not the instrument identity.

#### Scenario: Snapshot lot closed by a subsequently imported closing execution
- **WHEN** an `open_position` opening leg exists and a later import contains a closing execution for the same instrument `(symbol, conid, asset_class)` in the opposite direction
- **THEN** the FIFO aggregator SHALL match them into one `Trade` with both `opened_at` and `closed_at` populated

#### Scenario: Real opening execution supersedes the snapshot leg (shared id)
- **WHEN** a broker provides a shared raw `id` (e.g. IBKR `transactionID`) and a later import contains the real opening execution whose raw `id` equals the snapshot record's raw `id`
- **THEN** the upsert SHALL treat it as a duplicate and no second opening `LogicalExecution` SHALL be created
- **THEN** exactly one open lot SHALL remain for that position

### Requirement: Position snapshots are the source of truth for a broker account's open lots
On each import that carries position snapshots, the system SHALL make the snapshot set authoritative for that account's open lots: existing `open_position`-origin legs for the same `(account, instrument)` that are not present in the new snapshot set SHALL be removed before the new snapshots are seeded, so a re-import never leaves stale (superseded or quantity-changed) snapshot lots. This single "snapshot-replace" rule covers both quantity changes and the case where a real opening execution has since taken over.

#### Scenario: Quantity change does not leave a stale snapshot lot
- **WHEN** a prior import seeded an `open_position` leg for an instrument at quantity Q1
- **WHEN** a later import's snapshot set reports the same instrument at a different quantity Q2 (or omits it entirely)
- **THEN** re-aggregation SHALL remove the stale Q1 `open_position` leg before seeding the current snapshot
- **THEN** at most one `open_position` open lot per `(account, instrument)` SHALL remain, reflecting the latest snapshot

#### Scenario: Real opening execution supersedes the snapshot leg (no shared id)
- **WHEN** a broker cannot provide a shared id and a real `imported` opening execution exists for an instrument `(symbol, conid, asset_class)` that also has an `open_position` snapshot leg
- **THEN** re-aggregation SHALL drop the `open_position` leg in favour of the `imported` opening leg
- **THEN** exactly one open lot SHALL remain for that instrument

#### Scenario: Snapshot leg without a competing real execution is retained
- **WHEN** an `open_position` leg exists and the current snapshot still reports that instrument and no real `imported` opening execution overlaps it
- **THEN** the `open_position` leg SHALL be retained as the open lot
