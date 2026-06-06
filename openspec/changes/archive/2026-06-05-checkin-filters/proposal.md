## Why

Users need the ability to filter their daily check-ins efficiently (e.g., by date, market phase, related indices, or whether they include images) to quickly find specific journal entries or analyze trading performance during certain market regimes. Additionally, they should be able to save these filter combinations as presets to easily switch between different analytical views without manually re-applying filters each time.

## What Changes

- Add a global filter bar to the Check-ins overview page (similar to the Reporting Hub / Workspace).
- Extend the `list_checkins` backend API to support filtering by `target_indices` and `has_media`.
- Create a new database table and SQLAlchemy model `SavedCheckinFilter` (similar to `SavedTradeFilter` or `SavedDashboardView`) to store user-defined filter presets for check-ins.
- Create new backend API endpoints to create, read, update, and delete saved checkin filters.
- Extend the frontend Check-ins page to load, select, and manage these saved filter views.

## Capabilities

### New Capabilities
- `checkin-filtering`: The core ability to filter check-ins by date, regime, target indices, and media presence.
- `saved-checkin-filters`: The ability to persist filter configurations as named views and recall them.

### Modified Capabilities
- `daily-checkin`: Extend the check-in listing capability with additional filtering dimensions (target_indices, has_media).

## Impact

- **Backend APIs**: Extends `GET /api/v1/checkins` with new query parameters. Introduces new endpoints under `/api/v1/checkins/filters` or similar.
- **Database**: Introduces a new table for saved checkin filters.
- **Frontend**: Adds a new UI component `CheckinFilterBar` and extends `CheckinsPageClient`. Uses new hooks to fetch and mutate saved checkin views.
