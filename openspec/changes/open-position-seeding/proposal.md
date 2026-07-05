## Why

Multiple broker imports need the same thing — turn a broker's *currently-held positions* into open trades in the journal — but each was heading toward its own broker-specific solution:

- IBKR `<OpenPosition>` XML elements need converting into synthetic `BrokerRawTransaction` records so they flow through FIFO as opening legs.
- `schwab-positions-cli-import` writes Schwab `positions[]` into the wrapped file but **explicitly does not import them** ("Open-positions seeding is a separate capability" — its own design.md Non-Goals).

This capability defines the shared contract; each broker is an **adapter** that implements it (`ibkr-open-position-adapter`, `schwab-open-position-adapter`, and any future broker).

The underlying goal is identical and broker-neutral: **a broker reports an open holding → the system creates an open-lot trade (opening `LogicalExecution`, `pnl=None`, no `closed_at`) that later reconciles with its real closing execution.** There is no reason for IBKR and Schwab to model this differently at the domain level; only the *parse* step differs.

Crucially, the domain layer already supports open lots: `LogicalExecution.pnl` is nullable for opening legs, and the FIFO aggregator already produces an open `Trade` (no `exit_price`, no `closed_at`) and matches later closes against existing open lots. What is missing is a **shared, broker-neutral seam** that marks an execution as position-snapshot-derived (`origin = "open_position"`) and a documented policy for how a snapshot lot reconciles with the broker's own later close.

## What Changes

- Add a broker-neutral capability `open-position-seeding` that defines the domain contract for ingesting broker position snapshots as open-lot opening legs — independent of any single broker's file format.
- Add the `open_position` origin to `LogicalExecution` (`VALID_ORIGINS` + DB CHECK constraint via Alembic) so snapshot-derived opening legs are distinguishable from execution-derived ones.
- Define the **adapter boundary**: each broker parser is responsible for emitting position snapshots as `BrokerRawTransactionCreate` records flagged as open positions; the shared import/logical layer maps those to `LogicalExecution(origin="open_position")`. The *how a snapshot becomes a raw record* (timestamp source, dedup key) is a per-broker adapter concern; the *resulting domain semantics* are shared.
- Define **reconciliation semantics** so a snapshot open lot and the broker's own later closing execution converge on one round-trip `Trade` without duplicate open legs — including the case where the broker later reports the *opening* execution too (must not double-count).
- Position snapshots that carry no usable opening timestamp (Schwab `positions[]`) use a deterministic fallback so they remain idempotent across re-imports.

## Capabilities

### New Capabilities

- `open-position-seeding`: Broker-neutral domain contract for turning a broker-reported open holding into an open-lot opening `LogicalExecution` (`origin = "open_position"`, `pnl = None`), with idempotent re-import and reconciliation against the broker's own later closing execution.

### Modified Capabilities

- `raw-transaction-layer`: Add `open_position` as a valid `LogicalExecution.origin` value (shared by all brokers, not IBKR-only).

## Impact

- **Relationship to adapter changes** — this capability owns the *domain contract*; the broker specifics live in dedicated adapter changes that depend on it:
  - `ibkr-open-position-adapter`: the **IBKR adapter** (`<OpenPosition>` parsing + `openDate`/`transactionID` keys). It supersedes the earlier `ibkr-open-positions-import` change, whose `open_position` origin + `raw-transaction-layer` delta are subsumed here to avoid a duplicate/conflicting delta.
  - `schwab-open-position-adapter`: the **Schwab adapter** consuming `positions[]` (deterministic-id + approximate reconciliation).
  - `schwab-positions-cli-import` drops its "positions are not imported" Non-Goal and points at these as the consumers of Schwab `positions[]`.
- **Code**:
  - `backend/app/models/logical_execution.py` — add `EXECUTION_ORIGIN_OPEN_POSITION` + `VALID_ORIGINS` entry.
  - `backend/app/services/logical_execution_service.py` — `create_from_raw()` currently hardcodes `origin = EXECUTION_ORIGIN_IMPORTED`; branch to `open_position` when the raw record is flagged as a position snapshot.
  - `backend/app/schemas/broker_raw_transaction.py` — add a broker-neutral flag (e.g. `is_open_position: bool = False`) so parsers can mark snapshot-derived records without leaking broker specifics into the service.
  - Alembic migration widening the `logical_executions.origin` CHECK constraint.
- **APIs**: No new endpoints; no request/response schema changes. Behaviour change is confined to the import pipeline.
- **Tests**: broker-neutral unit tests for the origin/flag mapping and reconciliation; the IBKR and Schwab adapter changes supply their own parser fixtures.
- **Non-breaking** for existing imported/manual/merged/split executions and for the FIFO aggregator (no aggregator logic change).
