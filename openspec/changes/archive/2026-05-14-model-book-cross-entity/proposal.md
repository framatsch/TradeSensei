## Why

The current Model Book view is a check-in-only screenshot gallery. Traders build pattern recognition from *both* setups (trades) and market environments (check-ins) — keeping them separate forces users to context-switch rather than see patterns across domains. This change evolves the Model Book into a unified "vault of conviction": any trade or check-in can be starred and will appear side-by-side in the Model Book gallery.

## What Changes

- Add `is_modelbook: bool` (default: `false`) column to the `trades` table via Alembic migration.
- Add `is_modelbook: bool` (default: `false`) column to the `daily_checkins` table via Alembic migration.
- Add PATCH endpoints for starring/unstarring on both trades and check-ins.
- Replace the current check-in-only `ModelBookView` with a cross-entity grid that renders both Trade cards and Check-in cards.
- Add a "Star" toggle button to the Trade Detail view toolbar and the Check-in Detail (form) toolbar.
- Implement a unified filter bar in the Model Book that supports date range + entity type filter (All / Trades / Check-ins).
- Update the Model Book tab navigation label/icon to reflect the new cross-entity scope.

## Capabilities

### New Capabilities

- `model-book-starring`: Star/unstar toggle that marks trades and check-ins as Model Book entries, with persistent backend state.
- `model-book-cross-entity-gallery`: Unified gallery view rendering Trade cards and Check-in cards side-by-side, with entity-type filtering and date range filtering.

### Modified Capabilities

- `checkin-modelbook-filters`: The existing filter bar (date range, regime) must be extended to support an entity-type filter (All / Trades / Check-ins). The regime filter becomes Check-in-only and is hidden when "Trades" is selected.

## Impact

- **Backend**: Two new columns (`trades.is_modelbook`, `daily_checkins.is_modelbook`) — Alembic migration required. Two new PATCH endpoints (`/trades/{id}/modelbook`, `/checkins/{date}/modelbook`). New paginated GET endpoint `/model-book/entries` that merges starred trades and check-ins sorted by date.
- **Frontend**: `ModelBookView.tsx` replaced entirely. New `ModelBookCard` component (polymorphic: trade vs. check-in variant). Trade Detail page gains a star toggle (note: `trade-detail-redesign` change is in-progress — coordinate toolbar placement). Check-in form gains a star toggle.
- **API Client**: Regenerate after backend changes.
- **No breaking changes** to existing trade or check-in endpoints.
