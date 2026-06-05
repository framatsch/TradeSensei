## 1. Backend — Schema Extensions

- [x] 1.1 Add `symbols: list[str] | None` and `excluded_symbols: list[str] | None` to `DashboardFilterConfig` Pydantic schema
- [x] 1.2 Add `asset_classes: list[AssetClass] | None` to `DashboardFilterConfig` Pydantic schema
- [x] 1.3 Replace `symbol: str | None` with `symbols: list[str] | None` and add `excluded_symbols: list[str] | None` to `TradeFilters` Pydantic schema (GET query params)

## 2. Backend — Repository Query Logic

- [x] 2.1 Update the trades list repository query to apply `symbols` include filter using `UPPER(symbol) ILIKE UPPER(value) || '%'` for each entry (OR logic)
- [x] 2.2 Update the trades list repository query to apply `excluded_symbols` using NOT ILIKE for each entry (AND NOT logic)
- [x] 2.3 Update analytics repository (used by all `/analytics/*` endpoints) to apply `symbols` and `excluded_symbols` predicates on the underlying trade subquery before aggregation
- [x] 2.4 Update analytics repository to apply `asset_classes` filter from `DashboardFilterConfig`
- [x] 2.5 Verify all analytics endpoints pass the new filter fields through to the repository layer

## 3. OpenAPI Client Regeneration

- [x] 3.1 Run `openapi-sync` skill to regenerate the frontend TypeScript client from the updated FastAPI spec

## 4. Frontend — SymbolTagInput Component

- [x] 4.1 Create `frontend/components/ui/SymbolTagInput.tsx` with `included`/`excluded` props and change callbacks
- [x] 4.2 Implement `!`-prefix typing shortcut (strips `!`, routes to excluded list)
- [x] 4.3 Implement comma-separated multi-entry (`AAPL, MSFT` → two tags on Enter)
- [x] 4.4 Uppercase all tags on entry
- [x] 4.5 Render include tags in neutral style and exclude tags with `text-destructive`/`border-destructive` tokens
- [x] 4.6 Implement duplicate-tag guard (silent ignore)
- [x] 4.7 Implement × removal button on each tag
- [x] 4.8 Add a help icon (e.g., Info or HelpCircle) with a tooltip/popover to `SymbolTagInput` explaining how to use multiple symbols, comma-separation, prefix matches, and the `!` exclusion syntax.
## 5. Frontend — Trades Filter Bar

- [x] 5.1 Replace the existing `symbol` text input in `TradeFilterBar.tsx` with `SymbolTagInput`
- [x] 5.2 Wire `included`/`excluded` state from `TradeFilters.symbols` and `TradeFilters.excluded_symbols`
- [x] 5.3 Update `useTradeFilterParams.ts` to serialize `symbols` as `symbols=A,B` and `excluded_symbols` as `excluded_symbols=C` in URL params
- [x] 5.4 Update `useTradeFilterParams.ts` to deserialize `symbols` and `excluded_symbols` from URL on page load
- [x] 5.5 Add URL backward-compat shim: if `symbol=` param exists in URL and `symbols=` does not, treat `symbol` value as first element of `symbols`

## 6. Frontend — Dashboard Filter Bar

- [x] 6.1 Add a collapsible "Extended Filters" toggle section to `WorkspaceFilterBar.tsx` (collapsed by default, persisted to `localStorage`)
- [x] 6.2 Add badge count to the toggle button showing number of active extended filter fields when collapsed
- [x] 6.3 Wire `SymbolTagInput` into the extended section, connected to `WorkspaceFilterContext` `symbols`/`excluded_symbols` state
- [x] 6.4 Add `asset_classes` multi-toggle (EQUITY / OPTION / FUTURE / FOREX / CRYPTO) to the extended section, matching the visual pattern in `TradeFilterBar`
- [x] 6.5 Auto-expand the extended section when the URL already has active extended filters on page load

## 7. Frontend — Workspace Filter Context & URL Sync

- [x] 7.1 Add `symbols: string[]`, `excluded_symbols: string[]`, `asset_classes: AssetClass[]` to `FilterConfig` in `WorkspaceFilterContext.tsx`
- [x] 7.2 Serialize `symbols`, `excluded_symbols`, `asset_classes` to URL params in the context's debounced URL sync
- [x] 7.3 Deserialize those params from URL on context initialization
