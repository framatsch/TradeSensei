## 1. Pillar Routing — Isolate Trading Log Layout

- [x] 1.1 Create `frontend/app/dashboard/trades/layout.tsx` as a nested layout that renders a two-column flex row: `TradingLogSidebar` (left) + `{children}` (right, flex-1)
- [x] 1.2 Modify `DashboardLayout` to suppress the global `<aside>` when `pathname.startsWith("/dashboard/trades")` — the main content div should expand to full width on trades routes

## 2. Trading Log Operative Sidebar Component

- [x] 2.1 Create `frontend/components/trading-log/TradingLogSidebar.tsx` — a sidebar with two sections: "ACTIONS" and "Trades"
- [x] 2.2 Implement Actions section with three buttons: "+ New Trade" (navigates to `/dashboard/trades/new`), "Quick Import" (opens import dialog/page), "CSV Export" (triggers CSV download from current filter state)
- [x] 2.3 Implement Trades section: render saved filter shortcuts using `useSavedTradeFilters()` — system presets first (All Trades, Open Trades, All Winners, All Losers), then user-saved filters
- [x] 2.4 Highlight the active saved filter in the sidebar (match `view_id` URL param or "All Trades" when no param is set)
- [x] 2.5 Wire sidebar filter clicks to update URL params (`view_id` + filter definition params) without page reload

## 3. Filter URL Sync Hook

- [x] 3.1 Create `frontend/hooks/useTradeFilterParams.ts` — extracts filter-to-URL logic from `TradesPageClient` into a standalone hook exposing `filters`, `setFilter(key, value)`, `clearFilters()`, and `savedViewId`
- [x] 3.2 Refactor `TradesPageClient` to use `useTradeFilterParams` instead of inline `useSearchParams` + `useRouter` filter logic

## 4. Collapsible Filter Configurator

- [x] 4.1 Create `frontend/components/trading-log/FilterConfigurator.tsx` — a collapsible panel with a toggle button labeled "▼ Filter Configuration"
- [x] 4.2 Implement filter inputs inside the panel: Ticker/symbol search input, date-from picker, date-to picker, trade status toggles — all wired to `useTradeFilterParams`
- [x] 4.3 Add "Save Filter" button that opens a name prompt and calls the save filter API, then refetches the saved filters list
- [x] 4.4 Integrate `FilterConfigurator` at the top of the trade table in `TradesPageClient`, replacing or wrapping the existing inline filter controls

## 5. Pagination Footer

- [x] 5.1 Add a "Rows per page" dropdown to the trade table footer (options: 25, 50, 100) — value synced to URL param `limit`
- [x] 5.2 Ensure pagination controls (prev/next, page numbers) are visible in the footer when more than one page of results exists

## 6. Reporting Hub — Saved View Sub-links

- [x] 6.1 Check if a `useSavedDashboardViews` / `useReportingViews` hook or query already exists in the frontend; if not, create `frontend/hooks/useSavedDashboardViews.ts` using the existing API client
- [x] 6.2 In `DashboardLayout`, fetch saved dashboard views and render them as sub-links under the "Reporting Hub" nav item when `activeContext === 'portfolio'` and at least one saved view exists
- [x] 6.3 Each sub-link navigates to `/dashboard/reporting?view_id=<id>` and is highlighted when the URL matches

## 7. Bundle Audit — Charting Library Decoupling

- [x] 7.1 Audit `TradesPageClient` and all components in the `trades/` directory for any direct or indirect Recharts/D3 imports and remove them
- [x] 7.2 Verify that the `/dashboard/trades` page does not include the Recharts bundle (check Next.js build output or dev tools network panel)

## 8. Check-in Hub UI — Market Regime Pills, Markdown Editor, Screenshot Upload

- [x] 8.1 Replace the `<select>` dropdown for Market Phase in `checkin/page.tsx` with color-coded pill buttons — one per active `MarketPhaseDefinition`, styled with its `color_hex`, clicking the active pill deselects it
- [x] 8.2 Replace the plain `<textarea>` for Notes with a Markdown editor using `react-markdown` (already installed) — implement a Write/Preview tab toggle; Write tab = raw textarea, Preview tab = rendered Markdown
- [x] 8.3 Create `frontend/components/checkin/ScreenshotUploader.tsx` — file input (accept: image/png, image/jpeg, image/webp), on select: call `POST /api/v1/checkins/screenshot-upload-url`, PUT file directly to presigned URL, append returned public URL to form state
- [x] 8.4 Render uploaded screenshot URLs as thumbnail previews with a remove (×) button in the Check-in form
- [x] 8.5 Handle HTTP 503 from the presigned URL endpoint — show "Screenshot upload unavailable" message and disable the upload input

## 9. Verification

- [x] 9.1 Manually verify the Trading Log sidebar is visible and the global sidebar is hidden on `/dashboard/trades`
- [x] 9.2 Manually verify filter state (ticker, dates, status, saved filter) is reflected in the URL and restored on page reload
- [x] 9.3 Manually verify saved views appear as sub-links under Reporting Hub in the portfolio sidebar
- [x] 9.4 Manually verify the Filter Configurator collapses/expands and the Save Filter button creates a new entry in the sidebar
- [x] 9.5 Manually verify Market Regime pills render with correct colors and selection/deselection works
- [x] 9.6 Manually verify Markdown editor Write/Preview toggle works and renders formatted output
- [x] 9.7 Manually verify screenshot upload flow: select image → upload → thumbnail appears → remove button works
