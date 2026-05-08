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
