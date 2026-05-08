## Why

Traders analyze multiple market indices daily (e.g., S&P 500, NASDAQ, DAX) to understand the macro context. We need to associate check-ins with these target indices. Crucially, to adhere to our strict Anti-Lag and Static Historical Context principles, this association must avoid dynamic, main-thread-blocking chart embeds. Historical integrity requires that visual context captures the exact manual drawings made on that day, which dynamic charts fail to do.

## What Changes

- Add a Settings section to manage Market Indexes (Symbol, Name, TradingView link).
- Update the Check-in form with a multi-select component (or selectable chips) to tag multiple target indices per check-in.
- Display associated indices as neutral badges in the Timeline view alongside static TradingView external links.
- Enforce static visual evidence: index charts must be uploaded as static screenshots rather than embedded dynamically.
- Index-specific observations are to be recorded directly in the check-in's markdown notes (e.g., `### NQ`, `### DAX`).

## Capabilities

### New Capabilities
- `market-indexes`: Management of configurable market indices scoped to the user, seeded with default global indices.

### Modified Capabilities
- `daily-checkins`: Update data model to support a many-to-many relationship with market indices, updating the API and UI to accommodate multi-select input and badge display.

## Impact

- **Database**: New `market_index_definitions` table and a `checkin_market_indices` junction table.
- **Backend API**: Endpoints for index management. `DailyCheckinPayload` accepts `target_index_ids: list[UUID]`.
- **Frontend UI**: Settings for indexes. Multi-select on Check-in form. Badges and external TV links on Timeline. No embedded charts or iFrames permitted.