## Context

Option combos are imported via the IBKR Flex Query XML parser and the Schwab JSON parser.
Both brokers encode option contracts in the OCC symbol format
(`<UNDERLYING><YYMMDD><C|P><8-digit strike>`, e.g. `QQQ   251003C00712000`). The IBKR parser
currently reduces this to the underlying (`_extract_occ_underlying`) before persisting, and
Schwab stores the full OCC string as `symbol` but never decodes it. The strike/expiry/type
therefore never reach the leg model, the API, the legs table, or the chart. The full raw
symbol survives only in each raw transaction's `raw_data`.

The leg model is `LogicalExecution` (created 1:1 from `BrokerRawTransaction` via
`LogicalExecutionService.create_from_raw`). Leg API responses use `LogicalExecutionRead`,
surfaced to the frontend inside `TradeRead.legs`. The frontend already has a working OCC
regex parser (`frontend/lib/parseOccSymbol.ts`) used as a fallback for the chart's underlying
symbol resolution. Contract details (strike/type/expiry) are surfaced exclusively on the
trade detail page (execution legs table, summary card) — not on the chart.

Constraints (AGENTS.md): `Decimal` for money (strike), timezone-aware UTC for timestamps
(expiry is a pure `date`, no time), schema changes via Alembic only, `mypy --strict` clean,
layered architecture, no `float`.

## Goals / Non-Goals

**Goals:**
- Make strike, expiry, and call/put first-class, queryable, nullable fields on the leg model.
- Populate them at import for both brokers; backfill existing option legs from `raw_data`.
- Surface them in the legs table and the summary card on the trade detail page.

**Non-Goals:**
- No chart-side option overlays (strike lines, option chips, expiry line, or a
  `localStorage`-persisted toggle popover). Contract details live on the trade detail page
  only — this was implemented in an earlier iteration and explicitly descoped; see
  `proposal.md` § Descoped.
- No options payoff / P&L-at-expiry diagram (belongs in a separate panel; mixes axes on a
  price chart and is out of scope).
- No change to FIFO aggregation, P&L, or the `Trade` top-level model.
- No re-import of existing data; backfill is data-only in the migration.
- No manual entry of `strike`/`expiry`/`option_type` in the TradeForm UI. The typed
  contract fields are derived automatically during broker import and backfilled for
  existing data. Manually created option trades will have `null` contract fields and
  therefore no Strike/Type/Expiry columns or chart overlays until a future "manual
  contract details" feature is added.

## Decisions

**Decision 1 — Typed columns over storing the raw OCC string.**
Add `strike` (`Numeric(18,8)`), `expiry` (`Date`), `option_type` (`String(1)`) to both
`logical_executions` and `broker_raw_transactions`. Rationale: strike, DTE, and moneyness
are analytical dimensions in trading software, not just display strings; typed columns are
queryable and type-safe. Alternative considered: add a single `occ_symbol` string column and
decode on the frontend — smaller, but leaves the data trapped in a string and unqueryable.
Rejected in favour of proper modeling. `option_type` mirrors the existing `open_close`
`String(1)` + validator pattern.

**Decision 2 — Shared OCC parser module `app/utils/occ.py`.**
Introduce `parse_occ_option(symbol) -> (Decimal | None, date | None, str | None)` and
`extract_occ_underlying(symbol) -> str` in a dependency-light module. Both broker parsers and
the Alembic backfill import it (the migration must not import the full parser modules). The
IBKR parser's existing `_extract_occ_underlying` is refactored to re-export the shared one so
behaviour is unchanged. Year handling (`yy <= 50 → 2000+yy else 1900+yy`) matches
`frontend/lib/parseOccSymbol.ts` so backend and frontend agree.

**Decision 3 — Parse before stripping in IBKR; parse from `symbol` in Schwab.**
IBKR must derive the fields from the original OCC symbol *before* `_extract_occ_underlying`
reduces it to the underlying. Schwab already keeps the full OCC symbol in `symbol`, so it
derives directly (and its existing symbol behaviour is left unchanged — surgical scope).

**Decision 4 — Backfill via `source_id` join for logical legs.**
`broker_raw_transactions` has `raw_data->>'symbol'` (the full OCC string) directly.
`logical_executions` has no `raw_data`; it links back through
`logical_executions.source_id = broker_raw_transactions.id`. The migration backfills BRT rows
from their own `raw_data`, then backfills logical legs by joining on `source_id`. Both are
scoped to `asset_class = 'OPTION'`; invalid/absent OCC symbols stay `null`.

**Decision 5 — Frontend distinct-leg key prefers typed fields.**
The summary card and chart group/label option legs by `(option_type, strike, expiry)` when
present, falling back to `conid` only when those are `null` (older/edge data). This makes
contracts human-readable while remaining robust for un-backfilled rows.

**Decision 6 — (Reverted) Chart-local overlay control.**
An earlier iteration added a "Chart layers" popover with `localStorage`-persisted toggles
for strike lines / chips / markers / expiry line. This was explicitly descoped per product
decision: contract details belong on the trade detail page, not the chart. `TradeChart.tsx`
was reverted to its pre-existing behaviour (generic entry/exit markers only, no option-aware
overlays). See `proposal.md` § Descoped.

**Decision 7 — Option contract display applies to single-option trades, not just COMBOs.**
A standard (non-COMBO) option trade has exactly one option leg, which receives the same
typed `strike`/`expiry`/`option_type` fields as any COMBO leg. The legs table therefore keys
Strike/Type/Expiry off "does this leg have `option_type != null`", not off `trade.is_combo`.
Concretely: the Symbol/Asset-Class columns in the legs table remain COMBO-gated (they exist
to disambiguate multiple instruments within one trade — irrelevant for a single-option
trade), but the Strike/Type/Expiry columns are gated only on "trade has ≥1 option leg". This
closes the gap where IBKR single-option trades previously showed nothing (their
`trade.symbol` is the bare underlying) and Schwab single-option trades relied on a fragile
client-side symbol regex — both now render identically from the leg fields, independent of
broker.

## Risks / Trade-offs

- **Backfill correctness for non-standard OCC symbols** → The shared parser validates the
  15-char suffix (all-digit expiry, `C`/`P`, all-digit strike) and returns `null`s on failure;
  the frontend fallback to `conid` keeps such legs functional.
- **Migration on large `broker_raw_transactions`** → Backfill is a single set-based UPDATE
  filtered to `asset_class = 'OPTION'` (a small subset); acceptable. If done in Python, batch
  to avoid loading all rows.
- **Two OCC parsers (backend Python + frontend TS) drifting** → Mitigated by matching the
  year-window logic explicitly and covering both with unit tests using the same fixtures.

## Migration Plan

1. Ship backend model/schema/parser changes + one Alembic revision (down_revision =
   current head) that adds the six nullable columns to both tables and backfills option legs
   from `raw_data` (BRT direct, logical via `source_id` join).
2. Regenerate the OpenAPI client so the frontend types include the new leg fields.
3. Ship frontend legs table and summary card.
4. Rollback: `downgrade()` drops the six columns; nullable additive columns mean no data loss
   for existing non-option behaviour. Frontend gracefully degrades (fields simply `null`).

## Open Questions

- Instrument-label format in the summary card: `QQQ 712 Call · Oct 3 2025` is proposed; final
  wording/locale can be adjusted during implementation without a spec change.
