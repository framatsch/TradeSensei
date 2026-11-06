# pwa-installability Specification

## Purpose
Progressive Web App (PWA) manifest, multi-resolution icons, viewport/apple-web-app metadata, and network-first/API-bypassing service worker enabling standalone Chrome app installation on PC, Android Phone/Tablet, and iOS/iPadOS.

## Requirements

### Requirement: Web App Manifest for standalone installation
The frontend application SHALL expose a valid Web App Manifest at `/manifest.webmanifest` (via Next.js `app/manifest.ts`) with:
- `name`: `"Trade Sensei"`
- `short_name`: `"Trade Sensei"`
- `description`: `"Advanced statistical analysis and journaling for your trades"`
- `start_url`: `"/dashboard"`
- `scope`: `"/"`
- `display`: `"standalone"`
- `background_color`: `"#0a0a14"`
- `theme_color`: `"#131317"`
- `icons`:
  - `/icons/icon-192x192.png` (`192x192`, `image/png`, `purpose: "any"`)
  - `/icons/icon-512x512.png` (`512x512`, `image/png`, `purpose: "any"`)
  - `/icons/icon-maskable-512x512.png` (`512x512`, `image/png`, `purpose: "maskable"`)

#### Scenario: Browser fetches the Web App Manifest
- **WHEN** a browser or PWA audit tool requests `/manifest.webmanifest`
- **THEN** the response has status 200 and JSON content containing `display: "standalone"`, `start_url: "/dashboard"`, and the `192x192`, `512x512`, and `maskable` icon entries

#### Scenario: PWA icon assets exist and are served as PNGs
- **WHEN** a client requests `/icons/icon-192x192.png`, `/icons/icon-512x512.png`, `/icons/icon-maskable-512x512.png`, or `/apple-touch-icon.png`
- **THEN** each asset is served from `public/` with valid PNG dimensions matching its filename

### Requirement: Root layout exposes PWA viewport and Apple Web App metadata
The root layout (`frontend/app/layout.tsx`) SHALL export Next.js `viewport` configuration (`themeColor: "#131317"`, `width: "device-width"`, `initialScale: 1`, `viewportFit: "cover"`) and `metadata` including `manifest: "/manifest.webmanifest"`, `appleWebApp` (`capable: true`, `statusBarStyle: "black-translucent"`, `title: "Trade Sensei"`), and `icons.apple: "/apple-touch-icon.png"`.

#### Scenario: Document head contains manifest and mobile web app meta tags
- **WHEN** any page is rendered by Next.js
- **THEN** `<head>` includes `<link rel="manifest" href="/manifest.webmanifest">`, `<link rel="apple-touch-icon" href="/apple-touch-icon.png">`, and `<meta name="theme-color" content="#131317">`

### Requirement: Service Worker registration with strict API bypass
The application SHALL register a Service Worker (`/sw.js`) in supported browsers via a client component (`PwaRegistrar`) mounted in `RootLayout`. The Service Worker SHALL:
1. Activate immediately (`skipWaiting` + `clients.claim`) and clean up obsolete cache versions.
2. Strictly bypass (`return` without intercepting) all non-GET requests, all requests whose pathname starts with `/api/` or `/auth/`, and all cross-origin requests, ensuring trading and authentication data is never cached by the Service Worker.
3. Provide a network-first `fetch` handler for same-origin static/navigation GET requests so Chrome on Desktop (Windows, macOS, Linux) and Android (Phone & Tablet) recognizes the app as installable.

#### Scenario: Service worker registers on page load
- **WHEN** a user opens Trade Sensei in a browser supporting `navigator.serviceWorker`
- **THEN** `navigator.serviceWorker.register("/sw.js")` is called after window load

#### Scenario: API requests bypass the Service Worker cache
- **WHEN** the frontend makes any request to `/api/v1/*` or any non-GET request while `/sw.js` is active
- **THEN** the Service Worker does not cache or intercept the response and passes the request directly to the network
