## Context

IBKR Flex Query XML reports include two distinct sections relevant to trade history:

- `<Trades>` / `<Trade>` — completed round-trip executions (both opening and closing legs are present)
- `<OpenPositions>` / `<OpenPosition>` — currently-held positions where only the opening leg exists

The current `IBKRXMLParser` processes only `<Trade>` and `<Execution>` elements. `<OpenPosition>` elements are read solely to build a validation set of known open conids, but are never converted into `BrokerRawTransaction` or `LogicalExecution` records. Consequently, any position opened before the report window (or with `from_date` filtering enabled) is invisible to the journal.

The `LogicalExecution` model supports a fixed `origin` field with values: `imported`, `manual`, `merged`, `split`. A new value `open_position` is needed to distinguish snapshot-derived opening legs from regular execution-derived ones.

The DB constraint on `origin` is enforced via a CHECK constraint (not an Enum type column), making it extensible without a destructive migration.

## Goals / Non-Goals

**Goals:**
- Parse `<OpenPosition>` elements in `parse_raw()` and emit one `BrokerRawTransaction` per open position
- Add `open_position` origin to `LogicalExecution` so these entries are distinguishable
- Deduplicate on re-import: if an open-position execution for the same `conid` + `executed_at` already exists as a `LogicalExecution`, skip it
- When a subsequent import contains a `<Trade>` that closes a position previously ingested as `open_position`, the FIFO aggregator matches entry leg (open_position) with close leg (imported) correctly — no code changes needed here as the aggregator works on `(symbol, conid, direction, quantity, executed_at)` keys
- Add Alembic migration to widen the DB CHECK constraint to include `open_position`
- Unit tests for parser and deduplication; integration test for full import cycle

**Non-Goals:**
- Automatically detecting when an open position transitions to closed (that happens naturally on the next import when `<Trade>` records appear)
- Modifying the FIFO aggregator logic
- Frontend or API schema changes
- Handling `<OpenPosition>` from Schwab or other brokers

## Decisions

### D1: Represent `<OpenPosition>` as a `BrokerRawTransaction` + `LogicalExecution(origin=open_position)`

**Options:**
- A) Treat as a regular `imported` execution (reuse existing origin)
- B) Add new `open_position` origin value

**Choice: B**

Rationale: `open_position` entries are snapshot-derived — they represent the broker's current view of an open lot, not a discrete execution event. Using a distinct origin makes it possible to identify and replace them on subsequent imports (re-import idempotency), skip them during execution leg display if needed, and avoid confusion in audit/debugging.

### D2: Deduplication key for open-position records

**Options:**
- A) Use `transactionID` from `<OpenPosition>` (matches the original `<Trade>` transactionID in IBKR)
- B) Use composite `conid` + `reportDate` (snapshot date)
- C) Use composite `symbol` + `executed_at` + `quantity`

**Choice: A with fallback to C**

IBKR `<OpenPosition>` elements carry a `transactionID` attribute that matches the original opening `<Trade>` element's `transactionID`. This allows exact 1:1 deduplication when both are present in the same or a later report. When `transactionID` is absent (some report configurations), fall back to deterministic composite key.

The raw transaction ID format: `ibkr:{transactionID}` — same as `<Trade>` records. This means if the original `<Trade>` was already imported, its `BrokerRawTransaction` already exists with the same ID, and the upsert in `BrokerRawTransactionRepository.bulk_upsert()` will skip the duplicate silently. No additional deduplication code required.

### D3: `openDate` vs `reportDate` as `executed_at`

**Choice:** Use `openDate` (the original trade date, present on `<OpenPosition>`) as `executed_at`.

This ensures the execution timestamp matches what the `<Trade>` element would carry, so the FIFO aggregator can match them by `(conid, executed_at)` across reports.

### D4: DB migration approach for `open_position` origin

The CHECK constraint `origin IN ('imported', 'manual', 'merged', 'split')` must be widened. Use Alembic `ALTER TABLE ... DROP CONSTRAINT ... ADD CONSTRAINT` pattern — this is a non-destructive add-only change with no data migration.

## Risks / Trade-offs

- **[Risk] `<OpenPosition>` transactionID absent in some Flex configurations** → Mitigation: composite key fallback (`ibkr:{symbol}:{datetime}:{qty}`) same as `<Trade>` fallback.
- **[Risk] Same position imported twice as both `<Trade>` (opening leg) and `<OpenPosition>`** → Mitigation: shared `transactionID` means `bulk_upsert` idempotently skips duplicates.
- **[Risk] DB CHECK constraint widening requires downtime** → Mitigation: ALTER CONSTRAINT is fast metadata-only in PostgreSQL for non-foreign-key checks; no row scan needed.
- **[Risk] FIFO aggregator produces duplicate open lots if open_position leg and a subsequent imported opening leg for the same position are both active** → Mitigation: deduplication in `import_service.py` skips `open_position` origin entries when an identical `(user_id, conid, executed_at)` already exists in `logical_executions`.

## Migration Plan

1. Alembic migration: widen CHECK constraint on `logical_executions.origin` to include `open_position`
2. Deploy backend — zero downtime, no data migration
3. Next IBKR sync or file import picks up `<OpenPosition>` elements automatically

Rollback: revert Alembic migration (constraint narrows back; any existing `open_position` rows would violate it — drain/delete them first if needed).

## Open Questions

- Should `open_position` executions be shown in the Execution Legs UI? Currently no change is planned; they will appear as regular opening legs. Mark as follow-up.
- IBKR `costBasis` on `<OpenPosition>` — should it be stored as the `price`? Yes: `costBasis / (quantity * multiplier)` gives the average open price per unit. Same calculation as `tradePrice` on `<Trade>`.
