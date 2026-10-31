## Context

`playbook-checkin-document-layout` introduced a mobile pattern for qualitative detail views: a compact Header Card followed by a segmented switcher (`flex lg:hidden p-1 rounded-xl bg-secondary border border-border`, `role="tablist"`) whose panes stay mounted and are toggled with `hidden lg:block`. The trade views never received a mobile treatment:

- **Trade Detail** (`app/dashboard/trades/[id]/page.tsx`): desktop header (`md:flex-row`), `grid lg:grid-cols-3` with `MediaChartsCard` (`min-h-[400px]`) and a 9-row Performance list, followed by `ExecutionSummaryCard`, `QualitativeMetadataPanel`, `NoteList` and `ExecutionLegsTable` (10–16 columns, `overflow-x-auto`). On a phone everything stacks; the journal sits several screens down and legs scroll horizontally.
- **Trades list** (`TradesPageClient` → `TradeFilterBar`, `BulkActionToolbar`, `TradeTable` / `TradeRow`): 12-column table in `overflow-x-auto`, filter panel with ~18 fields in `grid-cols-1` below `sm`, bulk toolbar with four text buttons in one row.
- Several controls are hover-only (`opacity-0 group-hover:opacity-100`): journal edit (`QualitativeMetadataPanel`), screenshot delete/zoom (`MediaChartsCard`), quick-note actions (`NoteList`).

Constraints: frontend-only, no new dependencies (`@radix-ui/react-dialog` and `@radix-ui/react-dropdown-menu` are already installed), semantic color tokens only (no `dark:` in new code), UI review baselines `375×812` (mobile) and `1440×900` (desktop) per `.opencode/agents/ui-reviewer.md` and `docs/styleguide.md` §11.

## Goals / Non-Goals

**Goals:**
- Mobile (`< lg`) layouts for Trade Detail and Trades list that reuse the established segmented-switcher pattern and match the reference wireframes in `specs/trade-detail-mobile-ui/spec.md` and `specs/trade-list-mobile-ui/spec.md`.
- Full functional parity with desktop on mobile: every action (inline SL/TP edit, journal, leg edit/split/move/detach/delete, bulk actions, every filter, saved views) remains reachable.
- Zero visual or behavioral change on `lg+`, except the new Previous/Next navigation row.
- Previous/Next navigation through the user's current filtered and sorted trade list on all viewports, including `←`/`→` shortcuts, without backend changes.

**Non-Goals:**
- Any other desktop (`lg+`) layout change.
- Restoring the exact list page (cursor) when returning via `Back to Trades` — filters, sort and saved view are restored, the list starts at page 1.
- Cross-tab or server-side persistence of the list context.
- Day/date grouping in the trade list (explicitly rejected — achievable via date filters).
- Swipe gestures, pull-to-refresh, infinite scrolling.
- Trade create/edit forms (`/dashboard/trades/new`, `/edit`), import page, dashboard/report pages.
- Backend, API or schema changes.

## UI Mockups

The reference wireframes are part of the specs so they survive archiving into `openspec/specs/`:
- Trade Detail: `specs/trade-detail-mobile-ui/spec.md` → *Requirement: Trade Detail mobile layout reference*
- Trades list, selection mode, filter sheet: `specs/trade-list-mobile-ui/spec.md` → *Requirement: Trades list mobile layout reference*
- Previous/Next navigation (desktop + mobile): `specs/trade-detail-navigation/spec.md` → *Requirement: Trade navigation layout reference*

## Decisions

### 1. Single breakpoint `lg` (1024px) for all mobile behavior
- **Decision**: Every mobile adaptation in this change switches at `lg`, identical to the Playbook/Check-in switchers and the dashboard sidebar (`lg:hidden` overlay in `app/dashboard/layout.tsx`). Verification happens at `375×812`; `768×1024` must also render without overflow.
- **Alternative**: Cards below `md`, table from `md`. Rejected — the 12-column table also overflows between 768–1023px, and one breakpoint across the app is easier to reason about and test.

### 2. CSS-based dual rendering instead of a JS media query
- **Decision**: Mobile and desktop variants are both rendered and toggled via Tailwind (`hidden lg:block` / `lg:hidden`). `TradeTable` renders the `<table>` (`hidden lg:block` wrapper) and a card list (`lg:hidden`) from the same `trades` array, selection state and handlers. The detail page keeps a local `mobileTab: "overview" | "journal" | "executions"` state (default `"overview"`) and applies the same visibility pattern as `PlaybookEditorClient`.
- **Rationale**: No hydration mismatch or layout flash (the page is a client component but initial render happens before `matchMedia` is known), no resize listeners, and inactive panes stay mounted — critical for the TradingView widget and unsaved journal drafts.
- **Alternative**: `useMediaQuery` and conditional rendering. Rejected for the reasons above. Cost of dual rendering: at most 100 extra card nodes per page — negligible.

### 3. Dedicated mobile header block
- **Decision**: The existing desktop header is wrapped with `hidden lg:flex`; a new `TradeMobileHeader` component (`components/trades/TradeMobileHeader.tsx`, `lg:hidden`) receives the already-computed values (`realizedR`, `returnPct`, holding period string, flags) from the page plus callbacks for `Correct Trade…` / `Merge with…`. Its `⋯` menu uses `@radix-ui/react-dropdown-menu` (as `ExecutionRow` does) instead of the page's hand-rolled `overflowRef` menu.
- **Alternative**: Make the desktop header responsive with additional breakpoint classes. Rejected — the KPI strip and three-row structure differ too much; responsive class juggling would risk desktop regressions, which are a non-goal.

### 4. Shared leg-editing logic via `useExecutionLegEditor`
- **Decision**: Extract the draft state, `handleSave` / `handleCancel` / delete-confirm / `handleRestore`, error message and `canSplit` / `canLinkBroker` derivations from `ExecutionRow` into `hooks/useExecutionLegEditor.ts`. `ExecutionRow` (desktop, unchanged markup) and the new `ExecutionLegCard` (mobile) both consume it. `ExecutionLegsTable` renders the `<table>` (`hidden lg:table`) and the card list (`lg:hidden`) from the same `timelineItems`, and is expanded by default below `lg`.
- **Alternative A**: Copy the logic into the card. Rejected — two diverging implementations of the same mutation flow are exactly the failure mode the project rules warn about.
- **Alternative B**: Make leg editing desktop-only. Rejected — violates the parity goal.

### 5. Filter field registry + tabbed bottom sheet
- **Decision**: Refactor `TradeFilterBar`'s inline field JSX into a `renderField(key)` function keyed by a `FilterFieldKey` union, plus a `FILTER_GROUPS` constant (`trade`, `time`, `journal`, `account`) and a `countActiveFilters(filters, keys?)` helper. The desktop panel iterates the existing field order (unchanged output); the new `TradeFilterSheet` (`components/trades/TradeFilterSheet.tsx`) iterates one group per tab. The sheet is built on `@radix-ui/react-dialog` (focus trap, `Esc`, overlay close — same primitive as `CheckinFilterBar` modals) and anchored to the bottom (`fixed inset-x-0 bottom-0 max-h-[90dvh] rounded-t-2xl`).
- **Decision**: Filters apply live through the existing `onChange` (URL sync unchanged); `Show results` only closes the sheet.
- **Alternative A**: A separate mobile filter form. Rejected — duplicates ~400 lines and every future filter would need to be added twice.
- **Alternative B**: Draft-then-apply semantics in the sheet. Rejected — diverges from desktop behavior and saved-view logic, which operate on the live filter state.
- **Alternative C**: `vaul` drawer library. Rejected — new dependency for one component.

### 6. Selection mode and bottom bulk bar
- **Decision**: `TradeTable` owns a local `selectionMode` boolean (mobile only; desktop always shows checkboxes). `Done` clears the selection via the existing `onSelectionChange`. `BulkActionToolbar` renders its current sticky-top markup as `hidden lg:flex` and a new fixed-bottom variant as `lg:hidden` (`fixed inset-x-0 bottom-0 z-30 pb-[env(safe-area-inset-bottom)]`) with the same props. The list adds bottom padding while the bar is visible.

### 7. Journal dirty state surfaced to the page
- **Decision**: `QualitativeMetadataPanel` gets an optional `onDirtyChange?: (dirty: boolean) => void` prop so the page can show the dot on the `Journal` tab. The panel renders its existing header Save/Cancel controls as `hidden lg:flex` and a fixed bottom bar (`lg:hidden`, same z-index/safe-area classes as Decision 6) when dirty.

### 8. Touch-visible hover controls
- **Decision**: Replace `opacity-0 group-hover:opacity-100` with `opacity-100 lg:opacity-0 lg:group-hover:opacity-100` (plus `lg:group-focus-within:opacity-100` where already used) in the affected trade components only.

### 9. Sticky segmented switcher
- **Decision**: The detail switcher uses `sticky top-0 z-10` with an opaque `bg-background` wrapper so it stays reachable inside `<main className="overflow-y-auto">`. The conflict banner's `onReview` sets `mobileTab = "executions"` before scrolling to `#executions-table`.

### 10. Frontend-only list context in `sessionStorage`
- **Decision**: `lib/tradeListContext.ts` defines the context type and `read` / `write` helpers for the key `tradesensei.tradeListContext`:
  ```ts
  interface TradeListContext {
    portfolioId: string;
    filters: TradeFilters;          // effective filters sent to the API (incl. enforced status)
    sort: TradeSortConfig;
    limit: number;
    listQuery: string;              // URL search string of /dashboard/trades (incl. view_id)
    viewName: string | null;
    total: number | null;
    pages: { cursor: string | null; ids: string[]; nextCursor: string | null }[];
  }
  ```
  `TradeTable` writes it in an effect whenever `data` for the current cursor arrives: same query (portfolio/filters/sort/limit deep-equal) → upsert the page at `cursorStack.length - 1`; different query → replace with a fresh context. `TradesPageClient` passes `listQuery` and the active view name down to `TradeTable`.
- **Rationale**: The backend already uses keyset cursor pagination with filters and sort; because `TradeTable`'s cursor stack always starts at page 1, the stored pages always cover page 1 … current page contiguously. `Previous` therefore never needs a request, and `Next` at a page edge is one regular list request with the stored `nextCursor` — through `useTrades` with identical parameters, so the TanStack Query cache (`["trades", portfolioId, cursor, limit, filters, sort]`) is shared with the list.
- **Alternative A**: New backend endpoint `GET /trades/{id}/neighbors` with the filter query. Rejected for now — duplicates the keyset logic for every sort field including the NULL-sort-value edge cases in `TradeRepository.list_cursor`, needs a backend release, and adds nothing for the main flow (opening trades from the list). Could be added later to support deep links.
- **Alternative B**: Store only the IDs of the current page. Rejected — navigation would stop at page boundaries.
- **Alternative C**: `localStorage`. Rejected — the context would leak across tabs, and two tabs with different filters would overwrite each other. The user requirement is "in the session".

### 11. `useTradeNavigation` hook and `TradeNavControls`
- **Decision**: `hooks/useTradeNavigation(tradeId)` reads the context, ignores it if the portfolio differs or the ID is not found, and returns `{ available, prevId, nextId, position, total, sourceLabel, isLoadingNext, goPrev, goNext, backHref }`. At the last ID of the last stored page it enables `useTrades` for the stored `nextCursor` only when `goNext` is invoked, then appends the page and navigates. Navigation uses `router.replace`. Adjacent symbols for tooltips come from the TanStack cache of the list page if present (no extra requests).
- `components/trades/TradeNavControls.tsx` renders the buttons + indicator in two variants: `desktop` (labelled buttons, nav row next to `Back to Trades`, `hidden lg:flex`) and `compact` (icon-only, used inside `TradeMobileHeader`).
- **Keyboard**: one `window` `keydown` listener in the page (pattern already used in `PlaybookEditorClient`) handling `ArrowLeft` / `ArrowRight`, skipping editable targets, modifiers, `defaultPrevented`, open page modals (`correctModalOpen`, `tradePickerOpen`, `mergePreviewOpen`) and any open `[role="dialog"]` / `[role="menu"]` / `[aria-modal="true"]` element. The screenshot `Lightbox` in `MediaChartsCard` gets `role="dialog" aria-modal="true"` so it is covered by the check.
- **Unsaved changes**: the `onDirtyChange` prop from Decision 7 is reused; `goPrev`/`goNext` call `window.confirm` when dirty (same mechanism as existing confirms in `TradesPageClient`).

## Risks / Trade-offs

- **[Risk] Duplicate DOM breaks existing tests** (`getByText("AAPL")` now matches table row and card; two `Save` buttons in the journal panel) → **Mitigation**: scope unit-test queries with `within(...)` on `role="table"` / a `data-testid="trade-card-list"` container; jsdom does not apply Tailwind visibility, so tests must target containers explicitly. Playwright mobile cases run with a `375×812` viewport where only one variant is visible.
- **[Risk] Duplicate `aria-label`s** (e.g. two `Trade actions` buttons, two `Back to Trades` links) → **Mitigation**: hidden variants use `display: none`, which removes them from the accessibility tree; Playwright uses `getByRole`, which ignores hidden elements.
- **[Risk] Absolute-positioned dropdowns (`AccountMultiSelect`, `SymbolTagInput` suggestions) clipped inside the sheet's scroll area** → **Mitigation**: verify in the sheet; if clipped, render the dropdown list inline (static) when inside the sheet via a `variant="inline"` prop.
- **[Risk] Fixed bottom bars overlap iOS home indicator or the on-screen keyboard** → **Mitigation**: `pb-[env(safe-area-inset-bottom)]`; journal bar is only shown while dirty, and the textarea keeps natural page scrolling.
- **[Risk] Sticky switcher offset inside a padded scroll container** → **Mitigation**: verify at `375×812`; if content shows through above it, use a negative top margin matching `<main>` padding (`-mt-4` / `top-0` with `pt-4` background).
- **[Trade-off] TradingView widget stays mounted while hidden** → keeps memory usage of one iframe while on other tabs; accepted to avoid reload cost and lost chart state.
- **[Risk] Stale context** (trades deleted/merged/edited so they no longer match the filter after the list was loaded) → **Mitigation**: the list refresh updates stored pages; on the detail page a navigated-to ID that returns 404 shows the existing "Trade not found" state with `Back to Trades`. A trade edited out of the filter stays navigable until the list is reloaded — accepted.
- **[Risk] Stale context from an earlier list visit used for a trade opened elsewhere** → **Mitigation**: navigation is only offered if the trade ID is in the stored pages, and the position tooltip names the list source (view name / filtered / all), so the user sees which list is being stepped through.
- **[Risk] Arrow keys conflict with focused widgets** (TradingView iframe, Radix menus, the check-in style lightbox arrows) → **Mitigation**: iframe focus does not bubble key events to the page; menus/dialogs are excluded by role check; the trade lightbox has no arrow navigation today.
- **[Trade-off] `router.replace`** → browser Back skips intermediate trades and returns to the list; users who expect Back to go to the previous trade use `←` instead.

## Migration Plan

Frontend-only; ships with the next frontend build. Rollback = revert the commit. No data migration. The `sessionStorage` key is new; stale or malformed values are ignored (parse errors → no context).

## Open Questions

- None blocking. A backend `neighbors` endpoint (Decision 10, Alternative A) can be proposed separately if navigation for deep links becomes a requirement.
