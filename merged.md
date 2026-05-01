#########################
# openspec/changes/daily-checkin-system/design.md
#########################

## Context

The platform currently has no mechanism for users to record daily market context or psychological state. Performance metrics (win rate, Sharpe ratio, drawdown) exist but cannot be correlated against trader behavior or macro environment. This change introduces the foundational data layer for that correlation — a portfolio-independent daily check-in system.

The backend follows a strict layered architecture (API → Service → Repository → Model) with async SQLAlchemy, Pydantic v2 schemas, and Alembic migrations. All monetary values use `Decimal`; timestamps are UTC-aware. The existing `auth_service.register()` method is the correct extension point for seeding default field definitions.

## Goals / Non-Goals

**Goals:**
- Introduce `DailyCheckin` and `CheckinFieldDefinition` ORM models with migrations
- Implement full CRUD for both entities, scoped strictly to the authenticated user
- Validate `custom_metrics` JSONB payload server-side against the user's active `CheckinFieldDefinition` records at the service layer
- Seed a default set of field definitions on user registration via a hook in `auth_service.register()`
- Provide a dedicated presigned-URL endpoint for screenshot uploads (no file bytes through API)
- Expose all functionality via versioned REST endpoints under `/api/v1/checkins` and `/api/v1/checkin-fields`

**Non-Goals:**
- Frontend implementation (API and data model only)
- Historical migration of existing data
- Cross-user aggregation or admin views
- Correlation computation or dashboard integration (future layer)
- Video or file types other than images for screenshots

## Decisions

### D1 — JSONB validation at the service layer, not the DB layer

**Decision**: Validate `custom_metrics` keys/types in Python (service layer) against the user's active `CheckinFieldDefinition` rows, not via DB constraints.

**Rationale**: PostgreSQL CHECK constraints on JSONB are static and cannot reference another table. Triggers are fragile and hard to test. Service-layer validation integrates naturally with Pydantic error reporting, is unit-testable, and allows richer error messages (unknown field names, type mismatches).

**Trade-off**: A race condition exists if a `CheckinFieldDefinition` is deactivated mid-request. Mitigation: load field definitions inside the same DB transaction that writes the check-in; treat the snapshot as authoritative for that request.

**Alternative considered**: PostgreSQL domain type or trigger — rejected: untestable without a live DB, leaks business logic into the schema.

### D2 — `market_phase` is user-configurable, not a fixed enum

**Decision**: `market_phase` on `DailyCheckin` is stored as a free-form `string` referencing a `market_phase_name` from the user's own `MarketPhaseDefinition` records, not a hard-coded Python enum. The `DailyCheckin.market_phase` column is a plain `VARCHAR` validated server-side against the user's active `MarketPhaseDefinition` rows at write time — identical in pattern to `custom_metrics` validation against `CheckinFieldDefinition`.

**Default set seeded at registration** (within the same transaction as `CheckinFieldDefinition` defaults):

| `name` | `label` | `color_hex` |
|--------|---------|-------------|
| `bullish` | Bullish | `#22c55e` |
| `bearish` | Bearish | `#ef4444` |
| `sideways` | Sideways | `#f59e0b` |
| `volatile` | Volatile | `#8b5cf6` |

Users can deactivate any default phase, rename the label, change the color, or add entirely new phases (e.g. `trending`, `ranging`). The `name` field is the stable storage key (kebab-case, unique per user globally, immutable after creation — same rules as `CheckinFieldDefinition.field_name`). The `label` is a display-only string the user can rename freely.

**New entity required**: `MarketPhaseDefinition` — a new ORM model, repository, service, and API router (`/api/v1/market-phases`). Full CRUD with the same ownership semantics as `CheckinFieldDefinition`.

**Impact on Attribution API (Spec 6)**: The Attribution API groups by `DailyCheckin.market_phase` (the stored name string). The response bucket labels come from `MarketPhaseDefinition.label` for display; the grouping key is the `name`. The Attribution API MUST join `market_phase` values to `MarketPhaseDefinition` records for the requesting user to resolve display labels. Unknown/deactivated phase names in historical check-ins are preserved as-is and included in attribution with their raw name as the label.

**Rationale**: Different traders use fundamentally different market-phase taxonomies. A macro trader might want `risk-on / risk-off / consolidation`; a day trader might want `trending / ranging / volatile / news-driven`. Hardcoding four values limits the platform's analytical depth. The user-configurable model adds one entity but unlocks arbitrary correlation taxonomies.

**Alternative considered**: Fixed enum `bullish | bearish | sideways | volatile` — rejected by product decision; would require a schema migration every time a new value is needed and excludes users with different frameworks.

**Trade-off**: One additional entity and API surface. Validation complexity is identical to `custom_metrics` (same pattern already exists). The `market_phase` field on `DailyCheckin` loses compile-time enum safety — compensated by service-layer validation tests.

### D2b — `field_type` limited to `integer` and `boolean` initially

**Decision**: The `CheckinFieldDefinition.field_type` enum is restricted to `integer | boolean`. `float` and `string` are not included.

**Rationale**: The stated requirements explicitly list only these two types. Adding `float` introduces ambiguity (precision, rounding); `string` creates open-ended storage that weakens the typed-metrics contract. Extend the enum via a future migration if needed.

**Alternative considered**: Generic `string` type with format hints — rejected: defeats the purpose of typed validation.

### D3 — Presigned URL upload, no file bytes through the API

**Decision**: Screenshot uploads use a two-step flow: (1) client requests a presigned PUT URL from the API, (2) client uploads directly to object storage, (3) client includes the resulting URL in the check-in payload.

**Rationale**: Avoids streaming large binary payloads through the FastAPI process, eliminates memory pressure, and keeps the API server stateless. The presigned URL is generated server-side and expires shortly (e.g., 15 minutes).

**Trade-off**: Requires a configured S3-compatible storage backend (AWS S3, MinIO, etc.). Without it, the upload endpoint must return a meaningful error, not silently fail. The `STORAGE_BACKEND` config key must be validated at startup.

**Alternative considered**: Multipart upload directly to the API — rejected: scales poorly, complicates testing, increases server memory requirements.

### D3b — `screenshot_urls` behaviour when storage is not configured

**Decision**: When `STORAGE_PUBLIC_URL` is not configured, the `screenshot_urls` field on a `DailyCheckin` is treated as not available. Any non-empty `screenshot_urls` array submitted to POST or PATCH SHALL be rejected with HTTP 422 and a message indicating that screenshot storage is not configured. An empty array or omitted field is accepted normally.

**Rationale**: Without a known storage domain there is no way to validate URL provenance, making SSRF-adjacent misuse possible. Rejecting the field when unconfigured is safer than silently accepting arbitrary URLs. Users who do not need screenshots are unaffected (the field is optional).

**Alternative considered**: Skip URL validation when `STORAGE_PUBLIC_URL` is absent — rejected: creates a security gap and produces inconsistent runtime behaviour depending on deployment configuration.

### D4 — Default field seeding at registration time

**Decision**: `auth_service.register()` calls a new `CheckinFieldDefinitionRepository.seed_defaults(user_id)` method after the user is persisted, within the same transaction.

**Rationale**: Seeding inside the same transaction guarantees atomicity — if registration fails, no orphan field definitions are created. Using a post-registration hook (event or signal) would introduce eventual consistency without benefit.

**Default fields**: `mood-level` (integer, 1–10 scale by convention), `focus` (integer, 1–10), `rule-followed` (boolean). These are informational defaults; users can deactivate or add more.

**Trade-off**: Tight coupling between `auth_service` and `CheckinFieldDefinitionRepository`. Acceptable because the dependency is one-directional and the seeding logic is small.

### D5 — Unique constraint: one check-in per user per date

**Decision**: A database-level `UniqueConstraint('user_id', 'date')` is placed on `DailyCheckin`. The API returns HTTP 409 if a duplicate is attempted; the client should use PUT/PATCH to update.

**Rationale**: Two check-ins for the same day would create ambiguity in correlation queries. The constraint is enforced at the DB level (not just service logic) to prevent race conditions on concurrent requests.

**Alternative considered**: Allow multiple check-ins per day and take the latest — rejected: complicates aggregation queries and hides user errors.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| `custom_metrics` validation bypassed if field definitions are fetched outside the write transaction | Load definitions inside the check-in write transaction (same DB session) |
| Presigned URL generation fails silently if storage is not configured | Validate `STORAGE_BACKEND` at application startup; return HTTP 503 with a clear message if not configured |
| `field_type` enum additions in the future require a migration | Enum is defined in Python (not as a PG native enum) to allow zero-downtime additions via Alembic |
| Default field seeding creates noise for users who don't use the feature | Fields are `is_active=True` by default but can be deactivated; seeding is idempotent (use `INSERT ... ON CONFLICT DO NOTHING`) |
| JSONB storage loses schema enforcement at the DB level | Compensate with thorough service-layer tests covering all type-mismatch and unknown-key scenarios |

## Migration Plan

1. Add Alembic migration: create `checkin_field_definitions` table, then `daily_checkins` table with JSONB column and unique constraint
2. Add a second Alembic data migration that seeds the three default `CheckinFieldDefinition` rows (`mood-level`, `focus`, `rule-followed`) for all existing users using `INSERT ... ON CONFLICT DO NOTHING`
3. Deploy backend with new routes (additive — no existing routes change)
4. Rollback: drop both tables; remove seeding call from `auth_service.register()`

## Decisions (Additions)

### D8 — `news_links` validation and limits

**Decision**: Each entry in `news_links` SHALL be validated as a well-formed URL (scheme `http` or `https`). The array is capped at a maximum of 10 entries per check-in.

**Rationale**: Without URL validation the field becomes a free-text array, which weakens the contract and complicates future integrations. A cap of 10 prevents abuse without restricting normal use.

### D9 — `GET /api/v1/checkins` pagination

**Decision**: The list endpoint uses cursor-based pagination. Default page size: 30. Maximum page size: 90. The `from_date` / `to_date` filters are available as the primary scoping mechanism. The response envelope includes `items`, `next_cursor`, and `total` fields.

**Cursor format**: `next_cursor` is a plain ISO 8601 date string (e.g. `"2025-03-14"`) — the date of the last item on the current page. The next request passes this as `?cursor=2025-03-14` and the query returns records with `date < cursor_date`. This differs from the trade list cursor (which is HMAC-signed and encodes a sort value + UUID) because check-ins have a simpler pagination key: `(user_id, date)` is already unique, always sorted by date descending, and no tie-breaker is needed. HMAC signing adds no security value here since the date is not sensitive and all queries are already user-scoped.

**Rationale**: A trader with several years of daily check-ins could accumulate 1,000+ records. Returning all records on every call is unbounded. The date-as-cursor approach is pragmatic, easy to implement, and easy to test.

### D10 — `CheckinFieldDefinition` has no DELETE endpoint (by design)

**Decision**: Field definitions can be deactivated (`is_active=false`) but not deleted. There is no `DELETE /api/v1/checkin-fields/{id}` endpoint.

**Rationale**: Existing `DailyCheckin.custom_metrics` JSONB blobs reference field names by string key. Deleting a definition would orphan historical data silently. Deactivation preserves the audit trail while blocking the field from new check-ins. Users who want to "reuse" a field name reactivate the existing definition.

### D11 — `screenshot_urls` rejected when storage is not configured

**Decision**: When `STORAGE_PUBLIC_URL` is not configured, any non-empty `screenshot_urls` array submitted to POST or PATCH is rejected with HTTP 422. An empty array or omitted field is accepted normally.

**Rationale**: Without a known storage domain there is no way to validate URL provenance. Rejecting the field when unconfigured is safer than accepting arbitrary URLs.

## Open Questions

All open questions from earlier analysis are resolved above (D2 market_phase, D3b screenshot storage, D8 news_links, D9 pagination, D10 no-delete, D11 screenshot_urls without storage, backfill in Migration Plan step 2).

---

#########################
# openspec/changes/daily-checkin-system/proposal.md
#########################

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

---

#########################
# openspec/changes/daily-checkin-system/specs/account-management/spec.md
#########################

## MODIFIED Requirements

### Requirement: Account Type Specialization
The system MUST require an explicit `type` upon Account creation, strictly limited to an accepted enumeration (`MANUAL`, `SCHWAB`, `IBKR`). Account creation additionally MUST require a valid `portfolio_id` owned by the requesting user. The created account SHALL be linked to that portfolio.

After successfully persisting a new user, the system SHALL automatically seed default records for that user within the same database transaction:
- Three `CheckinFieldDefinition` rows: `mood-level` (integer), `focus` (integer), `rule-followed` (boolean)
- Four `MarketPhaseDefinition` rows: `bullish` (label: "Bullish", color: #22c55e), `bearish` (label: "Bearish", color: #ef4444), `sideways` (label: "Sideways", color: #f59e0b), `volatile` (label: "Volatile", color: #8b5cf6)

Seeding SHALL be idempotent — if default records already exist for the user, the operation SHALL succeed without creating duplicates.

#### Scenario: Creating a new account with a valid type
- **WHEN** the user creates an account with type `SCHWAB` and a valid `portfolio_id`
- **THEN** the system SHALL save the account and assign the `SCHWAB` type
- **THEN** the account's `portfolio_id` SHALL be set to the provided value

#### Scenario: Creating an account without portfolio_id rejected
- **WHEN** the user creates an account without providing `portfolio_id`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

#### Scenario: Creating an account with foreign portfolio_id rejected
- **WHEN** the user creates an account with a `portfolio_id` that belongs to another user
- **THEN** the system SHALL return HTTP 404

#### Scenario: Default field definitions and market phases seeded on registration
- **WHEN** a new user successfully registers
- **THEN** the system SHALL create three `CheckinFieldDefinition` records (`mood-level` integer, `focus` integer, `rule-followed` boolean) and four `MarketPhaseDefinition` records (`bullish`, `bearish`, `sideways`, `volatile`), all with `is_active=true`

#### Scenario: Registration rollback also rolls back field seeding
- **WHEN** the user registration transaction fails after the user record is written but before commit
- **THEN** no `CheckinFieldDefinition` records SHALL be persisted for that user

### Requirement: Store Encrypted Account Properties
The system MUST be able to attach multiple secure key-value properties to an account and encrypt their values symmetrically before persisting to the database.

#### Scenario: Submitting Broker Credentials during Account Creation
- **WHEN** the user creates a `SCHWAB` account and provides an `app_key` and `app_secret`
- **THEN** the system SHALL encrypt both values using Fernet symmetric encryption
- **THEN** the system SHALL persist them to the `account_properties` table linked to the account

#### Scenario: Fetching Account details masks secure properties
- **WHEN** the user retrieves an account via `GET /api/v1/portfolios/{portfolio_id}/accounts`
- **THEN** the system SHALL NOT return the plain text values of the account properties
- **THEN** the system SHALL instead return a boolean indicator or masked string (e.g., `has_api_keys: true`)

## REMOVED Requirements

### Requirement: Global User Broker Connections
**Reason**: Broker connections are now scoped to individual accounts rather than globally per user.
**Migration**: Existing tokens in `broker_connections` will be dropped. Users must re-enter credentials per account.

---

#########################
# openspec/changes/daily-checkin-system/specs/checkin-field-definitions/spec.md
#########################

## ADDED Requirements

### Requirement: Create a field definition
The system SHALL allow an authenticated user to create a `CheckinFieldDefinition` via POST `/api/v1/checkin-fields`. The record SHALL require `field_name` (string, max 100 chars, unique per user, lowercase kebab-case) and `field_type` (enum: `integer`, `boolean`). `is_active` SHALL default to `true`. A user SHALL NOT be able to create two active definitions with the same `field_name`.

#### Scenario: Successful creation
- **WHEN** an authenticated user sends POST `/api/v1/checkin-fields` with `field_name="energy"` and `field_type="integer"`
- **THEN** the system SHALL persist the definition and return HTTP 201

#### Scenario: Duplicate field_name rejected
- **WHEN** an authenticated user sends POST `/api/v1/checkin-fields` with a `field_name` that already exists for that user
- **THEN** the system SHALL return HTTP 409 Conflict

#### Scenario: Invalid field_type rejected
- **WHEN** an authenticated user sends POST `/api/v1/checkin-fields` with `field_type="float"`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

### Requirement: List field definitions
The system SHALL allow an authenticated user to list their `CheckinFieldDefinition` records via GET `/api/v1/checkin-fields`. An optional `is_active` query parameter SHALL filter results. Only the requesting user's records SHALL be returned.

#### Scenario: List all definitions
- **WHEN** an authenticated user sends GET `/api/v1/checkin-fields`
- **THEN** the system SHALL return HTTP 200 with all definitions for that user

#### Scenario: Filter by active status
- **WHEN** an authenticated user sends GET `/api/v1/checkin-fields?is_active=true`
- **THEN** the system SHALL return only definitions with `is_active=true`

### Requirement: Update a field definition
The system SHALL allow an authenticated user to update `is_active` of an existing definition via PATCH `/api/v1/checkin-fields/{id}`. The `field_name` and `field_type` fields SHALL be immutable after creation — `field_name` references stored JSONB keys in `DailyCheckin.custom_metrics` and changing it would orphan historical data. `field_type` immutability preserves historical metric type contracts. The PATCH endpoint SHALL reject any attempt to modify `field_name` or `field_type` with HTTP 422.

#### Scenario: Deactivate a field
- **WHEN** an authenticated user sends PATCH `/api/v1/checkin-fields/{id}` with `{"is_active": false}`
- **THEN** the system SHALL update the field and return HTTP 200

#### Scenario: field_type change rejected
- **WHEN** an authenticated user sends PATCH `/api/v1/checkin-fields/{id}` with `{"field_type": "boolean"}`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity indicating `field_type` is immutable

#### Scenario: Cross-user update rejected
- **WHEN** a user sends PATCH `/api/v1/checkin-fields/{id}` where the definition belongs to another user
- **THEN** the system SHALL return HTTP 404

## Design Note: No DELETE endpoint (by design)

Field definitions cannot be deleted — only deactivated. This is intentional: existing `DailyCheckin.custom_metrics` JSONB blobs reference field names by string key. Deleting a definition would orphan historical data with no schema to interpret it. Deactivation preserves the audit trail while blocking the field from new check-ins. To "reuse" a field name, the user reactivates the existing definition. See `design.md` D10.

---

#########################
# openspec/changes/daily-checkin-system/specs/checkin-screenshot-upload/spec.md
#########################

## ADDED Requirements

### Requirement: Generate a presigned screenshot upload URL
The system SHALL provide a POST `/api/v1/checkins/screenshot-upload-url` endpoint that generates a short-lived (≤ 15 minutes) presigned PUT URL for direct upload to the configured object storage. The response SHALL include the presigned URL and the final public URL of the uploaded object. No file bytes SHALL pass through the API server. The endpoint SHALL require authentication.

#### Scenario: Successful presigned URL generation
- **WHEN** an authenticated user sends POST `/api/v1/checkins/screenshot-upload-url` with `{"filename": "screenshot.png", "content_type": "image/png"}`
- **THEN** the system SHALL return HTTP 200 with a `presigned_url` (for PUT) and a `public_url` (the final storage URL)

#### Scenario: Unsupported content type rejected
- **WHEN** an authenticated user sends a request with `content_type` not in the allowed image MIME types (`image/png`, `image/jpeg`, `image/webp`)
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

#### Scenario: Storage backend not configured
- **WHEN** the storage backend is not configured and an authenticated user requests a presigned URL
- **THEN** the system SHALL return HTTP 503 Service Unavailable with a message indicating object storage is not configured

### Requirement: Validate screenshot URL domain on check-in save
The system SHALL validate that any URL in the `screenshot_urls` field of a `DailyCheckin` has a prefix matching the configured `STORAGE_PUBLIC_URL` setting before persisting. This prevents storing arbitrary external URLs as screenshots.

#### Scenario: Valid storage URL accepted
- **WHEN** an authenticated user submits a check-in with `screenshot_urls: ["https://storage.example.com/user-uploads/abc.png"]` and `STORAGE_PUBLIC_URL=https://storage.example.com`
- **THEN** the system SHALL accept and persist the URL

#### Scenario: External URL rejected
- **WHEN** an authenticated user submits a check-in with `screenshot_urls: ["https://external-site.com/image.png"]`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity indicating the URL is not from the configured storage domain

### Requirement: screenshot_urls field rejected when storage is not configured
When `STORAGE_PUBLIC_URL` is not set, the `screenshot_urls` field is unavailable. The system SHALL reject any check-in creation or update that includes a non-empty `screenshot_urls` array.

#### Scenario: Non-empty screenshot_urls rejected without storage config
- **WHEN** `STORAGE_PUBLIC_URL` is not configured and an authenticated user submits `screenshot_urls: ["https://any-url.com/img.png"]`
- **THEN** the system SHALL return HTTP 422 with `{"detail": "screenshot_urls is not available: object storage is not configured"}`

#### Scenario: Empty screenshot_urls always accepted
- **WHEN** `STORAGE_PUBLIC_URL` is not configured and an authenticated user submits `screenshot_urls: []` or omits the field entirely
- **THEN** the system SHALL accept the request normally — the absence of storage config does not affect check-ins without screenshots

---

#########################
# openspec/changes/daily-checkin-system/specs/daily-checkin/spec.md
#########################

## ADDED Requirements

### Requirement: Create a daily check-in
The system SHALL allow an authenticated user to create exactly one `DailyCheckin` record per calendar date. The `date` field SHALL be required and in ISO 8601 date format (YYYY-MM-DD). All other fields are optional: `market_phase` (string referencing an active `MarketPhaseDefinition.name` — may be omitted or `null` when the trader has not yet assessed the market, e.g. a morning check-in before market open), `notes` (text, max 10,000 characters), `news_links` (array of strings), `screenshot_urls` (array of strings), `custom_metrics` (JSONB object). A second check-in for the same user and date SHALL be rejected.

**Rationale for optional `market_phase`**: Traders in time zones where the market opens hours after their morning routine (e.g. European traders trading US markets) routinely create check-ins before market open and update `market_phase` later via PATCH once the market context is clear. Requiring the field at creation would block this workflow.

#### Scenario: Successful creation without market_phase
- **WHEN** an authenticated user sends POST `/api/v1/checkins` with a valid `date` and no `market_phase`
- **THEN** the system SHALL persist the record with `market_phase = null` and return HTTP 201

#### Scenario: Successful creation with market_phase
- **WHEN** an authenticated user sends POST `/api/v1/checkins` with a valid `date` and a `market_phase` that matches an active `MarketPhaseDefinition` name for that user
- **THEN** the system SHALL persist the record and return HTTP 201 with the created check-in

#### Scenario: Duplicate date rejected
- **WHEN** an authenticated user sends POST `/api/v1/checkins` with a `date` for which a check-in already exists
- **THEN** the system SHALL return HTTP 409 Conflict

#### Scenario: Unknown market_phase rejected
- **WHEN** an authenticated user sends POST `/api/v1/checkins` with a non-null `market_phase` value that does not match any active `MarketPhaseDefinition` name for that user
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity identifying the unknown phase name

#### Scenario: Inactive market_phase rejected
- **WHEN** an authenticated user sends POST `/api/v1/checkins` with a `market_phase` that exists but is inactive (`is_active=false`)
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

#### Scenario: screenshot_urls rejected when storage not configured
- **WHEN** `STORAGE_PUBLIC_URL` is not set and an authenticated user submits a non-empty `screenshot_urls` array
- **THEN** the system SHALL return HTTP 422 with a message indicating screenshot storage is not configured

#### Scenario: news_links with invalid URL rejected
- **WHEN** an authenticated user submits `news_links` containing a non-URL string (e.g. `"not a url"`)
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity indicating the invalid entry

#### Scenario: news_links exceeds max count rejected
- **WHEN** an authenticated user submits `news_links` with more than 10 entries
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

### Requirement: Validate custom_metrics against field definitions
The system SHALL validate the `custom_metrics` JSONB payload at the service layer before persisting. Each key in `custom_metrics` SHALL correspond to a `field_name` of an active `CheckinFieldDefinition` owned by the requesting user. Each value SHALL match the `field_type` declared in that definition: `integer` fields SHALL only accept integer values; `boolean` fields SHALL only accept boolean values. Keys not present in active definitions SHALL be rejected. Inactive fields SHALL be treated as unknown and rejected.

#### Scenario: Valid integer metric accepted
- **WHEN** an authenticated user submits `custom_metrics: {"mood-level": 7}` and an active definition with `field_name="mood-level"`, `field_type="integer"` exists for that user
- **THEN** the system SHALL persist the check-in and return HTTP 201

#### Scenario: Unknown key rejected
- **WHEN** an authenticated user submits `custom_metrics: {"unknown-key": 5}` and no active definition for `"unknown-key"` exists for that user
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity with a message identifying the unknown key

#### Scenario: Type mismatch rejected
- **WHEN** an authenticated user submits `custom_metrics: {"rule-followed": 42}` and an active definition with `field_type="boolean"` exists for `"rule-followed"`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity indicating the type mismatch

#### Scenario: Inactive field rejected
- **WHEN** an authenticated user submits `custom_metrics: {"focus": 8}` and the definition for `"focus"` has `is_active=false`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

### Requirement: Retrieve a daily check-in by date
The system SHALL allow an authenticated user to retrieve their check-in for a specific date via GET `/api/v1/checkins/{date}`. Access SHALL be restricted to the requesting user's own records.

#### Scenario: Check-in found
- **WHEN** an authenticated user sends GET `/api/v1/checkins/2025-04-30` and a check-in for that date exists for that user
- **THEN** the system SHALL return HTTP 200 with the full check-in record including `custom_metrics`

#### Scenario: Check-in not found
- **WHEN** an authenticated user sends GET `/api/v1/checkins/2025-04-30` and no check-in for that date exists
- **THEN** the system SHALL return HTTP 404

#### Scenario: Cross-user access denied
- **WHEN** user A has a check-in on date X, and user B sends GET `/api/v1/checkins/X`
- **THEN** the system SHALL return HTTP 404 (not HTTP 403, to avoid leaking existence)

### Requirement: Update a daily check-in
The system SHALL allow an authenticated user to update an existing check-in via PATCH `/api/v1/checkins/{date}`. Partial updates SHALL be supported; fields not included in the request SHALL retain their existing values. `custom_metrics` updates SHALL be fully validated against the user's active field definitions at the time of the update.

#### Scenario: Partial update of notes
- **WHEN** an authenticated user sends PATCH `/api/v1/checkins/2025-04-30` with only `{"notes": "Updated note"}`
- **THEN** the system SHALL update only `notes` and return HTTP 200 with the full updated record

#### Scenario: Updating custom_metrics with invalid key rejected
- **WHEN** an authenticated user sends PATCH `/api/v1/checkins/2025-04-30` with `custom_metrics` containing an unknown key
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

### Requirement: Delete a daily check-in
The system SHALL allow an authenticated user to delete their check-in for a specific date via DELETE `/api/v1/checkins/{date}`. Deleting another user's check-in SHALL NOT be possible.

#### Scenario: Successful deletion
- **WHEN** an authenticated user sends DELETE `/api/v1/checkins/2025-04-30` and the check-in exists
- **THEN** the system SHALL delete the record and return HTTP 204 No Content

#### Scenario: Delete non-existent check-in
- **WHEN** an authenticated user sends DELETE `/api/v1/checkins/2025-04-30` and no check-in exists for that date
- **THEN** the system SHALL return HTTP 404

### Requirement: List check-ins with pagination and optional date range filter
The system SHALL allow an authenticated user to list their check-ins via GET `/api/v1/checkins` with optional `from_date` and `to_date` query parameters (ISO 8601 date). Results SHALL be paginated (default page size: 30, maximum: 90) and ordered by date descending. Only the requesting user's records SHALL be returned. The response envelope SHALL use the shape `items`, `next_cursor`, `total`.

**Cursor format**: `next_cursor` is an ISO 8601 date string (e.g. `"2025-03-14"`) representing the date of the last item on the current page. The next page starts exclusively after that date (i.e. `date < cursor_date`). This is safe because `(user_id, date)` is a unique constraint — no tie-breaker is needed. HMAC signing is not required; the date value carries no sensitive information and cannot be manipulated to access other users' data (all queries are already scoped by `user_id`).

**Cursor + filter interaction**: `from_date` / `to_date` filters are applied independently of the cursor. The cursor is always honoured within the active filter window. A cursor from an unfiltered request is valid in a filtered request — it simply returns results after that date within the new filter window (which may be an empty page if the cursor date is outside the window).

#### Scenario: List all check-ins (first page)
- **WHEN** an authenticated user sends GET `/api/v1/checkins` with no filters
- **THEN** the system SHALL return HTTP 200 with the first page of check-ins (up to 30) ordered by date descending, including `next_cursor` (ISO date of the last item) and `total`

#### Scenario: List with date range
- **WHEN** an authenticated user sends GET `/api/v1/checkins?from_date=2025-04-01&to_date=2025-04-30`
- **THEN** the system SHALL return only check-ins within that inclusive date range, paginated

#### Scenario: Cursor-based navigation
- **WHEN** an authenticated user sends GET `/api/v1/checkins?cursor=2025-03-14` using the `next_cursor` from a previous response
- **THEN** the system SHALL return check-ins with `date < 2025-03-14`, ordered by date descending

#### Scenario: Last page
- **WHEN** the current page contains the oldest check-in for the user (within the active filter)
- **THEN** `next_cursor` SHALL be `null`

---

#########################
# openspec/changes/daily-checkin-system/specs/market-phase-definitions/spec.md
#########################

## ADDED Requirements

### Requirement: Create a market phase definition
The system SHALL allow an authenticated user to create a `MarketPhaseDefinition` via POST `/api/v1/market-phases`. The record SHALL require `name` (string, max 50 chars, unique per user globally regardless of `is_active` status, lowercase kebab-case — this is the stable storage key used in `DailyCheckin.market_phase`) and `label` (string, max 100 chars — the human-readable display name). Optional `color_hex` (6-digit hex string, default `#6366f1`). `is_active` SHALL default to `true`.

The `name` field is **immutable after creation**. The `label` and `color_hex` fields are freely editable. A user SHALL NOT be able to create two definitions with the same `name`, even if the existing definition is inactive.

#### Scenario: Successful creation
- **WHEN** an authenticated user sends POST `/api/v1/market-phases` with `name="trending"`, `label="Trending"`, `color_hex="#22c55e"`
- **THEN** the system SHALL persist the definition and return HTTP 201

#### Scenario: Duplicate name rejected (including inactive)
- **WHEN** an authenticated user sends POST `/api/v1/market-phases` with a `name` that already exists for that user (regardless of `is_active`)
- **THEN** the system SHALL return HTTP 409 Conflict

#### Scenario: Invalid name format rejected
- **WHEN** an authenticated user sends POST `/api/v1/market-phases` with `name` containing uppercase letters or spaces
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

### Requirement: List market phase definitions
The system SHALL allow an authenticated user to list their `MarketPhaseDefinition` records via GET `/api/v1/market-phases`. An optional `is_active` query parameter SHALL filter results. Only the requesting user's records SHALL be returned. Results SHALL be ordered by `created_at` ascending (default creation order reflects the user's preferred display order).

#### Scenario: List all definitions
- **WHEN** an authenticated user sends GET `/api/v1/market-phases`
- **THEN** the system SHALL return HTTP 200 with all phase definitions for that user

#### Scenario: Filter by active status
- **WHEN** an authenticated user sends GET `/api/v1/market-phases?is_active=true`
- **THEN** the system SHALL return only definitions with `is_active=true`

### Requirement: Update a market phase definition
The system SHALL allow an authenticated user to update `label`, `color_hex`, or `is_active` via PATCH `/api/v1/market-phases/{id}`. The `name` field SHALL NOT be changeable after creation (it is the storage key used in persisted `DailyCheckin.market_phase` values — changing it would orphan historical records).

#### Scenario: Rename the display label
- **WHEN** an authenticated user sends PATCH `/api/v1/market-phases/{id}` with `{"label": "Strong Trend"}`
- **THEN** the system SHALL update only `label` and return HTTP 200

#### Scenario: Deactivate a phase
- **WHEN** an authenticated user sends PATCH `/api/v1/market-phases/{id}` with `{"is_active": false}`
- **THEN** the system SHALL update `is_active` and return HTTP 200. Existing `DailyCheckin` records that reference this phase name are NOT affected (historical data is preserved).

#### Scenario: name change rejected
- **WHEN** an authenticated user sends PATCH `/api/v1/market-phases/{id}` with `{"name": "new-name"}`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity indicating `name` is immutable

#### Scenario: Cross-user update rejected
- **WHEN** a user sends PATCH `/api/v1/market-phases/{id}` where the definition belongs to another user
- **THEN** the system SHALL return HTTP 404

### Requirement: Default market phase definitions seeded at registration
The system SHALL seed four default `MarketPhaseDefinition` records for every new user within the same database transaction as user registration. Seeding SHALL be idempotent.

#### Scenario: Default phases present after registration
- **WHEN** a new user successfully registers
- **THEN** the system SHALL create four `MarketPhaseDefinition` records: `bullish` (label: "Bullish", color: #22c55e), `bearish` (label: "Bearish", color: #ef4444), `sideways` (label: "Sideways", color: #f59e0b), `volatile` (label: "Volatile", color: #8b5cf6) — all with `is_active=true`

#### Scenario: Registration rollback also rolls back phase seeding
- **WHEN** the user registration transaction fails before commit
- **THEN** no `MarketPhaseDefinition` records SHALL be persisted for that user

### Requirement: market_phase on DailyCheckin is validated against user's active definitions
When creating or updating a `DailyCheckin`, the system SHALL validate that `market_phase` matches the `name` of an active `MarketPhaseDefinition` owned by the requesting user. Validation SHALL load phase definitions inside the same DB transaction as the check-in write.

#### Scenario: Valid phase accepted
- **WHEN** an authenticated user submits a check-in with `market_phase: "bullish"` and an active `MarketPhaseDefinition` with `name="bullish"` exists for that user
- **THEN** the system SHALL persist the check-in

#### Scenario: Unknown phase name rejected
- **WHEN** an authenticated user submits a check-in with `market_phase: "TRENDING"` and no active definition with `name="TRENDING"` exists
- **THEN** the system SHALL return HTTP 422 with a message identifying the unknown phase name

#### Scenario: Historical check-ins with deactivated phase are preserved
- **WHEN** a `MarketPhaseDefinition` is deactivated after check-ins were recorded using that phase name
- **THEN** existing `DailyCheckin` records retaining that phase name SHALL remain intact and readable

---

#########################
# openspec/changes/daily-checkin-system/tasks.md
#########################

## 1. Database Models & Migration

- [x] 1.1 Create `CheckinFieldDefinition` SQLAlchemy ORM model with columns: `id`, `user_id` (FK → users), `field_name` (VARCHAR, unique per user enforced at DB level via UniqueConstraint), `field_type` (Python enum: `integer`, `boolean`), `is_active` (bool, default True), `created_at`
- [x] 1.2 Create `MarketPhaseDefinition` SQLAlchemy ORM model with columns: `id`, `user_id` (FK → users), `name` (VARCHAR, unique per user enforced at DB level via UniqueConstraint — this is the stable storage key), `label` (VARCHAR — display name, user-editable), `color_hex` (VARCHAR, default `#6366f1`), `is_active` (bool, default True), `created_at`
- [x] 1.3 Create `DailyCheckin` SQLAlchemy ORM model with columns: `id`, `user_id` (FK → users), `date` (Date), `market_phase` (VARCHAR, **nullable** — validated at service layer against `MarketPhaseDefinition.name` only when non-null, NOT a PG enum), `notes` (Text, nullable), `news_links` (ARRAY of Text), `screenshot_urls` (ARRAY of Text), `custom_metrics` (JSONB, nullable), `created_at`, `updated_at`
- [x] 1.4 Add `UniqueConstraint('user_id', 'date')` to `DailyCheckin`
- [x] 1.5 Generate Alembic schema migration: create `checkin_field_definitions` table, then `market_phase_definitions` table, then `daily_checkins` table
- [x] 1.6 Generate a second Alembic **data migration** that seeds default rows for all existing users using `INSERT ... ON CONFLICT DO NOTHING`: three `CheckinFieldDefinition` rows (`mood-level` integer, `focus` integer, `rule-followed` boolean) and four `MarketPhaseDefinition` rows (`bullish`/Bullish/#22c55e, `bearish`/Bearish/#ef4444, `sideways`/Sideways/#f59e0b, `volatile`/Volatile/#8b5cf6)
- [x] 1.7 Apply both migrations locally and verify tables, constraints, and backfill data

## 2. Pydantic Schemas

- [x] 2.1 Create `CheckinFieldDefinitionCreate` schema: `field_name` (str, max 100, kebab-case validated), `field_type` (FieldTypeEnum: `integer | boolean`)
- [x] 2.2 Create `CheckinFieldDefinitionUpdate` schema: optional `is_active` only; `field_name` and `field_type` excluded (both immutable — `field_name` references stored JSONB keys in `custom_metrics` and must not change post-creation)
- [x] 2.3 Create `CheckinFieldDefinitionRead` schema: all fields including `id`, `user_id`, `created_at`
- [x] 2.4 Create `MarketPhaseDefinitionCreate` schema: `name` (str, max 50, kebab-case validated), `label` (str, max 100), optional `color_hex` (6-digit hex, default `#6366f1`)
- [x] 2.5 Create `MarketPhaseDefinitionUpdate` schema: optional `label`, optional `color_hex`, optional `is_active`; `name` excluded (immutable)
- [x] 2.6 Create `MarketPhaseDefinitionRead` schema: all fields including `id`, `user_id`, `created_at`
- [x] 2.7 Create `DailyCheckinCreate` schema: `date` (date, required), optional `market_phase` (str | None — validated at service layer only when non-null), optional `notes` (max 10,000 chars), optional `news_links` (list of `AnyHttpUrl`, max 10 entries), optional `screenshot_urls` (list[str]), optional `custom_metrics` (dict[str, int | bool])
- [x] 2.8 Create `DailyCheckinUpdate` schema: all fields optional (for PATCH); same constraints as Create apply to provided fields
- [x] 2.9 Create `DailyCheckinRead` schema: full response including `id`, `user_id`, all fields
- [x] 2.10 Create `ScreenshotUploadUrlRequest` and `ScreenshotUploadUrlResponse` schemas
- [x] 2.11 Create `DailyCheckinListResponse` schema: `items: list[DailyCheckinRead]`, `next_cursor: date | None` (ISO 8601 date of the last item on the page — `null` on the last page), `total: int`

## 3. Repository Layer

- [x] 3.1 Create `CheckinFieldDefinitionRepository` with methods: `create`, `get_by_id`, `list_by_user` (with optional `is_active` filter), `update`, `get_by_name_and_user`, `seed_defaults(user_id, session)` (INSERT ... ON CONFLICT DO NOTHING for three default fields)
- [x] 3.2 Create `MarketPhaseDefinitionRepository` with methods: `create`, `get_by_id`, `list_by_user` (with optional `is_active` filter), `update`, `get_by_name_and_user`, `seed_defaults(user_id, session)` (INSERT ... ON CONFLICT DO NOTHING for four default phases)
- [x] 3.3 Create `DailyCheckinRepository` with methods: `create`, `get_by_date_and_user`, `list_by_user` (optional `from_date`/`to_date` filters; optional `cursor: date` — returns records with `date < cursor` ordered by `date DESC`; `limit` parameter), `update`, `delete`

## 4. Service Layer

- [x] 4.1 Create `CheckinFieldDefinitionService` with methods: `create_field`, `list_fields`, `update_field` (enforce `field_name` and `field_type` immutability — only `is_active` is updatable via PATCH; enforce `field_name` unique globally per user including inactive)
- [x] 4.2 Create `MarketPhaseDefinitionService` with methods: `create_phase`, `list_phases`, `update_phase` (enforce `name` immutability; enforce `name` unique globally per user including inactive)
- [x] 4.3 Create `DailyCheckinService` with methods: `create_checkin`, `get_checkin`, `list_checkins`, `update_checkin`, `delete_checkin`
- [x] 4.4 Implement `_validate_market_phase(user_id, market_phase, session)` private method in `DailyCheckinService`: called **only when `market_phase` is non-null**. Load active `MarketPhaseDefinition` records within the same transaction, validate `market_phase` matches a `name` — raise HTTP 422 with the unknown phase name identified on failure. When `market_phase` is `null` or omitted, skip validation entirely.
- [x] 4.5 Implement `_validate_custom_metrics(user_id, metrics, session)` private method in `DailyCheckinService`: load active `CheckinFieldDefinition` records within the same transaction, validate all keys exist and types match — raise HTTP 422 with field-level error messages on failure
- [x] 4.6 Implement `generate_screenshot_upload_url(user_id, filename, content_type)` in a new `StorageService`: validate content type allowlist (`image/png`, `image/jpeg`, `image/webp`), generate presigned PUT URL, return presigned + public URL; raise HTTP 503 if storage not configured
- [x] 4.7 Implement screenshot URL domain validation in `DailyCheckinService`: validate each `screenshot_url` prefix against `settings.STORAGE_PUBLIC_URL` before persisting; if `STORAGE_PUBLIC_URL` is not set and a non-empty `screenshot_urls` array is submitted, raise HTTP 422

## 5. Registration Hook

- [x] 5.1 Inject `CheckinFieldDefinitionRepository` and `MarketPhaseDefinitionRepository` into `auth_service.register()`
- [x] 5.2 Call `seed_defaults(user_id, session)` for **both** repositories after the user record is persisted, before commit, within the same transaction

## 6. API Routes

- [x] 6.1 Create `/api/v1/checkin-fields` router with: `POST /` (create), `GET /` (list with `?is_active=` filter), `PATCH /{id}` (update)
- [x] 6.2 Create `/api/v1/market-phases` router with: `POST /` (create), `GET /` (list with `?is_active=` filter), `PATCH /{id}` (update)
- [x] 6.3 Create `/api/v1/checkins` router with routes in this exact order: (1) `POST /screenshot-upload-url`, (2) `POST /` (create), (3) `GET /` (list with `?from_date=&to_date=&cursor=&limit=`), (4) `GET /{date}`, (5) `PATCH /{date}`, (6) `DELETE /{date}`. **Route order is critical**: the static path `screenshot-upload-url` MUST be defined before the `{date}` path-parameter route in the same router file; otherwise FastAPI matches the literal string as a date value and returns 422.
- [x] 6.4 Register all three routers in `app/api/v1/router.py`
- [x] 6.5 Ensure all routes require authentication (`Depends(get_current_user)`)

## 7. Storage Configuration

- [x] 7.1 Add `STORAGE_BACKEND`, `STORAGE_BUCKET`, `STORAGE_PUBLIC_URL`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_ENDPOINT_URL` to `app/core/config.py` (all optional, with `None` defaults)
- [x] 7.2 Implement `StorageService` using `boto3` (or `aiobotocore`) to generate presigned PUT URLs; return HTTP 503 if `STORAGE_BACKEND` is not set
- [x] 7.3 Add `boto3` (or `aiobotocore`) to project dependencies via `uv add`

## 8. Tests

- [x] 8.1 Unit tests for `_validate_market_phase`: unknown phase name → 422, inactive phase → 422, valid phase → accepted, `null` market_phase → validation skipped (no error)
- [x] 8.2 Unit tests for `_validate_custom_metrics`: unknown key, type mismatch (int vs bool), inactive field, valid payload, empty payload
- [x] 8.3 Unit tests for screenshot URL domain validation: valid URL accepted, external URL rejected, `STORAGE_PUBLIC_URL` not configured → non-empty `screenshot_urls` rejected, empty `screenshot_urls` always accepted
- [x] 8.4 Unit tests for `news_links` validation: valid URL accepted, non-URL string rejected, more than 10 entries rejected
- [x] 8.5 Integration tests for check-in CRUD: create without market_phase → 201 with `market_phase=null`, create with valid market_phase → 201, create with unknown market_phase → 422, PATCH to set market_phase after creation → 200, read, update, delete, duplicate date returns 409, cross-user returns 404
- [x] 8.6 Integration tests for check-in list pagination: first page, cursor navigation, date range filter, empty result
- [x] 8.7 Integration tests for field definition CRUD: create, list with filter, update, duplicate name (active or inactive) returns 409, field_type change rejected
- [x] 8.8 Integration tests for market phase definition CRUD: create, list with filter, update label/color, deactivate, name change rejected, duplicate name (active or inactive) returns 409
- [x] 8.9 Integration test for registration: new user has default field definitions and default market phase definitions seeded
- [x] 8.10 Integration test for backfill migration: existing user in test DB gets default rows for both entities after migration
- [x] 8.11 Integration test for screenshot upload URL endpoint: valid request, unsupported content type, storage not configured

## 9. OpenAPI Annotations

- [x] 9.1 Add `summary`, `description`, and `response_model` to all new route handlers
- [x] 9.2 Add `Field(description=...)` to all new Pydantic schema fields
- [x] 9.3 Regenerate frontend OpenAPI client (`openapi-sync` skill)

---

