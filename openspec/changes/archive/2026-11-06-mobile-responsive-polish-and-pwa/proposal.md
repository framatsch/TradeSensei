## Why

Recent changes (`2026-10-11-playbook-active-status-management`, `2026-10-30-playbook-checkin-document-layout`, `2026-10-30-trade-mobile-layout`, and `2026-10-31-trade-detail-chart-maximize-and-collapsible-panels`) modernized the Trade Detail, Trades list, Playbook editor, and Market Check-in editor for mobile viewports (`< lg`). However, several high-visibility responsive gaps remain on phone (`< sm` / 375px) and tablet (`sm`–`lg`) viewports:
1. The **Home button** in `TopBar` is hidden on phones (`hidden sm:flex`), leaving mobile users without a 1-tap way to return to their configured home route, while fixed `w-1/3` topbar columns crowd the `PortfolioSwitcher` on 375px screens.
2. In the **Global Library**, the **Playbooks table** (`PlaybookList`) renders a 5-column desktop `<table>` without a mobile card layout or `overflow-x-auto` wrapper, causing columns (`Created`, `Actions`, `Status`) to be clipped on phones; additionally, `PlaybooksPage` renders a duplicate `PageHeader` above `PlaybookList`'s own header, and the Tags/Metrics library cards hide their Edit/Delete actions behind hover-only `opacity-0 group-hover:opacity-100` classes that are unreachable on touch devices.
3. Users want to install Trade Sensei as a native-like **Chrome / Web App (PWA)** on Desktop (Chrome/Edge), Android (Phone & Tablet), and iOS/iPadOS, which currently fails because the app lacks a Web App Manifest, app icons, apple-web-app metadata, and a service worker.

## What Changes

- **TopBar Responsive Layout (Phone, Tablet & PC)**:
  - Make the `Home` link visible across all viewports (`flex` instead of `hidden sm:flex`) with a touch-friendly hit target.
  - Replace rigid `w-1/3` TopBar sections with a flexible layout (`shrink-0` left/right controls, `min-w-0 flex-1` center section) and responsive `PortfolioSwitcher` truncation (`max-w-[110px] sm:max-w-[160px] md:max-w-[220px]`) so the sidebar toggle, Home button, BentoMenu, PortfolioSwitcher, and UserBadge all fit cleanly on a 375px phone without clipping.
- **Global Library & Playbooks Responsive Layout (`PlaybookList`, `PlaybookFilterBar`, `TaxonomyManager`, `AnnotationManager`)**:
  - **Playbooks Mobile Card List (`< md`)**: Below `md` (`< 768px`), render playbooks as stacked, tappable `PlaybookCard` items showing Playbook Name, interactive `Active` / `Inactive` status toggle badge, taxonomy tag pills, created date, and a touch-visible `Edit` action button, accompanied by a compact mobile sort dropdown (`Name: A → Z`, `Name: Z → A`, `Created: newest`, `Created: oldest`, `Status: Active first`, `Status: Inactive first`).
  - **Playbooks Tablet & Desktop Table (`md+`)**: Keep the 5-column sortable table on `md+` wrapped in `overflow-x-auto` so tablet portrait (`768px`) never clips columns.
  - **Simplified Single-Row Page Headers & Proportionate Action Buttons**: Remove the duplicate heading and both description texts on Playbooks (`PlaybooksPage` + `PlaybookList`), simplifying to a single compact header row (`<h1 className="text-2xl font-bold tracking-tight text-foreground">Playbooks</h1>` on the left, compact single-line `+ New Playbook` button with `shrink-0 whitespace-nowrap h-9 px-3 sm:px-4 text-xs sm:text-sm` on the right) with no subtitle clutter—matching `Check-ins` and `Trades`. Apply the same clean single-row header pattern (title + action button/controls on one row, without redundant description subtitles) to `Tags` (`tags/page.tsx` + `TaxonomyManager`) and `Metrics` (`metrics/page.tsx` + `AnnotationManager`), and ensure `PlaybookFilterBar` status tabs wrap cleanly on 375px viewports.
  - **Touch-Accessible Library Cards & Detail Headers**: Make Edit/Delete action buttons on Tags (`TaxonomyManager`) and Metrics (`AnnotationManager`) cards visible below `lg` (`opacity-100 lg:opacity-0 lg:group-hover:opacity-100`), and allow detail view headers in `TaxonomyManager` / `AnnotationManager` and filter bars (`WorkspaceFilterBar`, `CheckinFilterBar`) to wrap cleanly on narrow viewports without overflow.
- **Installable Chrome App / Progressive Web App (PWA)**:
  - Add a Web App Manifest (`frontend/app/manifest.ts` serving `/manifest.webmanifest`) with `display: "standalone"`, `start_url: "/dashboard"`, theme/background colors matching the Obsidian dark theme (`#0a0a14` / `#131317`), and PNG icons (`192×192`, `512×512`, `512×512 maskable`, plus `180×180` `apple-touch-icon.png`) generated from `public/logo.svg`.
  - Add Next.js `viewport` (`themeColor`, `viewportFit: "cover"`) and `appleWebApp` metadata in `frontend/app/layout.tsx`.
  - Add a minimal, safe Service Worker (`frontend/public/sw.js`) registered via a client component (`PwaRegistrar`) that satisfies Chrome's installability criteria on Desktop and Android while strictly bypassing `/api/*` requests and authentication flows so financial and trading data is never stale-cached.

## Capabilities

### New Capabilities
- `topbar-responsive-navigation`: Responsive TopBar behavior across phone (`< sm`), tablet (`sm`–`lg`), and desktop (`lg+`), ensuring the Home button, Sidebar toggle, BentoMenu, PortfolioSwitcher, and UserBadge are always accessible without horizontal overflow.
- `library-responsive-ui`: Responsive layouts for the Global Library (`PlaybookList`, `PlaybookFilterBar`, `TaxonomyManager`, `AnnotationManager`) across phone (card list + sort select), tablet (`overflow-x-auto` table + touch-visible actions), and desktop.
- `pwa-installability`: Progressive Web App (PWA) manifest, multi-resolution icons, viewport/apple-web-app metadata, and network-first/API-bypassing service worker enabling standalone Chrome app installation on PC, Android Phone/Tablet, and iOS/iPadOS.

### Modified Capabilities
- `playbook-list-filtering-sorting`: Add mobile sort select below `md` and responsive filter bar wrapping on narrow viewports to complement desktop table column sorting.
- `playbook-lifecycle-status`: Extend the interactive `Active` / `Inactive` status toggle and `Edit`-only action pattern to mobile playbook cards below `md`.

## Impact

- **Frontend Layout & Navigation**:
  - `frontend/components/layout/TopBar.tsx`
  - `frontend/components/layout/PortfolioSwitcher.tsx`
- **Frontend Global Library & Responsive Views**:
  - `frontend/app/dashboard/library/playbooks/page.tsx`
  - `frontend/components/playbooks/PlaybookList.tsx`
  - `frontend/components/playbooks/PlaybookFilterBar.tsx`
  - `frontend/components/library/TaxonomyManager.tsx`
  - `frontend/components/library/AnnotationManager.tsx`
  - `frontend/components/workspace/WorkspaceFilterBar.tsx`
  - `frontend/components/checkin/CheckinFilterBar.tsx`
- **Frontend PWA Assets & Registration**:
  - `frontend/app/layout.tsx`
  - `frontend/app/manifest.ts`
  - `frontend/components/pwa/PwaRegistrar.tsx`
  - `frontend/public/sw.js`
  - `frontend/public/icons/icon-192x192.png`, `icon-512x512.png`, `icon-maskable-512x512.png`, `apple-touch-icon.png`
- **Tests**:
  - `frontend/__tests__/components/layout/TopBar.test.tsx`
  - `frontend/__tests__/components/playbooks/PlaybookList.test.tsx`
  - `frontend/tests/specs/playbook-strategy-hub.spec.ts` (mobile 375×812 & tablet 768×1024 assertions)
- **Backend / API**: No backend or database changes required.
