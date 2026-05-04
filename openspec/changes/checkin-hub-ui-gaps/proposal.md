## Why

The Market Check-in Pillar was partially implemented but deviates from the specified UI layout and is missing several features. An audit against the canonical spec revealed: the sidebar layout order is inverted (calendar and toggles are swapped), three Model Book features are absent (date range filter, per-page selector UI, and a dedicated filter panel), thumbnail images are displayed at 120px visually but downloaded at full resolution wasting bandwidth, and clicking a day in the mini calendar navigates to a dynamic route (`/dashboard/checkins/[date]`) that does not exist. These gaps prevent the Check-in pillar from matching the spec and degrade UX and performance.

## What Changes

- **FIX** `CheckinSidebar.tsx` — swap order: mini calendar at top, view toggle buttons at bottom
- **ADD** date range filter UI in Model Book view — feeds `fromDate`/`toDate` into `useCheckinEntries` (hook already supports these params)
- **ADD** per-page selector UI in `ModelBookView.tsx` — wires existing `setPerPage` state to a `<select>` element
- **FIX** thumbnail loading — use `Next.js <Image>` with explicit `width={120}` instead of `<img>` to prevent full-resolution downloads; or append a `?w=120` resize hint if images are served via a CDN
- **ADD** `app/dashboard/checkins/[date]/page.tsx` — dynamic route for day-click navigation from the mini calendar; renders the check-in form for that specific date
- **REFACTOR** regime filter placement — in Model Book view, render a dedicated filter bar (Date Range + Regime) above the grid; in Timeline view keep the existing `RegimePills` placement

## Capabilities

### New Capabilities

- `checkin-modelbook-filters`: Date range + regime filter panel dedicated to the Model Book view, with per-page selector

### Modified Capabilities

- `checkin-hub-ui`: Sidebar layout order fix (calendar top, toggles bottom); thumbnail bandwidth fix; broken calendar day-click route; Model Book filter and pagination UI completion

## Impact

- **Files modified:** `components/checkin/CheckinSidebar.tsx`, `components/checkin/ModelBookView.tsx`, `components/checkin/TimelineView.tsx`, `app/dashboard/checkins/CheckinsPageClient.tsx`
- **Files created:** `app/dashboard/checkins/[date]/page.tsx`, dedicated filter bar component for Model Book
- **No backend changes required** — `useCheckinEntries` already accepts `fromDate`, `toDate`, `limit` params
- **No API client regeneration needed**
