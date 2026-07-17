# Design: Leg-native COMBO import

## Context

IBKR Flex Query reports each option execution as a `<Trade>` row. A multi-leg
strategy (e.g. a vertical spread) is a set of rows that share a
`brokerageOrderID` but reference different option contracts (`conid`). The full
lifecycle of a closed vertical is **4 executions**:

| # | conid | buySell | openClose | brokerageOrderID | pnl |
|---|-------|---------|-----------|------------------|-----|
| 1 | 712C  | BUY     | O         | `...6a4c7ea6...` | 0   |
| 2 | 722C  | SELL    | O         | `...6a4c7ea6...` | 0   |
| 3 | 712C  | SELL    | C         | `...6a4f2098...` | +465 |
| 4 | 722C  | BUY     | C         | `...6a4f2098...` | −393 |

Key facts confirmed from real data (`tmp/TradeSensei.xml`):

1. Every combo order is **either all-open or all-close** — a single
   `brokerageOrderID` never mixes O and C legs.
2. The opening order and the closing order have **different**
   `brokerageOrderID`s.
3. A "combo position" therefore spans **two** broker orders (open + close),
   linked by their shared set of contracts (`conid`s) and matching quantities.

Both broker parsers already have the open/close signal but discard it:

- **IBKR**: `openCloseIndicator` top-level attribute (`"O"`, `"C"`, `"C;O"`,
  `"O;C"`) — currently only used to derive `is_mixed_execution`.
- **Schwab**: nested `transferItems[n].positionEffect` (`"OPENING"` /
  `"CLOSING"`) — currently only used for direction/PnL (archived change
  `2026-07-15-schwab-real-transactions-import`).

## Goals / Non-Goals

**Goals**
- One COMBO `Trade` per matched open→close combo position (IBKR).
- All real executions bound as `LogicalExecution` legs (`trade_id → COMBO.id`).
- Per-leg `open_close` persisted for **both** IBKR and Schwab.
- COMBO header direction reflects net debit/credit.
- Cross-import open→close combos.

**Non-Goals**
- Schwab combo grouping, Greeks, live-broker sync.

## Decisions

### Decision 1: `open_close` derived in the parser, carried on the raw record

Because the two brokers store the signal in different `raw_data` shapes
(IBKR top-level, Schwab nested), the derivation lives in each parser, which
knows its own schema. `BrokerRawTransactionCreate` gains an `open_close: str |
None` field:

- IBKR (`ibkr_xml.py`): `openCloseIndicator` → `"O"` if it contains `"O"` and
  not `"C"`; `"C"` if it contains `"C"` and not `"O"`; `null` for mixed
  (`"C;O"`/`"O;C"`) or empty.
- Schwab (`schwab_json.py`): `positionEffect` → `"OPENING"` = `"O"`,
  `"CLOSING"` = `"C"`, else `null`.

`LogicalExecutionService.create_from_raw` then copies `raw.open_close` verbatim
onto the new `LogicalExecution` (broker-agnostic). `is_mixed_execution` keeps
its current derivation (unchanged).

**Alternative rejected**: deriving in the broker-agnostic service. It cannot
read Schwab's nested `positionEffect` without broker knowledge.

### Decision 2: Detect combos BEFORE FIFO, bind legs directly

The single-instrument FIFO aggregator destroys leg structure (it collapses each
contract into a round-trip and discards BUY/SELL + O/C per fill). Therefore
combo executions are **removed from the FIFO input** and handled by a dedicated
combo builder.

Pipeline (raw-data path in `ImportService.import_file`):

```
raw → logical executions (1:1, now with open_close)
     → partition executions:
         • combo-eligible executions → combo builder
         • everything else           → FIFO aggregator (unchanged)
     → persist COMBO trades + bind their legs
     → persist FIFO trades (unchanged) + split-aware backfill (unchanged)
```

**Alternative rejected**: post-FIFO merge (an earlier attempt). It cannot
recover leg structure and cannot bind legs, because the FIFO already consumed
the executions into round-trips.

### Decision 3: Combo eligibility = order-group with ≥2 distinct conids

An execution is combo-eligible when its `brokerageOrderID` order group contains
**two or more distinct `conid`s** (different instruments placed as one order).
Order groups with a single `conid` (multi-fill of one contract) are NOT combos
and go to FIFO.

### Decision 4: Position matching (open ↔ close) — exact set

A COMBO **position** is built by matching an opening combo order to a closing
combo order:

- **Opening order**: all legs `open_close = "O"`.
- **Closing order**: all legs `open_close = "C"`.

Matching algorithm (per `underlyingSymbol`, chronological):
1. Collect opening combo orders → each becomes an open COMBO position holding
   its opening legs (contract set = the order's `conid` set).
2. For each closing combo order, find the earliest open COMBO position whose
   contract set **equals exactly** the closing order's contract set, with
   matching absolute quantities per contract (FIFO across positions).
   - **Exact match** → attach closing legs; position becomes closed.
   - **No exact match** (mismatched set, quantity mismatch) → **data anomaly**:
     emit a warning and leave the open position open; do not reroute legs into
     single-instrument FIFO (Decision 6).

### Decision 5: COMBO header field derivation

For each COMBO position:
- `is_combo = true`
- `asset_class = null`, `quantity = null`, `entry_price = null`,
  `exit_price = null`
- `symbol = underlyingSymbol` (e.g. `"QQQ"`)
- `opened_at = MIN(open_leg.executed_at)`
- `closed_at = MAX(close_leg.executed_at)` when all opening contracts are
  closed, else `null`
- `commission = SUM(all leg.commission)`
- `pnl = SUM(close_leg.pnl)` when close legs exist, else `null`
- `net_pnl = pnl − total_commission` when `pnl` is not null
- `direction`: sign of the opening net cash flow
  (`SUM(open_leg.netCash)` from `raw_data`): net debit (cash out, negative) →
  `LONG`; net credit (cash in, positive) → `SHORT`.

### Decision 6: Unmatched combo close is a data anomaly → warn, keep combo open

For a genuine IBKR combo order the legs are always opened and closed together as
one order, so a partial close of a combo order **cannot occur** in valid IBKR
data. Therefore an all-`C` combo order that references an open combo position's
underlying but does **not** match its contract set / quantities exactly is
treated as a **data anomaly**, not an expected FIFO situation.

When this happens the combo builder SHALL:
- **not** silently reroute the legs into single-instrument FIFO,
- emit a parser/import **warning** naming the offending `brokerageOrderID`, the
  expected contract set, and the received contract set,
- leave the corresponding open COMBO position **open** (unclosed), and
- still bind the anomalous closing executions as legs to the open COMBO trade so
  no execution is lost (they remain visible under the combo, flagged via the
  warning), OR leave them unlinked if no open position shares the underlying —
  in which case the warning is the only signal.

This keeps behaviour loud and debuggable rather than masking a broker/data bug
behind a P&L number that silently differs from the combo the user placed.

Note: single-`conid` order groups (multi-fill of one contract) are **not** combo
orders (Decision 3) and continue to flow through single-instrument FIFO as
before — this decision only concerns order groups that are combo-eligible
(≥2 distinct conids) yet fail exact open↔close matching.

### Decision 7: Cross-import open→close combos (seed positions)

Open COMBO positions already persisted in the DB (from a prior import) are
loaded as **seed combo positions** and made available to the combo builder,
analogous to `seed_open_lots` for FIFO. A later import file containing only the
closing order can then match and close the existing COMBO trade (UPDATE), rather
than creating a disconnected trade.

- New repository method lists open COMBO trades with their opening legs for the
  user/account: contract set = distinct `conid`s of the trade's non-deleted
  opening legs.
- The combo builder seeds these as open positions before processing the file's
  opening orders.
- When a seed COMBO position is closed, the resulting change carries the
  existing `db_trade_id` so the import service issues an UPDATE (close) instead
  of INSERT — consistent with the single-instrument seed-lot path.

### Decision 8: New `open_close` column on `LogicalExecution`

`LogicalExecution` gains `open_close: str | None` (`"O"` / `"C"` / `null`),
nullable → backward compatible; existing rows stay `null`. Manual executions may
leave it `null`. Alembic migration sets `down_revision = "c1f0baf3b07d"`
(current head). Exposed in `LogicalExecutionRead`.

### Decision 9: UI leg grouping key includes conid + open_close

The `combo-positions` spec groups legs by `(symbol, asset_class)`. For combos
where all legs share `(QQQ, OPTION)` this would hide the individual strikes.
The grouping key is extended to `(symbol, asset_class, conid)` and the legs
table adds an **Open/Close** column. A closed vertical shows 4 rows.

## Risks / Trade-offs

- **Complexity in position matching.** Mitigated by strict "exact contract set +
  quantity" matching; anything ambiguous falls back to FIFO (never wrong P&L,
  just not grouped as combo).
- **Cross-import seed complexity.** The COMBO seed path mirrors the existing
  `seed_open_lots` mechanism; reuse its UPDATE-vs-INSERT convention via
  `db_trade_id`.
- **Migration.** Single nullable column, no backfill required (re-import
  repopulates `open_close` because the raw layer already stores the indicator).

## Migration Plan

1. Add nullable `open_close` column (Alembic, `down_revision = c1f0baf3b07d`).
2. Deploy backend (populates on new imports; old rows null).
3. Re-import to project combos and backfill `open_close` on logical executions
   (raw layer already stores `openCloseIndicator` / `positionEffect`).

## Open Questions

- None blocking. Schwab combo **grouping** (not just `open_close`) remains a
  documented follow-up.
