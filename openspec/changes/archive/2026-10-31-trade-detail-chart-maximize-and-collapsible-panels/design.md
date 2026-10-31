## Context

Following `2026-10-30-trade-mobile-layout`, the Trade Detail page (`/dashboard/trades/[id]`) has a compact mobile header and a 3-tab segmented switcher (`Overview`, `Journal`, `Executions`). Two usability gaps remain:
1. **Chart height on mobile (`< lg`)**: `MediaChartsCard` renders with `min-h-[360px]`. While `TradeChart` already uses a `ResizeObserver` on its container (`frontend/components/charts/TradeChart.tsx`) and `TradingViewFallback` uses `autosize: true`, there is no way on mobile to expand the chart to full screen and return to the inline card.
2. **Long vertical scrolling inside panes**: In the `Journal` tab, `QualitativeMetadataPanel` bundles Playbook, Tags (Taxonomies), Annotations, and the Markdown `Journal` inside a single card, followed by `NoteList` (`Quick Notes`). Users with multiple tags or annotations must scroll past all structured fields to reach the `Journal` editor. Similarly, `Performance`, `Execution Summary`, and `Quick Notes` cannot be collapsed when not needed.

Constraints: Frontend-only, no new dependencies (`lucide-react` already provides `Maximize2`, `Minimize2`, `ChevronDown`, `ChevronRight`), semantic tokens only (no `dark:` modifiers in new code).

## Goals / Non-Goals

**Goals:**
- Allow maximizing the `Chart` tab of `MediaChartsCard` to a full-viewport overlay on mobile (`< lg`) and restoring it without unmounting `TradeChart` or losing zoom/pan/interval state.
- Split `QualitativeMetadataPanel` visually into two distinct collapsible cards (`Qualitative Analysis & Metadata` and `Journal`) while keeping their shared draft/save lifecycle in one component.
- Make all Trade Detail panels (`Performance`, `Execution Summary`, `Qualitative Analysis & Metadata`, `Journal`, `Quick Notes`) collapsible on all viewports (`< lg` and `lg+`), starting expanded by default.

**Non-Goals:**
- Chart maximize button on desktop (`lg+`), where the 2/3-width `520px` card already provides sufficient space.
- Persisting panel collapse state across sessions or backend user settings.
- Changing any backend endpoints, schemas, or mutation flows.

## Decisions

### 1. In-place CSS fullscreen for `MediaChartsCard` instead of a React Portal
- **Decision**: Keep a boolean `isMaximized` state inside `MediaChartsCard`. When `isMaximized` is `true`, replace the card's outer sizing classes (`solid-card flex flex-col h-full min-h-[360px] lg:min-h-[520px]`) with `fixed inset-0 z-50 flex flex-col bg-card w-screen h-[100dvh] pb-[env(safe-area-inset-bottom)]` and attach `role="dialog" aria-modal="true" aria-label="Maximized trade chart"`.
- **Rationale**: A portal or separate modal component would unmount and remount `TradeChart` (or the TradingView iframe), resetting the user's candle zoom/scroll position, selected interval (`1h`/`4h`/`1d`), display option toggles, and triggering a redundant market-data fetch. Because `TradeChart` already observes `chartContainerRef.current` with `ResizeObserver`, toggling CSS classes on the ancestor container resizes the canvas seamlessly in both directions.
- **Alternative**: Render a second `<TradeChart />` inside `@radix-ui/react-dialog`. Rejected due to state loss and duplicate network/canvas overhead.

### 2. Mobile-only toggle in `MediaChartsCard` tab bar + `Escape` / scroll lock
- **Decision**: Render the maximize/restore icon button (`Maximize2` / `Minimize2`) on the right side (`ml-auto mr-2`) of the `MediaChartsCard` tab bar with `lg:hidden`, visible only when `activeTab === "tradingview"`. When `isMaximized` is active:
  - Lock `document.body.style.overflow = "hidden"` and restore it on cleanup.
  - Listen for `Escape` on `window` to set `isMaximized(false)`.
  - Reset `isMaximized(false)` if the viewport crosses `lg` or if the user switches to the `Screenshots` tab.
  - Because `page.tsx` already skips `ArrowLeft` / `ArrowRight` trade navigation when `document.querySelector('[role="dialog"], [role="menu"], [aria-modal="true"]')` matches, adding `role="dialog" aria-modal="true"` on the maximized card automatically prevents accidental trade switching while panning the chart.

### 3. Visual split of `QualitativeMetadataPanel` into two cards with shared state
- **Decision**: Keep `QualitativeMetadataPanel` as a single component owning `draftPlaybookId`, `draftTaxonomyIds`, `draftAnnotations`, `draftJournal`, `importedNoteIds`, `isDirty`, `handleSave`, and `handleCancel`, but render a `<div className="space-y-6">` containing two `solid-card` sections:
  1. **`Qualitative Analysis & Metadata` card**: Playbook, Tags (`TaxonomySelector`), and Annotations (`AnnotationInputs`). Header includes the collapse toggle (`ChevronDown` / `ChevronRight`), a compact summary badge row when collapsed (e.g., playbook name/count, tag count, annotation count), and the desktop `Unsaved changes` / `Cancel` / `Save` controls when dirty.
  2. **`Journal` card**: Markdown preview/write toggle, `Edit` icon button, `Import Quick Notes` button, and the preview/textarea body. Header includes the collapse toggle (`ChevronDown` / `ChevronRight`) and, if the metadata card's desktop save controls are out of view or either card is dirty, the desktop `Unsaved changes` / `Cancel` / `Save` controls remain accessible in the `Qualitative Analysis & Metadata` header (plus in the `Journal` card header if only journal or metadata is being edited on desktop, or shared cleanly). To avoid duplicate `Save` buttons in desktop DOM tests, the desktop `Unsaved changes` + `Cancel` + `Save` bar renders in the `Qualitative Analysis & Metadata` card header when expanded, or in a shared sticky/top bar of `QualitativeMetadataPanel` (`hidden lg:flex`). Keeping a single desktop action bar and a single mobile bottom bar preserves existing unit and E2E selectors (`getByRole("button", { name: "Save" })`).
- **Rationale**: Zero duplication of mutation or dirty-tracking logic, no prop drilling to `page.tsx`, and existing save/cancel flows work identically.

### 4. Consistent collapsible card pattern (`hidden` body, default expanded)
- **Decision**: Each collapsible panel (`Performance` in `page.tsx`, `ExecutionSummaryCard`, `Qualitative Analysis & Metadata`, `Journal`, and `NoteList`) uses a local `const [collapsed, setCollapsed] = useState(false)` state (default `false` = expanded). The card header renders a `<button type="button" aria-expanded={!collapsed} onClick={() => setCollapsed((c) => !c)}>` with `ChevronDown` / `ChevronRight` (matching `ExecutionLegsTable`). The card body wrapper toggles `className={collapsed ? "hidden" : "..."}`.
- **Rationale**: Using `hidden` instead of conditional rendering keeps child inputs and hooks mounted so unsaved edits in `InlineNumberField`, `QualitativeMetadataPanel`, or `NoteList` are never lost when collapsing and re-expanding a panel.

## Risks / Trade-offs

- **[Risk] Parent stacking context clips `fixed inset-0` on `MediaChartsCard`** → **Mitigation**: Verify that no ancestor of `MediaChartsCard` in `app/dashboard/trades/[id]/page.tsx` sets `transform`, `filter`, or `perspective`. (`#trade-overview-pane` and the grid only use `space-y-6` and `grid`.)
- **[Risk] Existing unit tests query `Qualitative Analysis & Metadata` or `NoteList` structure** → **Mitigation**: All panels default to expanded (`collapsed = false`), so every field and button remains visible on initial render without changing existing test setup.
- **[Risk] Duplicate `Save` buttons if rendered in both split cards on desktop** → **Mitigation**: Render the desktop `Unsaved changes` + `Cancel` / `Save` controls once per `QualitativeMetadataPanel` instance (and the mobile fixed bottom bar once), keeping button queries unambiguous.
