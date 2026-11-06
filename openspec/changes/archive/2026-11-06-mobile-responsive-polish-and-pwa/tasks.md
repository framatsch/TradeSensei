## 1. TopBar Responsive Navigation (Phone, Tablet & PC)

- [x] 1.1 Update `frontend/components/layout/TopBar.tsx` to make the `Home` link (`aria-label="Home"`) visible on all viewports (`flex` instead of `hidden sm:flex`), replace rigid `w-1/3` sections with `shrink-0` left/right containers and a `min-w-0 flex-1 px-1 sm:px-2` center container, and hide the `contextLabel` below `md` (`hidden md:block`).
- [x] 1.2 Update `frontend/components/layout/PortfolioSwitcher.tsx` to constrain width on narrow viewports (`max-w-full min-w-0`, portfolio name `truncate max-w-[96px] sm:max-w-[150px] md:max-w-[220px]`, currency label `hidden sm:inline`) so `TopBar` never overflows on 375px phones.

## 2. Global Library & Playbooks Responsive Layout

- [x] 2.1 Remove the redundant `<PageHeader title="Playbooks" subtitle="..." />` in `frontend/app/dashboard/library/playbooks/page.tsx` and the duplicate heading + description texts in `PlaybookList.tsx`, leaving a single clean header row (`<h1 className="text-2xl font-bold tracking-tight text-foreground">Playbooks</h1>` on the left and a compact single-line `+ New Playbook` button with `shrink-0 whitespace-nowrap h-9 px-3 sm:px-4 text-xs sm:text-sm` on the right, with no subtitle text). Likewise remove redundant subtitle descriptions on `Tags` (`tags/page.tsx`) and `Metrics` (`metrics/page.tsx`) and ensure `New Tag`, `New Metric`, and `Today's Check-in` buttons use `shrink-0 whitespace-nowrap h-9`.
- [x] 2.2 Update `frontend/components/playbooks/PlaybookFilterBar.tsx` so the filter toggle and quick status tabs (`Active`, `Inactive`, `All`) wrap cleanly on 375px phone viewports without horizontal overflow.
- [x] 2.3 Update `frontend/components/playbooks/PlaybookList.tsx` to render:
  - A mobile sort bar (`md:hidden`) with `<select aria-label="Sort playbooks">` supporting `Name: A → Z`, `Name: Z → A`, `Created: newest`, `Created: oldest`, `Status: Active first`, and `Status: Inactive first`.
  - A mobile card list (`md:hidden`, `data-testid="playbook-card-list"`) where each card displays the playbook name, interactive `Active`/`Inactive` status toggle badge, creation date, `Edit` action button (`?edit=true`), and taxonomy tag pills.
  - The 5-column sortable table on `md+` wrapped in `<div className="hidden overflow-x-auto md:block">` so tablet portrait (`768px`) and desktop (`1024px+`) never clip columns.
- [x] 2.4 Update `frontend/components/library/TaxonomyManager.tsx` and `frontend/components/library/AnnotationManager.tsx` so card-level `Edit` and `Delete` buttons are visible on touch/mobile/tablet viewports (`opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus-within:opacity-100`) and detail view headers wrap cleanly (`flex-wrap gap-3`) on narrow screens.
- [x] 2.5 Update `frontend/components/workspace/WorkspaceFilterBar.tsx` and `frontend/components/checkin/CheckinFilterBar.tsx` header rows with `flex-wrap gap-2` so saved-view action buttons wrap cleanly on narrow viewports.

## 3. Installable Chrome App / Progressive Web App (PWA)

- [x] 3.1 Generate PWA PNG icon assets from `frontend/public/logo.svg` into `frontend/public/icons/icon-192x192.png`, `frontend/public/icons/icon-512x512.png`, `frontend/public/icons/icon-maskable-512x512.png`, and `frontend/public/apple-touch-icon.png`.
- [x] 3.2 Create `frontend/app/manifest.ts` exporting the Next.js `MetadataRoute.Manifest` (`name`, `short_name`, `description`, `start_url: "/dashboard"`, `scope: "/"`, `display: "standalone"`, `background_color: "#0a0a14"`, `theme_color: "#131317"`, and icon definitions).
- [x] 3.3 Create `frontend/public/sw.js` implementing a minimal Service Worker (`install` `skipWaiting`, `activate` cache cleanup + `clients.claim`, and network-first `fetch` handler that strictly bypasses `/api/*`, `/auth/*`, and non-GET requests) and `frontend/components/pwa/PwaRegistrar.tsx` to register `/sw.js` on client load.
- [x] 3.4 Update `frontend/app/layout.tsx` to export `viewport` (`themeColor: "#131317"`, `width: "device-width"`, `initialScale: 1`, `viewportFit: "cover"`), add `manifest` / `appleWebApp` / `icons` to `metadata`, and mount `<PwaRegistrar />`.

## 4. Verification & Automated Tests

- [x] 4.1 Add/update Jest unit tests for `TopBar` (asserting `Home` button is visible across viewports), `PlaybookList` (asserting mobile cards, mobile sort select, status toggle, and desktop table), and `PwaRegistrar` / `manifest`.
- [x] 4.2 Update Playwright E2E tests (`frontend/tests/specs/playbook-strategy-hub.spec.ts`) to verify mobile (`375×812`) and tablet (`768×1024`) Playbook overview rendering, `Home` button visibility on mobile, and `/manifest.webmanifest` availability.
- [x] 4.3 Run frontend lint, typecheck (`tsc --noEmit`), and Jest test suite to ensure zero regressions.
