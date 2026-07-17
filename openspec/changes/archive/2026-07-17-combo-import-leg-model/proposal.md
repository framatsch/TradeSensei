# Proposal: Import IBKR option combos as leg-native COMBO positions

## Why

IBKR Flex Query exports report multi-leg option strategies (vertical spreads,
etc.) as individual `<Trade>` execution rows. Today the importer runs every
execution through the FIFO aggregator, which produces one single-instrument
round-trip trade per option contract. A QQQ 712C/722C vertical spread therefore
appears as **two unrelated trades** instead of one COMBO position.

The `combo-positions` capability already defines the data model (`is_combo`,
nullable header fields, per-leg `asset_class`/`multiplier`) and the UI
requirements — but **nothing populates it from imports**. Only manually created
COMBO trades exist.

Separately, both broker parsers already receive an opening/closing signal —
IBKR via `openCloseIndicator`, Schwab via `positionEffect` (the latter was only
used for direction/PnL derivation in the archived
`2026-07-15-schwab-real-transactions-import` change and never persisted per
leg) — but neither stores it as a leg attribute. This information is required to
show open vs. close legs of a combo.

This change makes the IBKR importer detect combo orders and persist them as a
single COMBO `Trade` whose **execution legs are the real broker executions**,
so the user sees each individual instrument (long/short, open/close) instead of
a single opaque combo row or two disconnected trades. It also persists a new
per-leg `open_close` attribute for **both** IBKR and Schwab.

## What Changes

- **New per-leg `open_close` field** on `LogicalExecution` (`"O"` / `"C"` /
  `null`), derived in each broker parser (IBKR `openCloseIndicator`, Schwab
  nested `transferItems[].positionEffect`) and carried on
  `BrokerRawTransactionCreate`. Closes the gap left by the archived Schwab
  change and lets the UI distinguish opening from closing legs.
- **Combo detection is position-based, not FIFO-based.** Combo legs are grouped
  by broker order (`brokerageOrderID`) and matched into open→close positions.
  Legs are bound directly to the COMBO trade and are **not** run through the
  single-instrument FIFO round-trip logic. (IBKR only in this change.)
- **Exact-set open↔close matching.** A closing combo order matches an open combo
  position only when its `conid` set and per-contract quantities match exactly.
  Because a real IBKR combo is always opened and closed as one order, a
  combo-eligible closing order that fails to match exactly is a **data anomaly**:
  the import emits a warning (naming the order and the expected vs. received
  contract set) and leaves the combo position open, rather than silently
  rerouting legs into single-instrument FIFO.
- **Cross-import combos supported.** Open combo positions persisted in an
  earlier import are loaded as seed positions so a later import file that
  contains only the closing order correctly closes the COMBO trade.
- **COMBO header direction reflects net position**, derived from the net cash
  flow of the opening legs (net debit → LONG, net credit → SHORT). Per-leg
  `direction` (BUY/SELL) is preserved independently.
- **Spec extension**: the execution-legs table and `ExecutionSummaryCard`
  group legs by `(symbol, asset_class, conid)` and show an Open/Close column,
  so distinct strikes/legs of a combo remain visible.

## Non-goals

- Combo **detection** for Schwab imports (only the `open_close` field is
  populated for Schwab; Schwab combo grouping is a follow-up).
- Recomputing per-leg Greeks or spread analytics.
- Live-broker (TWS/API) combo sync.
- Manual combo creation flow changes (already covered by `combo-positions`).

## Impact

- Affected specs: `combo-positions` (extended)
- Affected code:
  - `backend/app/models/logical_execution.py` — new `open_close` column
  - Alembic migration — add `open_close` (nullable), `down_revision = c1f0baf3b07d`
  - `backend/app/schemas/broker_raw_transaction.py` — new `open_close` field
  - `backend/app/schemas/execution.py` — expose `open_close` in `LogicalExecutionRead`
  - `backend/app/utils/parsers/ibkr_xml.py` — set `open_close`, combo raw fields
  - `backend/app/utils/parsers/schwab_json.py` — set `open_close` from `positionEffect`
  - `backend/app/services/logical_execution_service.py` — copy `open_close`
  - `backend/app/utils/parsers/aggregator.py` — combo grouping + leg binding
  - `backend/app/services/import_service.py` — combo path wiring + cross-import seed
  - `backend/app/repositories/broker_raw_transaction_repository.py` — order-id/netcash lookup
  - `backend/app/repositories/trade_repository.py` — list open COMBO positions (seed)
  - `frontend` — legs table Open/Close column, `ExecutionSummaryCard` grouping
