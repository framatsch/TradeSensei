## Context

The Check-in Pillar lives at `/dashboard/checkins` with a persistent sidebar (`CheckinSidebar.tsx`), a `CheckinsPageClient.tsx` orchestrator, and two view components: `TimelineView.tsx` and `ModelBookView.tsx`. The sidebar currently renders view-toggle buttons first and the mini calendar second — the reverse of the spec. The `ModelBookView.tsx` renders a grid and pagination but has no date range filter UI and no per-page selector despite the state existing in `useCheckinParams`. Thumbnail images are rendered with `<img>` tags at 120px CSS width but fetch full-resolution files. The mini calendar routes to `/dashboard/checkins/YYYY-MM-DD` but no such dynamic route exists.

**Existing assets to reuse:**
- `components/checkin/CheckinMiniCalendar.tsx` — mini calendar, regime dot rendering — keep as-is
- `useCheckinParams` hook — already has `perPage`, `setPerPage`, `regimeFilter`, `setRegimeFilter`, `page`, `setPage`
- `useCheckinEntries` hook — already accepts `fromDate`, `toDate`, `limit`, `cursor`
- `components/checkin/RegimePills.tsx` — regime filter pills — reuse in Model Book filter bar
- `app/dashboard/checkins/page.tsx` — existing check-in form page for today

## Goals / Non-Goals

**Goals:**
- Fix sidebar layout order (calendar top, toggles bottom)
- Add Model Book date range filter + dedicated filter panel
- Add per-page selector UI in Model Book
- Fix thumbnail loading to not fetch full-resolution images
- Create `/dashboard/checkins/[date]` dynamic route

**Non-Goals:**
- Redesigning the check-in entry form
- Adding server-side image resizing infrastructure
- Changing the Timeline view's filter behaviour (regime filter stays shared)
- Cursor-based pagination refactor (out of scope — existing page/cursor hybrid stays)

## Decisions

### D1: Sidebar order fix — simple DOM reorder in `CheckinSidebar.tsx`

**Decision:** Move the `<CheckinMiniCalendar>` JSX block above the view-toggle buttons block in `CheckinSidebar.tsx`.

**Rationale:** Pure visual reorder, no logic change needed. Zero risk.

### D2: Thumbnail bandwidth fix — Next.js `<Image>` with explicit dimensions

**Decision:** Replace `<img src={url} className="max-w-[120px]" />` with `<Image src={url} width={120} height={90} className="object-cover" />` in `TimelineView.tsx`. This causes Next.js image optimisation to serve a resized variant at 120px instead of the original file.

**Alternatives considered:**
- CDN query param (`?w=120`): only works if images are behind a CDN that supports it — not guaranteed for S3 presigned URLs.
- Keep `<img>` + accept bandwidth waste: rejected — explicit spec requirement.

**Caveat:** Next.js `<Image>` requires the image hostname to be in `next.config.js` `images.remotePatterns`. A config entry for the S3 bucket hostname must be added or verified.

### D3: Model Book filter panel — new `ModelBookFilterBar` component

**Decision:** Create `components/checkin/ModelBookFilterBar.tsx` with a date-range picker (two `<input type="date">`) and the existing `RegimePills` component. Render it above the grid in `ModelBookView.tsx`. Wire to `useCheckinParams`'s existing `fromDate`/`toDate`/`regimeFilter` state.

**Rationale:** Keeps the Timeline view's existing shared `RegimePills` placement unchanged. The Model Book gets its own dedicated panel matching the spec mockup.

### D4: Per-page selector — inline `<select>` in `ModelBookView.tsx`

**Decision:** Add a `<select>` with options `[12, 24, 48]` next to the filter bar header, wired to `setPerPage`. Default remains 12.

**Rationale:** The state already exists. This is purely a UI binding task.

### D5: `/dashboard/checkins/[date]` route — renders the check-in form for a specific date

**Decision:** Create `app/dashboard/checkins/[date]/page.tsx` that reads the `date` param (format `YYYY-MM-DD`) and renders the existing check-in form pre-populated with that date. Reuse whatever form component is used by `app/dashboard/checkins/page.tsx`.

**Rationale:** The mini calendar already routes to this path on day-click. Without this route, clicking any calendar day produces a 404.

## Risks / Trade-offs

- **[Risk] Next.js `<Image>` hostname not whitelisted** → Mitigation: check `next.config.js` `images.remotePatterns` and add S3 bucket hostname if missing.
- **[Risk] `[date]` page renders with no check-in data** → Expected behaviour — show empty form ready for input.
- **[Risk] Model Book filter bar adds visual complexity** → Mitigation: keep it minimal — two date inputs + regime pills, consistent with the existing filter bar style.

## Open Questions

- Should the `[date]` route show a read-only view of an existing check-in, or always show the editable form? (Assumption: editable form, same as today's check-in page)
- Should the date range filter in Model Book also apply to the Timeline view, or remain isolated? (Assumption: isolated to Model Book per spec)
