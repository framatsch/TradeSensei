## Why

Trade filters in the Trades view are currently ephemeral, forcing users to rebuild the same filter sets repeatedly. Persisting named filters per user (and curated global filters) makes navigation faster and enables consistent, shareable views.

## What Changes

- Add persisted saved trade filters with UUIDs, names, scopes (global or user), and structured filter definitions.
- Expose read-only global filters seeded by the application and user-owned filters managed via CRUD endpoints.
- Surface saved filters as “Views” in the Trades navigation and apply their definitions to load trades.
- Enforce permissions: users can edit/delete only their own filters; global filters are read-only in UI/API.

## Capabilities

### New Capabilities
- `saved-trade-filters`: Persist, list, and apply named trade filters with per-user ownership and global read-only seeds.

### Modified Capabilities

## Impact

- Backend: new models, repositories, services, API endpoints, and database migration for saved trade filters.
- Frontend: Trades navigation and filter panel updates to list/apply/manage saved filters.
- Data: seed data for global filters.
