## 1. Trade Detail — Header & Segmented Switcher

- [x] 1.1 Create `components/trades/TradeMobileHeader.tsx` (`lg:hidden`): row 1 icon-only back button, symbol + split icon, slot for compact nav controls (filled in 6.4), Radix `⋯` menu (`Correct Trade…`, `Merge with…`); row 2 direction / asset-class / status / manually-edited badges; row 3 `opened → closed · holding` line with slot for the position indicator; 3-column KPI strip (P&L, Realized R, Return %) with `—` fallbacks
- [x] 1.2 In `app/dashboard/trades/[id]/page.tsx`: hide the existing back link and desktop header below `lg` (`hidden lg:flex` / `hidden lg:block`), render `TradeMobileHeader` with the already-computed values
- [x] 1.3 Add `mobileTab` state (`overview` | `journal` | `executions`, default `overview`) and the sticky segmented switcher (`role="tablist"`, same classes as `PlaybookEditorClient`), with `Executions (n)` count of non-deleted legs and a dot indicator on `Journal` when dirty
- [x] 1.4 Group page sections into three panes toggled via `hidden lg:block`; keep desktop order and grid unchanged on `lg+`
- [x] 1.5 Make the conflict banner `onReview` switch to the `executions` tab before scrolling to `#executions-table`

## 2. Trade Detail — Overview & Journal Panes

- [x] 2.1 Set `MediaChartsCard` min height to `360px` below `lg` (keep `lg:min-h-[520px]`)
- [x] 2.2 Render the Performance card metrics as a 2-column grid below `lg` and hide `Realized R`, `Return %`, `Holding Period` rows below `lg` (`hidden lg:flex`)
- [x] 2.3 Add optional `onDirtyChange` prop to `QualitativeMetadataPanel`; wire it to the `Journal` tab dot
- [x] 2.4 Render the panel's Save/Cancel controls as `hidden lg:flex` in the header and as a fixed bottom bar (`lg:hidden`, `z-30`, safe-area padding) while dirty; add bottom padding to the pane while the bar is visible
- [x] 2.5 Make hover-only controls touch-visible below `lg` (`opacity-100 lg:opacity-0 lg:group-hover:opacity-100`) in `QualitativeMetadataPanel` (journal edit), `MediaChartsCard` (screenshot delete/zoom) and `NoteList` (note actions)

## 3. Trade Detail — Execution Leg Cards

- [x] 3.1 Extract `hooks/useExecutionLegEditor.ts` from `ExecutionRow` (draft state, save/cancel, delete confirm, restore, error message, `canSplit`, `canLinkBroker`); refactor `ExecutionRow` to use it with unchanged markup
- [x] 3.2 Create `components/trades/ExecutionLegCard.tsx`: read view (side badge, qty @ price with split indicator, executed-at, commission, P&L, origin + lineage badges, combo/option extra fields, conflict styling, deleted opacity + `Restore`) and Radix `⋯` menu with the same entries/conditions as the row menu
- [x] 3.3 Implement the card's stacked edit form (direction toggle, executed-at, qty, price, commission, P&L, Save/Cancel, error message) via `useExecutionLegEditor`
- [x] 3.4 In `ExecutionLegsTable`: render table as `hidden lg:table` and the card list as `lg:hidden` from the same `timelineItems` (corporate actions as full-width dividers); expanded by default below `lg`; header controls wrap without overflow at 375px

## 4. Trades List — Cards, Sort, Pagination

- [x] 4.1 Create `components/trades/TradeCard.tsx` (4 rows per spec, tappable link to detail, notes badge toggling `QuickNoteInput` without navigation, checkbox in selection mode)
- [x] 4.2 In `TradeTable`: wrap the table in `hidden lg:block`, add `lg:hidden` card list (`data-testid="trade-card-list"`) from the same `trades`, selection handlers, empty/loading/error states
- [x] 4.3 Add the mobile list toolbar to `TradeTable`: sort select (8 options mapped to `sort_by` / `sort_dir`, reflecting current sort) and `Select` / `Done` toggle with `Select all on page`
- [x] 4.4 Add `selectionMode` state: card tap toggles selection in selection mode; `Done` clears selection via `onSelectionChange`
- [x] 4.5 Render the pagination footer in two rows below `lg` with ≥ 40px touch targets; desktop footer unchanged
- [x] 4.6 In `TradesPageClient`: hide the page subtitle below `lg`, keep title + `New Trade` on one row at 375px

## 5. Trades List — Bulk Bar & Filter Sheet

- [x] 5.1 In `BulkActionToolbar`: keep current markup as `hidden lg:flex`, add fixed-bottom `lg:hidden` variant (count, icon+label `Merge` [≥2], `Playbook`, `Tags`, `Delete`, safe-area padding); add list bottom padding while visible
- [x] 5.2 Refactor `TradeFilterBar` field JSX into `renderField(key)` + `FILTER_GROUPS` (`trade`, `time`, `journal`, `account`) + `countActiveFilters(filters, keys?)`; desktop panel output and order unchanged
- [x] 5.3 Create `components/trades/TradeFilterSheet.tsx` on `@radix-ui/react-dialog`: bottom-anchored, `max-h-[90dvh]`, close button/overlay/`Esc`, tab row with per-group active counts, scrollable body rendering one group, footer with saved-view actions, `Clear all`, `Show results`
- [x] 5.4 Below `lg`, replace the inline panel toggle with the trigger row (`Filter (n)`, active view name, `Clear`) opening `TradeFilterSheet`; verify `AccountMultiSelect` / `SymbolTagInput` dropdowns are not clipped inside the sheet (inline variant if needed)
- [x] 5.5 Assert every desktop filter field key is assigned to exactly one group (unit test over `FILTER_GROUPS`)

## 6. Trade Detail — Previous/Next Navigation (all viewports)

- [x] 6.1 Create `lib/tradeListContext.ts`: `TradeListContext` type, `readTradeListContext()` (returns `null` on missing/malformed JSON or SSR), `writeTradeListContext()`, `upsertPage()` / `isSameQuery()` helpers; key `tradesensei.tradeListContext` in `sessionStorage`
- [x] 6.2 In `TradeTable` (+ props from `TradesPageClient`: `listQuery`, `viewName`): write the context whenever page data arrives — replace on query change, upsert page at `cursorStack.length - 1` otherwise, store `total` and `nextCursor`
- [x] 6.3 Create `hooks/useTradeNavigation.ts`: locate the trade in the context (portfolio check), derive `prevId` / `nextId` / `position` / `total` / `sourceLabel` / `backHref`, fetch the next page on demand at the last stored ID via `useTrades` with stored params and append it, `goPrev` / `goNext` with `router.replace` and dirty-confirm
- [x] 6.4 Create `components/trades/TradeNavControls.tsx` (`desktop` and `compact` variants, disabled/loading states, tooltips `Previous: <symbol> (←)` / `Next: <symbol> (→)`, position tooltip with source); render the desktop variant in a nav row next to `Back to Trades` (`hidden lg:flex`) and the compact variant in `TradeMobileHeader`; render nothing when `available` is false
- [x] 6.5 Point desktop and mobile `Back to Trades` to `backHref` (stored `listQuery`, fallback `/dashboard/trades`)
- [x] 6.6 Add the `ArrowLeft` / `ArrowRight` `keydown` handler to the trade detail page with all exclusions (editable targets, modifiers, `defaultPrevented`, open page modals, `[role="dialog"]` / `[role="menu"]` / `[aria-modal="true"]`); add `role="dialog" aria-modal="true"` to the `MediaChartsCard` lightbox
- [x] 6.7 Wire `QualitativeMetadataPanel` `onDirtyChange` (from 2.3) into `useTradeNavigation` so navigation asks `Discard unsaved changes to this trade?` when dirty

## 7. Tests

- [x] 7.1 Update `__tests__/app/dashboard/trades/TradeDetailPage.test.tsx` for duplicated header/panes (scope queries with `within`); add tests for tab switching, preserved journal draft, `Executions (n)` count, conflict-review tab switch
- [x] 7.2 Add unit tests for `TradeMobileHeader` (KPI values and `—` fallbacks, actions menu) and `ExecutionLegCard` (read view, menu conditions, edit/save, restore)
- [x] 7.3 Add unit tests for `TradeCard` (navigation, notes badge, combo direction hidden, selection mode) and update `TradeRow.test.tsx` / `TradesPageClient.showOpenTrades.test.tsx` for dual rendering
- [x] 7.4 Add unit tests for `TradeFilterSheet` (tab counts, live apply, `Clear all`, saved-view actions) and update `TradeFilterBar.test.tsx`
- [x] 7.5 Add unit tests for `tradeListContext` (replace vs. upsert, malformed JSON) and `useTradeNavigation` (within page, previous across page boundary without request, next across boundary with fetch, first/last disabled, portfolio mismatch, ID not in context, position `25 / 128`, dirty confirm cancel)
- [x] 7.6 Add unit tests for the keyboard handler (arrows navigate; ignored in input/textarea, with modifiers, with open dialog/lightbox/modal)
- [x] 7.7 Add Playwright cases: mobile (`375×812`) in `tests/specs/trade-detail.spec.ts` and `tests/specs/trades.spec.ts` (no horizontal overflow, tab switching, leg card edit, card tap → detail, sort select, selection + bulk bar, filter sheet); desktop + mobile navigation flow (filter list → open trade → `→` / `Next` across a page boundary → `Back to Trades` restores filter; deep link shows no nav controls)
- [x] 7.8 Run `npm run lint`, `npx tsc --noEmit` and the frontend unit test suite; all green

## 8. Review & Docs

- [x] 8.1 Capture screenshots at `375×812` and `1440×900` for `/dashboard/trades` (list, selection mode, filter sheet) and `/dashboard/trades/[id]` (all three tabs, dirty journal bar, nav row) and run the `ui-visual-check` skill; fix CRITICAL/WARNING findings; confirm desktop screenshots are unchanged apart from the nav row
- [x] 8.2 Run `code-reviewer` on the change
- [x] 8.3 Document the `←` / `→` shortcuts and list-context behavior in the user guide via `docs-writer`
- [x] 8.4 Add an `[Unreleased]` CHANGELOG entry via `changelog-writer`
