## Context

The platform has two filter surfaces:

1. **Trades list** (`/dashboard/trades`) — uses `TradeFilters` (GET query params), already has a singular `symbol: str` field for exact-match text search.
2. **Dashboard/Workspace** (`/dashboard/workspace/*`) — uses `DashboardFilterConfig` (POST body), has no symbol or asset class filter at all.

Both surfaces have saved-view support. URL sync is bidirectional and debounced. The backend analytics layer receives `DashboardFilterConfig` and applies it before aggregating metrics; trade list queries apply `TradeFilters` at the repository layer.

There is no shared filter-input component between the two surfaces — each has its own filter bar.

## Goals / Non-Goals

**Goals:**
- Add `symbols` (include, prefix-match) and `excluded_symbols` (exclude, prefix-match) to both `TradeFilters` and `DashboardFilterConfig`.
- Add `asset_classes` to `DashboardFilterConfig` (already exists in `TradeFilters`).
- Build a reusable `SymbolTagInput` frontend component with include/exclude chip semantics.
- Replace the existing singular `symbol` text input in `TradeFilterBar` with the new tag input.
- Add the new symbol and asset-class fields to `WorkspaceFilterBar` inside a collapsible "Extended Filters" section.
- Keep active extended filters visible via a badge count even when the section is collapsed.
- Serialize new fields to/from URL params on both pages.
- Preserve saved view backward compatibility (new fields default to `null`/empty).

**Non-Goals:**
- Regex or full-text search on symbols — prefix-match only.
- Case-sensitive matching — always case-insensitive (`ILIKE`).
- Symbol autocomplete / type-ahead (out of scope for this change).
- Hour-of-day / day-of-week filters on the Dashboard — trade-level only.
- DB schema changes or migrations — purely query-level predicates.

## Decisions

### Decision 1: Prefix-match via `ILIKE 'value%'` instead of exact match

**Chosen:** `ILIKE 'AAPL%'` applied on the trade's `symbol` column.

**Rationale:** Options symbols share a root ticker (`AAPL240119C00150000`). Exact match would require knowing the full OCC symbol. Prefix-match covers equities (exact match is a degenerate prefix) and options naturally. No index change needed — existing B-tree index on `symbol` supports prefix-match queries.

**Alternative considered:** Full-text search (`tsvector`). Rejected — overkill, requires schema change, and breaks expected "starts with" semantics.

---

### Decision 2: Separate `symbols` + `excluded_symbols` lists instead of inline `!`-syntax in storage

**Chosen:** Two separate fields in the Pydantic schema and query model.

**Rationale:** Inline `!TSLA` mixed with `AAPL, MSFT` in a single string is ambiguous at the model level, harder to validate, and error-prone to parse. Storing them separately keeps the backend contract clean. The `!`-prefix is kept only as a **typing shortcut** in the UI: when the user types `!TSLA` and hits Enter, the UI interprets it as an exclude tag — it is never stored or transmitted as `!TSLA`.

---

### Decision 3: Extend existing `TradeFilters.symbol` to `symbols: list[str]` (breaking change within the filter interface)

**Chosen:** Replace `symbol: str | None` with `symbols: list[str] | None` in `TradeFilters`.

**Rationale:** Keeping both `symbol` and `symbols` creates ambiguity. The singular field is currently used only by `TradeFilterBar` (one input). Migrating the URL param from `symbol=AAPL` to `symbols=AAPL` is a minor URL-shape change with no saved-view impact (saved views store the filter object, not raw URL params).

**Alternative:** Add `symbols` alongside `symbol` (backward-compat shim). Rejected — doubles complexity for no real benefit; no external consumers depend on this URL shape.

---

### Decision 4: Collapsible "Extended Filters" section on Dashboard only

**Chosen:** WorkspaceFilterBar gets a collapsible section for symbol + asset class filters; TradeFilterBar adds the tag input inline (no separate section).

**Rationale:** TradeFilterBar is already a long panel with many fields — no need for another collapsible layer. WorkspaceFilterBar is currently compact (6 fields); adding symbol/asset-class inline would make it feel crowded. A collapsible section with badge count (e.g. "Extended (2)") keeps the default view clean.

---

### Decision 5: `SymbolTagInput` as a standalone reusable component

**Location:** `frontend/components/ui/SymbolTagInput.tsx`

**Props:**
```ts
interface SymbolTagInputProps {
  included: string[];
  excluded: string[];
  onIncludedChange: (v: string[]) => void;
  onExcludedChange: (v: string[]) => void;
  placeholder?: string;
}
```

On Enter/comma: if input starts with `!`, strip `!` and add to excluded; otherwise add to included. Tags are uppercased on entry. Excluded tags render with a red/destructive style using the existing design token (`text-destructive`, `border-destructive`).

---

### Decision 6: URL serialization format

| Field | URL param | Example |
|---|---|---|
| `symbols` (include) | `symbols` | `symbols=AAPL,MSFT` |
| `excluded_symbols` | `excluded_symbols` | `excluded_symbols=TSLA` |
| `asset_classes` (dashboard) | `asset_classes` | `asset_classes=EQUITY,OPTION` |

Comma-separated values, no `!` prefix in URL. Both filter contexts (workspace + trades) use the same param names for consistency.

## Risks / Trade-offs

**[Performance] ILIKE prefix scan on large trade tables** → Mitigation: existing B-tree index on `symbol` is usable for prefix patterns (`AAPL%`). Monitor query plan if table grows beyond ~1M rows; add a dedicated index if needed.

**[Saved Views silent mismatch] Existing views have no `symbols`/`excluded_symbols` fields** → Mitigation: Pydantic schema uses `None` as default; backend treats missing fields as "no filter". No migration needed. Views created before this change will simply have no symbol filter applied.

**[URL backward compat] `symbol=` param renamed to `symbols=`** → Mitigation: bookmarks/shared URLs with `symbol=` will silently drop the filter (unrecognized param ignored). Acceptable — this is a filter URL, not a resource URL. Add a one-liner URL migration shim in `useTradeFilterParams` if needed (`symbol` → first element of `symbols`).

**[UX discoverability — Extended section collapsed by default]** → Mitigation: Show badge count "Extended (N)" when any extended filter is active, even while collapsed.

## Migration Plan

1. Backend changes first: extend Pydantic schemas, update repository query builders. No DB migration.
2. Regenerate OpenAPI client (`openapi-sync` skill).
3. Frontend: build `SymbolTagInput`, wire into both filter bars, extend URL serialization.
4. No rollback complexity — feature is additive; removing new UI fields leaves backend unchanged.

## Open Questions

- Should `asset_classes` on the Dashboard filter use the same multi-toggle button style as TradeFilterBar (5 toggles: EQUITY / OPTION / FUTURE / FOREX / CRYPTO)? → Assumption: yes, reuse the same pattern.
- Should symbols be uppercased on the backend (normalization) or only on the frontend? → Assumption: frontend uppercases on tag entry; backend applies `UPPER(symbol) ILIKE UPPER(pattern)%` to be safe.
