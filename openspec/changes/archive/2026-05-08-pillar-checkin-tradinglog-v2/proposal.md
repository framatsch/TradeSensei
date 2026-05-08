## Why

The application has a working pillar routing skeleton but lacks fully operative layouts for the Trading Log and the Market Check-in pillars. The Trading Log pillar needs refinements (canonical "SAVED FILTERS" section labeling, explicit prohibition of the Column Visibility Toggle) and the Market Check-in pillar needs a fully specified UI: a persistent mini-calendar with regime-color indicators, two distinct view modes (Timeline and Model Book), thumbnail-first media rendering with a Lightbox for full-resolution images, and full URL-sync for all filter/pagination state.

## What Changes

- **Trading Log Pillar (Spec 10 revision):** Rename sidebar filter section from "Trades" to "SAVED FILTERS". Explicitly prohibit the Column Visibility Toggle. Lock down mockup-exact section structure and labels.
- **Market Check-in Pillar (Spec 8 — new):** Full operative layout for `/dashboard/checkins/...` — persistent mini-calendar sidebar with regime-color dot indicators, Timeline view and Model Book view, thumbnail-optimized media rendering (no full-res in lists), Lightbox on click, URL-synced filters and pagination, dynamic form inputs driven by `CheckinFieldDefinition` records.
- **Pillar color coding:** `MarketRegimeDefinition.color_hex` is applied consistently to calendar dots, active regime pills, timeline accent borders, and Model Book grid cards.
- **Performance constraint:** Full-resolution S3 images are NEVER loaded in list/grid views — only thumbnails; full images load on explicit Lightbox open.

## Capabilities

### New Capabilities
- `market-checkin-pillar`: Complete operative layout for the Market Check-in pillar — mini-calendar sidebar with regime indicators, Timeline view, Model Book view, Lightbox, URL-sync, dynamic form fields.

### Modified Capabilities
- `trading-log-operative-sidebar`: Rename "Trades" sidebar section to "SAVED FILTERS"; add explicit prohibition of Column Visibility Toggle; tighten section label spec.

## Impact

- Frontend: new `CheckinLayout`, `CheckinSidebar`, `CheckinMiniCalendar`, `TimelineView`, `ModelBookView`, `CheckinLightbox` components under `/dashboard/checkins/`.
- Frontend: `TradingLogSidebar` section label change (minor); remove any Column Visibility Toggle if present.
- No new backend endpoints required — uses existing checkin, regime, and field-definition APIs.
- URL state: `CheckinModelBookParams` hook for view mode, date range, regime filter, pagination.
