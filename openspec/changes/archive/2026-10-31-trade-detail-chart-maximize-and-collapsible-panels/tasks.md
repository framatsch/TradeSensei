## 1. Mobile Chart Maximize & Restore

- [x] 1.1 Update `frontend/components/trades/MediaChartsCard.tsx` to add `isMaximized` state, a mobile-only (`lg:hidden`) `Maximize chart` / `Restore chart` toggle button in the tab bar when the `Chart` tab is active, and in-place fullscreen overlay classes (`fixed inset-0 z-50 w-screen h-[100dvh] bg-card pb-[env(safe-area-inset-bottom)]`) with `role="dialog"`, `aria-modal="true"`, `aria-label="Maximized trade chart"`.
- [x] 1.2 Add `Escape` key handling and `document.body.style.overflow = "hidden"` scroll lock while `MediaChartsCard` is maximized, and reset `isMaximized` when switching to the `Screenshots` tab.

## 2. Separate Journal Card & Collapsible Panels

- [x] 2.1 Refactor `frontend/components/trades/QualitativeMetadataPanel.tsx` to render two separate collapsible `solid-card` panels (`Qualitative Analysis & Metadata` for Playbook, Tags, Annotations; `Journal` for Markdown preview/editor and Quick Notes import), both expanded by default (`aria-expanded="true"`), hiding collapsed bodies via `hidden`, showing a compact metadata summary badge row when `Qualitative Analysis & Metadata` is collapsed, and preserving the shared desktop and mobile `Unsaved changes` save/cancel bars.
- [x] 2.2 Add a collapsible card wrapper and header (`Quick Notes` with note count badge, expanded by default, body hidden via `hidden` when collapsed) to `frontend/components/notes/NoteList.tsx`.
- [x] 2.3 Add collapsible header toggle (`ChevronDown` / `ChevronRight`, `aria-expanded`, expanded by default, body hidden via `hidden` when collapsed) to `Performance` in `frontend/app/dashboard/trades/[id]/page.tsx` and to `Execution Summary` in `frontend/components/trades/ExecutionSummaryCard.tsx`.

## 3. Tests & Verification

- [x] 3.1 Add unit tests covering mobile chart maximize/restore (`MediaChartsCard.test.tsx`) and collapsible panel behavior + split `Journal` card (`QualitativeMetadataPanel.test.tsx`, `ExecutionSummaryCard.test.tsx`, `NoteList.test.tsx`).
- [x] 3.2 Update/extend Playwright mobile E2E tests in `frontend/tests/specs/trade-detail.spec.ts` to verify maximizing and restoring the chart on `375×812` and collapsing `Qualitative Analysis & Metadata` in the `Journal` tab to bring the `Journal` card into immediate view.
- [x] 3.3 Run frontend typecheck (`npx tsc --noEmit`), unit tests (`npm test`), and Playwright tests to verify zero regressions.
