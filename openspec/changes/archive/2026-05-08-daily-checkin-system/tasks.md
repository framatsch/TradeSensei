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
