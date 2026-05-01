## Context

The pillar routing skeleton from `pillar-architecture-trading-log` is complete. The Trading Log pillar (`/dashboard/trades`) has its dedicated layout and sidebar. What remains is:

1. **Trading Log section label fix**: The sidebar "Trades" section must be renamed to "SAVED FILTERS" per the master spec. Additionally, any Column Visibility Toggle that may have been added must be explicitly removed.
2. **Market Check-in Pillar**: The `/dashboard/checkins` route exists but lacks an operative layout. It needs a dedicated `CheckinLayout` with a sidebar (mini-calendar + view toggles), and two distinct view modes: Timeline and Model Book.

Existing APIs available (no new backend needed):
- `GET /api/v1/checkins/` — paginated list of `DailyCheckin`
- `GET /api/v1/checkins/{date}` — single checkin by date
- `GET /api/v1/checkins/market-regimes` — list of `MarketRegimeDefinition` (with `color_hex`)
- `GET /api/v1/checkins/field-definitions` — list of `CheckinFieldDefinition`
- `POST /api/v1/checkins/` — create/update checkin
- `POST /api/v1/checkins/screenshot-upload-url` — presigned S3 URL for screenshots

## Goals / Non-Goals

**Goals:**
- Rename `TradingLogSidebar` "Trades" section label to "SAVED FILTERS".
- Prohibit Column Visibility Toggle in the Trading Log table.
- Create `CheckinLayout` for all `/dashboard/checkins` routes — hides global sidebar, renders `CheckinSidebar` + children.
- `CheckinSidebar`: mini-calendar with regime-color dots, view mode toggles (Timeline / Model Book).
- `TimelineView`: vertical chronological list, text-first, screenshots as inline thumbnails.
- `ModelBookView`: responsive image grid, visual-first, Markdown hidden, collapsible filter panel, pagination.
- `CheckinLightbox`: overlay modal fetching and rendering full-resolution S3 image on click.
- Thumbnail rendering: all `screenshot_urls` in list/grid views render as `<img>` with `?w=320` suffix or CSS-capped dimensions — never full-res.
- URL-sync: `view` (timeline|modelbook), `date` (YYYY-MM), `regime`, `page`, `per_page` reflected in URL params.
- `color_hex` applied to: calendar day dots, active regime pill border, timeline card left border, Model Book card top border.

**Non-Goals:**
- New backend endpoints.
- Mobile/responsive redesign beyond basic grid breakpoints.
- Implementing a real image CDN — thumbnail optimization is achieved via CSS `max-width`/`object-fit` and lazy loading; presigned URL `?w=` param is optional if not supported by S3.

## Decisions

### Decision 1: CheckinLayout mirrors TradingLogLayout pattern
A nested `app/dashboard/checkins/layout.tsx` hides the global sidebar and renders `CheckinSidebar` + `{children}` in a two-column flex row. Consistent with how the Trading Log pillar was isolated.

### Decision 2: Thumbnail optimization via CSS + lazy loading
Full-res images are never loaded in list/grid views. Thumbnails use `<img loading="lazy" className="w-full h-40 object-cover" src={url} />`. The Lightbox is the only place that renders `<img src={url} />` at full size. No CDN transform required; S3 images sized by CSS, browser doesn't download full pixel data beyond viewport rendering — acceptable for this phase.

### Decision 3: Mini-calendar is a client-side custom component
Use a simple month grid (7-col CSS grid, 5-6 rows). Days with checkins are fetched via a lightweight endpoint or derived from a monthly checkin list query. Regime color is applied as a bottom dot (4px circle). Clicking a day navigates to `/dashboard/checkins/{YYYY-MM-DD}`.

### Decision 4: URL-sync via `useCheckinParams` hook
Mirror the `useTradeFilterParams` pattern. Hook encapsulates `useSearchParams` + `useRouter` and exposes `view`, `setView`, `month`, `setMonth`, `regime`, `setRegime`, `page`, `setPage`, `perPage`, `setPerPage`.

### Decision 5: Dynamic form fields driven by CheckinFieldDefinition
The Check-in form reads active `CheckinFieldDefinition` records. `field_type === 'integer'` renders a range slider (1–10). `field_type === 'boolean'` renders a toggle switch. Field values are stored in `custom_metrics: Record<string, number | boolean>`.

## Risks / Trade-offs

- [Mini-calendar requires knowing which dates have checkins for the current month] → Fetch checkins filtered by month on calendar mount; a lightweight query (dates only) is preferable. Use the existing list endpoint with `date_from`/`date_to` params.
- [Lightbox focus trap] → Use a simple `useEffect` + `keydown` listener for Escape key; full a11y focus trap is a stretch goal.
- [Model Book pagination resets on filter change] → Reset page to 1 whenever regime or date filter changes.
