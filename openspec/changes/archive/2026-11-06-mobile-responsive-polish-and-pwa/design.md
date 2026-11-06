## Context

The recent mobile layout initiatives (`2026-10-11-playbook-active-status-management`, `2026-10-30-playbook-checkin-document-layout`, `2026-10-30-trade-mobile-layout`, and `2026-10-31-trade-detail-chart-maximize-and-collapsible-panels`) established a clear responsive design language across Trade Sensei:
- **Phone (`< sm` / 375px) & Tablet (`sm`–`lg`)**: Card-based lists with a mobile sort dropdown, touch-accessible action buttons (never hover-only), and compact header strips.
- **Desktop (`lg+` / 1024px+)**: Multi-column sortable data tables and split-pane editors.

However, an audit of the remaining views across 375px (Phone), 768px (Tablet Portrait), and 1280px+ (PC) revealed three remaining gaps:
1. **TopBar (`frontend/components/layout/TopBar.tsx`)**:
   - The `Home` link has `hidden sm:flex`, hiding it completely on phones (`< 640px`), while remaining visible on tablets (`sm+`).
   - The three top-bar regions use fixed `w-1/3` widths (`<div className="flex items-center w-1/3">`). On a 375px screen (`px-4` = 343px inner width), each third gets only ~114px. Showing 3 icons on the left (Sidebar toggle, Home, BentoMenu = ~116px) and `PortfolioSwitcher` in the center (`max-w-[150px]` + dot + currency + chevron = ~210px) causes overlap or clipping on narrow viewports.
2. **Global Library (`PlaybookList`, `PlaybookFilterBar`, `TaxonomyManager`, `AnnotationManager`)**:
   - `PlaybookList.tsx` renders a 5-column `<table>` (`Name`, `Tags`, `Status`, `Created`, `Actions`) directly inside `<div className="solid-card">` with no `overflow-x-auto` and no mobile card view. On a 375px phone, the right side of the table is cut off.
   - `PlaybooksPage` (`app/dashboard/library/playbooks/page.tsx`) renders `<PageHeader title="Playbooks" ... />` while `PlaybookList` renders its own `<h2>Playbooks</h2>` header right below it.
   - `TaxonomyManager` (Tags) and `AnnotationManager` (Metrics) use `opacity-0 group-hover:opacity-100` for card Edit/Delete buttons, making quick actions invisible on touch screens (phones & tablets), and their read-only detail header bars do not wrap when tag/metric names are long.
   - `WorkspaceFilterBar` and `CheckinFilterBar` header rows use `flex items-center justify-between` without `flex-wrap`, cramping buttons when a Saved View is active on mobile.
3. **Chrome App / PWA Installability**:
   - The frontend has no Web App Manifest (`manifest.webmanifest` / `app/manifest.ts`), no PNG app icons in `public/` (only `public/logo.svg`), no `appleWebApp` or `themeColor` metadata in `app/layout.tsx`, and no Service Worker (`public/sw.js`).
   - Without a manifest + icons + registered service worker with a `fetch` handler, Chrome on Desktop (Windows/macOS/Linux) and Android (Phone/Tablet) will not offer the "Install Trade Sensei" prompt or standalone app window (`display: standalone`).

## Goals / Non-Goals

**Goals:**
- Ensure the `Home` button in `TopBar` is visible and touch-accessible on all viewports (Phone, Tablet, PC) without colliding with the `PortfolioSwitcher` or `BentoMenu`.
- Provide an optimal Playbooks overview across all three form factors:
  - **Phone (`< md` / `< 768px`)**: Stacked `PlaybookCard` list with an interactive `Active` / `Inactive` status toggle, tag pills, creation date, `Edit` action button, and a mobile sort dropdown.
  - **Tablet (`md`–`lg` / `768px`–`1023px`) & PC (`lg+` / `1024px+`)**: 5-column sortable table inside an `overflow-x-auto` container so columns never clip.
- Eliminate duplicate headers on `/dashboard/library/playbooks` and make touch actions (`Edit` / `Delete`) and filter bars responsive across the Global Library, Workspace, and Check-in hubs.
- Make Trade Sensei installable as a standalone Chrome App / PWA on PC (Chrome/Edge), Android (Phone & Tablet), and iOS/iPadOS ("Add to Home Screen") using zero external runtime npm dependencies.

**Non-Goals:**
- Offline trade creation or background sync of mutations while disconnected (Trade Sensei is an authenticated financial analytics platform; API requests must remain live and uncached).
- Push notifications or Web Push API integration.
- Changes to backend FastAPI endpoints or database schemas.

## Decisions

### Decision 1: Responsive TopBar Flex Layout instead of Fixed `w-1/3` Columns
- **Choice**: Replace the three `w-1/3` wrappers in `TopBar.tsx` with:
  - Left container: `flex items-center shrink-0 gap-1` (Sidebar toggle, `Home` link visible on all viewports via `flex`, `BentoMenu`, plus the `contextLabel` badge on `md:block`).
  - Center container: `flex items-center justify-center min-w-0 flex-1 px-1 sm:px-2` containing `PortfolioSwitcher`.
  - Right container: `flex items-center justify-end shrink-0` containing `UserBadge`.
  - In `PortfolioSwitcher.tsx`, make the trigger button `max-w-full min-w-0` with responsive name truncation (`max-w-[96px] sm:max-w-[150px] md:max-w-[220px]`) and hide the 3-letter currency code on ultra-narrow screens (`hidden xs:inline` / `hidden sm:inline`) so a 375px viewport comfortably fits all controls.
- **Rationale**: On a 375px phone, three 36px icon buttons on the left take ~116px and the 32px `UserBadge` on the right takes 32px, leaving ~195px in the center for `PortfolioSwitcher`. Fixed `w-1/3` wasted space on the right (32px avatar in a 114px box) while starving the left and center sections.
- **Alternatives considered**:
  - *Move Home button into BentoMenu on mobile*: Rejected because the user explicitly wants the Home button directly visible in the mobile top bar just like on tablet.

### Decision 2: Playbook Overview Responsive Breakpoints (`< md` Cards, `md+` Table)
- **Choice**:
  - Render a mobile card list (`md:hidden`) in `PlaybookList.tsx` and keep the 5-column sortable table on `md+` (`hidden md:block overflow-x-auto`).
  - Include a compact sort toolbar above the mobile cards (`md:hidden`) with a `<select aria-label="Sort playbooks">` offering `Name: A → Z`, `Name: Z → A`, `Created: newest`, `Created: oldest`, `Status: Active first`, `Status: Inactive first` wired to the same `sortKey` / `sortDir` state as the desktop table headers.
  - Each mobile playbook card is tappable (navigates to `/dashboard/library/playbooks/[id]`), displays the playbook name, the interactive `Active` / `Inactive` status toggle button (`e.stopPropagation()`), taxonomy tag chips, formatted creation date, and an explicit `Edit` button (`e.stopPropagation()` → `?edit=true`).
  - Remove the redundant `<PageHeader title="Playbooks" subtitle="..." />` in `app/dashboard/library/playbooks/page.tsx` and the second heading + description in `PlaybookList.tsx`. Replace both with a single clean header row in `PlaybookList.tsx`: `<h1 className="text-2xl font-bold tracking-tight text-foreground">Playbooks</h1>` on the left and a compact, non-wrapping `+ New Playbook` CTA button on the right (`shrink-0 whitespace-nowrap h-9 px-3 sm:px-4 text-xs sm:text-sm font-medium`), with no subtitle text—matching `CheckinsPageClient` and `TradesPageClient` (where `TradesPageClient` also removes its subtitle for consistency). Apply the same clean header simplification to `Tags` (`app/dashboard/library/tags/page.tsx`) and `Metrics` (`app/dashboard/library/metrics/page.tsx`) by removing the subtitle descriptions and keeping the `New Tag`, `New Metric`, and `Today's Check-in` buttons compact (`shrink-0 whitespace-nowrap h-9`).
- **Rationale**: A 5-column table fits comfortably at `768px` (Tablet portrait) when wrapped in `overflow-x-auto`, whereas below `768px` (`< md`) a card layout prevents horizontal scrolling and matches `TradeCard` from `2026-10-30-trade-mobile-layout`.

### Decision 3: Touch-Visible Actions & Responsive Filter Headers across Library / Workspace / Check-ins
- **Choice**:
  - In `TaxonomyManager.tsx` and `AnnotationManager.tsx`, change the card action wrapper from `opacity-0 group-hover:opacity-100 focus-within:opacity-100` to `opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus-within:opacity-100` so touch users on phones and tablets always see the Edit/Delete icons.
  - In `TaxonomyManager.tsx` and `AnnotationManager.tsx` detail view headers, add `flex-wrap gap-3` so long tag/metric names never push `Edit` / `Archive` / `Delete` buttons off-screen on 375px phones.
  - In `PlaybookFilterBar.tsx`, allow the header row and quick-status pill group (`Active (n)`, `Inactive (n)`, `All (n)`) to wrap or scroll horizontally without overflowing a 375px card.
  - In `WorkspaceFilterBar.tsx` and `CheckinFilterBar.tsx`, add `flex-wrap gap-2` to the top bar row so `Filters`, `Saved View`, `Save View`, `Update`, and `Clear` wrap cleanly on narrow screens.

### Decision 4: Native Next.js App Router Manifest + Minimal Network-First Service Worker (Zero Third-Party PWA Plugin)
- **Choice**:
  - Use Next.js App Router's built-in `frontend/app/manifest.ts` convention (`MetadataRoute.Manifest`) to serve `/manifest.webmanifest`.
  - Generate standard PNG icons from `frontend/public/logo.svg` into `frontend/public/icons/`:
    - `icon-192x192.png` (`192×192`, `purpose: "any"`)
    - `icon-512x512.png` (`512×512`, `purpose: "any"`)
    - `icon-maskable-512x512.png` (`512×512`, `purpose: "maskable"` with safe-zone padding on `#131317` background)
    - `apple-touch-icon.png` (`180×180` for iOS/iPadOS Home Screen)
  - Configure `export const viewport: Viewport` and `metadata.appleWebApp` in `frontend/app/layout.tsx` (`themeColor: "#131317"`, `appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "Trade Sensei" }`).
  - Create a lightweight, dependency-free Service Worker at `frontend/public/sw.js` and register it via a tiny client component `PwaRegistrar` mounted in `RootLayout`:
    - `install` event calls `self.skipWaiting()`.
    - `activate` event cleans up old caches and calls `self.clients.claim()`.
    - `fetch` event:
      - Immediately returns (network-only pass-through) for any non-GET request, any `/api/` or `/auth/` URL, or cross-origin requests.
      - Uses a **network-first** strategy for navigation and static assets (`/_next/static/*`, `/icons/*`, `/logo.svg`), falling back to cache only if the network is unreachable.
- **Rationale**:
  - Chrome on Desktop, Android Phone, and Android Tablet requires: (1) HTTPS or `localhost`, (2) a valid Web App Manifest with `name`/`short_name`, `start_url`, `display: "standalone"`, and `192×192` + `512×512` icons, and (3) a registered Service Worker with a `fetch` handler.
  - Third-party wrappers like `next-pwa` or `@ducanh2912/next-pwa` inject Workbox webpack plugins that frequently conflict with Next.js 16 standalone builds and aggressive precaching can serve stale auth/API states. A 40-line native `public/sw.js` with `app/manifest.ts` is 100% compatible with Next.js 16 `output: "standalone"`, requires zero npm packages, and guarantees `/api/*` is never cached.

## Risks / Trade-offs

- **[Risk] Service Worker caching stale Next.js chunks after a deployment** → **Mitigation**: Use a **network-first** strategy in `sw.js` for all requests (never cache-first for HTML/RSC payloads) and version the cache key with the app version or clear caches on `activate`. Never intercept `/api/*`.
- **[Risk] TopBar crowding when Portfolio name is very long on 320px–375px screens** → **Mitigation**: Apply `min-w-0 flex-1` to the center slot and `truncate max-w-[96px] sm:max-w-[150px] md:max-w-[220px]` to the portfolio name span inside `PortfolioSwitcher`, plus a `shrink-0` constraint on left/right icon groups.
- **[Risk] Existing Playwright or Jest tests expecting two "Playbooks" headings or desktop-only table rows** → **Mitigation**: Keep `<table>` in the DOM on `md+` (`hidden md:block`) and cards in `md:hidden` (matching the pattern proven in `TradeTable.tsx`), so unit tests and desktop E2E tests continue to find table elements while mobile E2E tests assert card visibility.
