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
