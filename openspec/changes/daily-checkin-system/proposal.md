## Why

Traders need a structured, portfolio-independent way to record their daily mental state, macro market context, and configurable personal metrics. Without this, performance analysis cannot be correlated against psychological or macro factors — the platform lacks the foundational data layer required for deeper retrospective insights and behavioral pattern detection.

## What Changes

- New `DailyCheckin` entity: a per-user, per-day record capturing market phase (string referencing user-defined phase), notes, linked news, and screenshot evidence
- New `CheckinFieldDefinition` entity: user-scoped schema for dynamic, typed custom fields (integer, boolean)
- New `MarketPhaseDefinition` entity: user-scoped registry of named market phases with display label and color. Four defaults (`bullish`, `bearish`, `sideways`, `volatile`) seeded at registration; fully user-configurable
- JSONB `custom_metrics` column on `DailyCheckin` with strict server-side validation against `CheckinFieldDefinition` records
- `market_phase` stored as `VARCHAR` on `DailyCheckin`, validated server-side against the user's active `MarketPhaseDefinition` names
- Seeding hook on user registration: provision default `CheckinFieldDefinition` rows AND default `MarketPhaseDefinition` rows for every new user
- Dedicated screenshot upload endpoint using presigned URLs (object storage), decoupled from check-in CRUD
- Full CRUD API for check-ins, field definitions, and market phase definitions, scoped per authenticated user

## Capabilities

### New Capabilities

- `daily-checkin`: Create, read, update, and delete daily check-in entries with market phase (user-defined), notes, news links, screenshot URLs, and validated custom metrics
- `checkin-field-definitions`: Manage user-scoped field definitions (name, type, active flag) that govern which custom metrics are valid on a check-in
- `market-phase-definitions`: Manage user-scoped market phase registry (name, label, color, active flag). Defaults seeded at registration; user can add, rename, recolor, or deactivate phases
- `checkin-screenshot-upload`: Dedicated endpoint for secure screenshot uploads via presigned object-storage URLs, returning a URL for attachment to a check-in

### Modified Capabilities

- `account-management`: User registration hook must seed default `CheckinFieldDefinition` rows for each new user

## Impact

- **Backend**: New ORM models (`DailyCheckin`, `CheckinFieldDefinition`, `MarketPhaseDefinition`), Pydantic schemas, repository layer, service layer, API routes under `/checkins`, `/checkin-fields`, and `/market-phases`
- **Database**: Three new tables + Alembic migration; `DailyCheckin.date` + `DailyCheckin.user_id` unique constraint; JSONB column; `market_phase` stored as VARCHAR (not a PG enum)
- **Auth**: All endpoints require authenticated user; queries are user-scoped — no cross-user data access possible
- **Registration flow**: `auth` / `user` service gains post-registration side-effects to seed both `CheckinFieldDefinition` and `MarketPhaseDefinition` defaults
- **Object storage**: Presigned URL generation requires a configured storage backend (S3-compatible); no file bytes pass through the API server
- **Frontend**: Out of scope for this change — API and data model only
