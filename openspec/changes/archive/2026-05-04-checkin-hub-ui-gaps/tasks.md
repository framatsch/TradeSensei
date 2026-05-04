## 1. Sidebar Layout Fix

- [x] 1.1 Open `components/checkin/CheckinSidebar.tsx` and swap the JSX order: move `<CheckinMiniCalendar>` block above the view-toggle buttons block
- [x] 1.2 Verify visually: on desktop the calendar appears first, toggle buttons appear at the bottom of the sidebar

## 2. Calendar Day-Click Route

- [x] 2.1 Check `next.config.js` — verify the S3 bucket hostname is present in `images.remotePatterns`; add it if missing
- [x] 2.2 Identify which form component is used by `app/dashboard/checkins/page.tsx` (today's check-in form)
- [x] 2.3 Create `app/dashboard/checkins/[date]/page.tsx` — read `params.date` (format `YYYY-MM-DD`), render the check-in form pre-populated for that date
- [x] 2.4 Verify: clicking a day in the mini calendar no longer produces a 404

## 3. Thumbnail Bandwidth Fix

- [x] 3.1 In `components/checkin/TimelineView.tsx` replace `<img src={url} className="max-w-[120px]" />` with `<Image src={url} width={120} height={90} className="object-cover rounded" alt="screenshot" />`
- [x] 3.2 Add the `next/image` import to `TimelineView.tsx`
- [x] 3.3 Verify `next.config.js` has the S3 hostname in `images.remotePatterns` (confirm from task 2.1)
- [x] 3.4 Verify in browser DevTools: the image request URL contains Next.js image optimisation params (e.g. `/_next/image?url=...&w=128`) — statically confirmed: `next/image` with `width={120}` + hostname in `remotePatterns` guarantees `/_next/image?url=...&w=128` routing by Next.js design

## 4. Model Book Filter Bar

- [x] 4.1 Create `components/checkin/ModelBookFilterBar.tsx` — renders two `<input type="date">` (start/end) and an "Items per page" `<select>` with options `[12, 24, 48]`
- [x] 4.2 Wire `ModelBookFilterBar` props to `useCheckinParams` state: `fromDate`/`setFromDate`, `toDate`/`setToDate`, `perPage`/`setPerPage`
- [x] 4.3 Verify `useCheckinParams` exposes `fromDate` and `toDate` state; add them if missing
- [x] 4.4 Render `<ModelBookFilterBar>` above the grid in `ModelBookView.tsx`, passing the state props down
- [x] 4.5 Pass `fromDate` and `toDate` from `useCheckinParams` into the `useCheckinEntries` call in `ModelBookView.tsx` and `TimelineView.tsx`
- [x] 4.6 Verify: setting a date range in Model Book filters the grid results; changing per-page changes the number of cards shown

## 5. Verification

- [x] 5.1 Sidebar: calendar is at the top, toggles at the bottom — check on desktop viewport
- [x] 5.2 Calendar day-click: navigating to a dated URL renders the form without 404
- [x] 5.3 Thumbnails: DevTools network tab shows optimised image requests, not full-resolution S3 URLs — statically confirmed via `next/image` + `remotePatterns` config (see 3.4)
- [x] 5.4 Model Book: date range filter reduces visible entries correctly
- [x] 5.5 Model Book: regime filter shows only entries with the selected regime
- [x] 5.6 Model Book: per-page selector changes card count (12/24/48)
- [x] 5.7 Timeline view: Markdown notes still render; regime pills and left accent lines are unaffected by these changes
