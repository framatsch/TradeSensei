## 1. Trading Log Sidebar — Label Fix & Column Toggle Removal

- [x] 1.1 In `frontend/components/trading-log/TradingLogSidebar.tsx`, rename the "Trades" section heading to "SAVED FILTERS"
- [x] 1.2 Search `frontend/` for any Column Visibility Toggle component or button in the trades table — remove if found

## 2. Checkin Pillar Layout

- [x] 2.1 Create `frontend/app/dashboard/checkins/layout.tsx` — two-column flex row: `CheckinSidebar` (left, ~220px) + `{children}` (right, flex-1)
- [x] 2.2 Modify `DashboardLayout` to hide the global `<aside>` when `pathname.startsWith("/dashboard/checkins")` — consistent with how trades routes suppress it

## 3. CheckinSidebar Component

- [x] 3.1 Create `frontend/components/checkin/CheckinSidebar.tsx` — contains `CheckinMiniCalendar` and view-mode toggle buttons (Timeline / Model Book)
- [x] 3.2 View toggle buttons update the `view` URL param (`timeline` | `modelbook`); active button is highlighted

## 4. CheckinMiniCalendar Component

- [x] 4.1 Create `frontend/components/checkin/CheckinMiniCalendar.tsx` — 7-column CSS grid month view with `<` / `>` month navigation
- [x] 4.2 Fetch checkins for the current month (`date_from` / `date_to` query params on existing list endpoint); derive which days have entries and their regime `color_hex`
- [x] 4.3 Render a 4px colored dot below each day that has a saved check-in, using the regime's `color_hex`
- [x] 4.4 Month navigation updates the `month` URL param (format `YYYY-MM`)
- [x] 4.5 Clicking a day with a check-in navigates to `/dashboard/checkins/{YYYY-MM-DD}`

## 5. useCheckinParams Hook

- [x] 5.1 Create `frontend/hooks/useCheckinParams.ts` — encapsulates `useSearchParams` + `useRouter` exposing: `view`, `setView`, `month`, `setMonth`, `regime`, `setRegime`, `page`, `setPage`, `perPage`, `setPerPage`
- [x] 5.2 `setRegime` clears `page` to 1 automatically; `setMonth` clears `page` to 1 automatically

## 6. Regime Filter Pills

- [x] 6.1 Create `frontend/components/checkin/RegimePills.tsx` — renders one pill per active `MarketRegimeDefinition` using `color_hex` for border styling
- [x] 6.2 Clicking a pill sets `regime` URL param; clicking the active pill clears it
- [x] 6.3 Render `RegimePills` at the top of the main content area in both Timeline and Model Book views

## 7. Timeline View

- [x] 7.1 Create `frontend/components/checkin/TimelineView.tsx` — fetches paginated checkins filtered by `regime` param, renders in reverse-chronological order
- [x] 7.2 Each entry card: left accent border in regime `color_hex`, date heading, regime pill, rendered Markdown (using `react-markdown`), screenshot thumbnails
- [x] 7.3 Thumbnails: `<img loading="lazy" className="max-w-[120px] h-auto object-cover" src={url} />` — never full-res in list
- [x] 7.4 Thumbnail click opens `CheckinLightbox` passing the clicked `url`

## 8. Model Book View

- [x] 8.1 Create `frontend/components/checkin/ModelBookView.tsx` — responsive grid (`grid-cols-3` desktop, `grid-cols-2` tablet)
- [x] 8.2 Each card: top accent border in regime `color_hex`, large thumbnail (`w-full h-48 object-cover`), date + regime label below — NO Markdown text
- [x] 8.3 Collapsible filter panel at top of grid: date range pickers + regime selector — values wired to `useCheckinParams`
- [x] 8.4 Pagination footer: prev/next + page numbers + `per_page` selector (options: 12, 24, 48) — all synced via `useCheckinParams`
- [x] 8.5 Filter changes (regime, date) reset page to 1 via `useCheckinParams`
- [x] 8.6 Thumbnail click opens `CheckinLightbox`

## 9. CheckinLightbox Component

- [x] 9.1 Create `frontend/components/checkin/CheckinLightbox.tsx` — full-screen overlay (`fixed inset-0 bg-black/80 z-50`) rendering the full-resolution image
- [x] 9.2 Close on Escape keydown (`useEffect` + `addEventListener('keydown', ...)`)
- [x] 9.3 Close on backdrop click (click outside the image container)

## 10. Check-in Form — Dynamic Fields

- [x] 10.1 In the check-in create/edit form, fetch active `CheckinFieldDefinition` records
- [x] 10.2 Render a range slider (min: 1, max: 10) for each `field_type === 'integer'` field — value stored in `custom_metrics[field_name]`
- [x] 10.3 Render a toggle switch for each `field_type === 'boolean'` field — value stored in `custom_metrics[field_name]`

## 11. Verification

- [x] 11.1 Verify global sidebar is hidden on all `/dashboard/checkins` routes and `CheckinSidebar` is rendered
- [x] 11.2 Verify mini-calendar renders dots with correct regime colors and month navigation works
- [x] 11.3 Verify Timeline view renders entries with left accent borders in correct `color_hex`
- [x] 11.4 Verify Model Book renders 3-col grid with top accent borders and no Markdown text
- [x] 11.5 Verify Lightbox opens on thumbnail click and closes on Escape / backdrop click
- [x] 11.6 Verify all URL params (`view`, `month`, `regime`, `page`, `per_page`) round-trip correctly on reload
- [x] 11.7 Verify Trading Log sidebar shows "SAVED FILTERS" (not "Trades") and no Column Visibility Toggle exists
