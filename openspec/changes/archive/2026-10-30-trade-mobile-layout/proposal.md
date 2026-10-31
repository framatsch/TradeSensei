## Why

The `playbook-checkin-document-layout` change gave Playbooks and Market Check-ins a mobile layout with a compact header and segmented tabs (`< lg`), but the two most frequently used views on a phone — the **Trade Detail page** (`/dashboard/trades/[id]`) and the **Trades list** (`/dashboard/trades`) — still render their desktop layout squeezed into a 375px viewport. On the detail page the user scrolls past a ≥400px chart, nine stacked metric rows and an execution summary before reaching the journal, and the execution legs table (up to 16 columns) scrolls horizontally. On the list page a 12-column table scrolls horizontally, the filter panel expands into ~18 stacked inputs, and the bulk-action toolbar overflows. Several controls (journal edit, screenshot delete, note actions) are hover-only and therefore unreachable on touch devices. Independently of the viewport, reviewing a filtered set of trades (e.g. "all losers of last week") requires going back to the list for every single trade, and the `Back to Trades` link drops all filters.

## What Changes

The mobile layout changes apply to viewports below `lg` (`< 1024px`) only; the desktop (`lg+`) layout stays visually and functionally unchanged except for the new Previous/Next navigation row, which applies to all viewports.

- **Trade Detail — Mobile Layout**:
  - Compact **Header Card**: back button, symbol, direction / asset-class / status badges, `⋯` actions menu, one-line open → close timestamp with holding period, and a **KPI strip** (Net P&L, Realized R, Return %).
  - **3-tab segmented switcher** directly below the header, using the same visual pattern as Playbooks/Check-ins: `[ Overview | Journal | Executions (n) ]`.
    - `Overview` (default): Media & Charts card (TradingView / Screenshots), compact 2-column Risk & Performance grid (inline-editable Stop Loss / Take Profit), Execution Summary.
    - `Journal`: Qualitative Analysis & Metadata panel (Playbook, Tags, Annotations, Markdown journal) and Quick Notes. Unsaved changes show a dot on the tab and a sticky bottom Save/Cancel bar.
    - `Executions (n)`: execution legs rendered as stacked cards instead of a table, with a per-card `⋯` action menu.
  - All panes stay mounted (CSS visibility only) so the TradingView widget and unsaved journal input survive tab switches.
  - Conflict / unlinked-execution banners stay above the tabs; the conflict banner's "Review" action switches to the `Executions` tab.
- **Trades List — Mobile Layout**:
  - The table is replaced by a **card list** (`TradeCard`): symbol, direction, asset class, P&L, quantity @ entry → exit, holding period, tags, notes count. Tapping the card opens the trade detail.
  - **Selection mode**: a `Select` toggle in the list toolbar reveals checkboxes; the bulk-action toolbar becomes a **fixed bottom bar** with icon+label actions.
  - **Sort dropdown** replaces sortable column headers.
  - **Filter bottom sheet**: the `Filter (n)` button opens a full-height bottom sheet with tabs `[ Trade | Time | Journal | Account ]` that splits the existing filter fields into groups; saved-view actions move into the sheet footer.
  - Compact pagination (`‹ Prev · Page n · Next ›` plus rows-per-page select).
- **Touch accessibility**: hover-only controls in the trade views (journal edit, screenshot delete/zoom, quick-note actions) become always visible below `lg`.
- **Trade Detail — Previous/Next navigation (all viewports)**:
  - The Trades list stores the current list context (effective filters, sort, page size, list URL, loaded pages with ordered trade IDs and cursors, total) in `sessionStorage`.
  - The Trade Detail page shows `‹ Previous`, a position indicator (`3 / 128`) and `Next ›` that step through that filtered, sorted list — loading the next page on demand at page boundaries. Controls are hidden when the trade was not opened from the list context.
  - Keyboard shortcuts `←` / `→` (ignored while typing, with modifiers, or while a modal/menu/lightbox is open).
  - Confirmation before navigating away from unsaved journal changes.
  - `Back to Trades` restores the stored filters, sort and saved view.

## Capabilities

### New Capabilities
- `trade-detail-mobile-ui`: Mobile (`< lg`) layout of the Trade Detail page — compact header with KPI strip, `Overview | Journal | Executions` segmented switcher with state-preserving panes, execution leg cards, sticky journal save bar, touch-visible controls.
- `trade-list-mobile-ui`: Mobile (`< lg`) layout of the Trades list — trade card list, selection mode with fixed bottom bulk-action bar, sort dropdown, tabbed filter bottom sheet, compact pagination.
- `trade-detail-navigation`: Session-stored trade list context, Previous/Next navigation with position indicator on the Trade Detail page (all viewports), `←`/`→` keyboard shortcuts, unsaved-changes guard, filter-restoring `Back to Trades`.

### Modified Capabilities
<!-- None: no existing spec defines layout requirements for the trade detail or trade list views. -->

## Impact

- **Frontend Components**:
  - `frontend/app/dashboard/trades/[id]/page.tsx`
  - `frontend/app/dashboard/trades/TradesPageClient.tsx`
  - `frontend/components/trades/TradeTable.tsx`, `TradeRow.tsx`, new `TradeCard.tsx`
  - `frontend/components/trades/TradeFilterBar.tsx`, new `TradeFilterSheet.tsx`
  - `frontend/components/trades/BulkActionToolbar.tsx`
  - `frontend/components/trades/ExecutionLegsTable.tsx`, new `ExecutionLegCard.tsx`
  - `frontend/components/trades/QualitativeMetadataPanel.tsx`, `MediaChartsCard.tsx`, `frontend/components/notes/NoteList.tsx` (touch visibility, sticky save bar)
  - New `frontend/lib/tradeListContext.ts`, `frontend/hooks/useTradeNavigation.ts`, `frontend/components/trades/TradeNavControls.tsx`
- **Tests**:
  - `frontend/__tests__/app/dashboard/trades/TradeDetailPage.test.tsx`
  - `frontend/__tests__/components/trades/` (TradeRow, TradeFilterBar, new TradeCard / TradeFilterSheet tests)
  - `frontend/tests/specs/trade-detail.spec.ts`, `trades.spec.ts` (mobile viewport 375×812 cases, Previous/Next + keyboard navigation)
- **Backend / API**: No backend, schema, or endpoint changes.
