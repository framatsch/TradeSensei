## Why

On mobile viewports (`< lg`), the Trade Detail chart is constrained to a `360px` card, leaving no quick way to inspect price action and execution markers in full screen without opening an external TradingView tab. In addition, the Trade Detail sections (`Performance`, `Execution Summary`, `Qualitative Analysis & Metadata`, `Journal`, and `Quick Notes`) cannot be collapsed, and `Journal` is nested at the bottom of `QualitativeMetadataPanel` below Playbook, Tags, and Annotations—forcing users to scroll past all structured metadata before reading or writing their trade journal.

## What Changes

- **Mobile Chart Maximize / Restore (`< lg`)**: Add a mobile-only (`lg:hidden`) maximize toggle button in the `MediaChartsCard` tab bar (when the `Chart` tab is active) that expands the existing card in-place into a full-viewport modal overlay (`fixed inset-0 z-50 h-[100dvh] w-screen`) and restores it back to normal view via a minimize button or `Escape`, preserving the mounted `TradeChart` / TradingView fallback instance, zoom/pan state, and active interval.
- **Separate `Journal` Card from `Qualitative Analysis & Metadata`**: Split the visual rendering of `QualitativeMetadataPanel` into two distinct cards (`Qualitative Analysis & Metadata` for Playbook, Tags, and Annotations; `Journal` for the Markdown preview/editor and `Import Quick Notes` action) while preserving their shared draft state, desktop Save/Cancel controls, and mobile sticky `Unsaved changes` bar.
- **Collapsible Trade Detail Panels (All Viewports)**: Make the Trade Detail section cards (`Performance`, `Execution Summary`, `Qualitative Analysis & Metadata`, `Journal`, and `Quick Notes`) collapsible on all viewports (`< lg` and `lg+`), all expanded by default, hiding collapsed bodies via CSS (`hidden`) so mounted state and unsaved drafts are never lost.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `trade-detail-mobile-ui`: Add mobile chart maximize/restore behavior, split `Qualitative Analysis & Metadata` and `Journal` into separate cards in the `Journal` pane, and specify collapsible section panels (expanded by default across viewports, preserving DOM state when collapsed).

## Impact

- **Frontend components**:
  - `frontend/components/trades/MediaChartsCard.tsx` (in-place mobile fullscreen state, header toggle button, `Escape` key & body scroll lock, `role="dialog"` / `aria-modal="true"` when maximized)
  - `frontend/components/trades/QualitativeMetadataPanel.tsx` (render `Qualitative Analysis & Metadata` and `Journal` as two separate collapsible cards with compact summary badges when collapsed, sharing draft/save state)
  - `frontend/components/trades/ExecutionSummaryCard.tsx` (collapsible card header, expanded by default)
  - `frontend/components/notes/NoteList.tsx` (wrap Quick Notes in a collapsible `solid-card` with note count badge, expanded by default)
  - `frontend/app/dashboard/trades/[id]/page.tsx` (collapsible `Performance` card, expanded by default)
- **Tests**:
  - Unit tests (`MediaChartsCard`, `QualitativeMetadataPanel`, `ExecutionSummaryCard`, `NoteList`, Trade Detail page)
  - Playwright mobile E2E tests (`frontend/tests/specs/trade-detail.spec.ts`)
- **Backend / API / DB**: None (frontend-only change).
