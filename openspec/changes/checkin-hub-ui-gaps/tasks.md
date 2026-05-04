## 1. Sidebar Layout Fix

- [ ] 1.1 Open `components/checkin/CheckinSidebar.tsx` and swap the JSX order: move `<CheckinMiniCalendar>` block above the view-toggle buttons block
- [ ] 1.2 Verify visually: on desktop the calendar appears first, toggle buttons appear at the bottom of the sidebar

## 2. Calendar Day-Click Route

- [ ] 2.1 Check `next.config.js` — verify the S3 bucket hostname is present in `images.remotePatterns`; add it if missing
- [ ] 2.2 Identify which form component is used by `app/dashboard/checkins/page.tsx` (today's check-in form)
- [ ] 2.3 Create `app/dashboard/checkins/[date]/page.tsx` — read `params.date` (format `YYYY-MM-DD`), render the check-in form pre-populated for that date
- [ ] 2.4 Verify: clicking a day in the mini calendar no longer produces a 404

## 3. Thumbnail Bandwidth Fix

- [ ] 3.1 In `components/checkin/TimelineView.tsx` replace `<img src={url} className="max-w-[120px]" />` with `<Image src={url} width={120} height={90} className="object-cover rounded" alt="screenshot" />`
- [ ] 3.2 Add the `next/image` import to `TimelineView.tsx`
- [ ] 3.3 Verify `next.config.js` has the S3 hostname in `images.remotePatterns` (confirm from task 2.1)
- [ ] 3.4 Verify in browser DevTools: the image request URL contains Next.js image optimisation params (e.g. `/_next/image?url=...&w=128`)

## 4. Model Book Filter Bar

- [ ] 4.1 Create `components/checkin/ModelBookFilterBar.tsx` — renders two `<input type="date">` (start/end) and `<RegimePills>` side by side, plus an "Items per page" `<select>` with options `[12, 24, 48]`
- [ ] 4.2 Wire `ModelBookFilterBar` props to `useCheckinParams` state: `fromDate`/`setFromDate`, `toDate`/`setToDate`, `regimeFilter`/`setRegimeFilter`, `perPage`/`setPerPage`
- [ ] 4.3 Verify `useCheckinParams` exposes `fromDate` and `toDate` state; add them if missing
- [ ] 4.4 Render `<ModelBookFilterBar>` above the grid in `ModelBookView.tsx`, passing the state props down
- [ ] 4.5 Pass `fromDate` and `toDate` from `useCheckinParams` into the `useCheckinEntries` call in `CheckinsPageClient.tsx`
- [ ] 4.6 Verify: setting a date range in Model Book filters the grid results; changing per-page changes the number of cards shown

## 5. Verification

- [ ] 5.1 Sidebar: calendar is at the top, toggles at the bottom — check on desktop viewport
- [ ] 5.2 Calendar day-click: navigating to a dated URL renders the form without 404
- [ ] 5.3 Thumbnails: DevTools network tab shows optimised image requests, not full-resolution S3 URLs
- [ ] 5.4 Model Book: date range filter reduces visible entries correctly
- [ ] 5.5 Model Book: regime filter shows only entries with the selected regime
- [ ] 5.6 Model Book: per-page selector changes card count (12/24/48)
- [ ] 5.7 Timeline view: Markdown notes still render; regime pills and left accent lines are unaffected by these changes
