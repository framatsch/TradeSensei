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
