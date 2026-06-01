## ADDED Requirements

### Requirement: Storage service generates presigned GET URLs
The storage service SHALL provide a method to generate presigned GET URLs for S3 objects with configurable expiry times.

#### Scenario: Generate presigned URL with default expiry
- **WHEN** storage service generates a presigned GET URL for a key without specifying expiry
- **THEN** system returns a presigned URL with 1 hour (3600 seconds) expiry

#### Scenario: Generate presigned URL with custom expiry
- **WHEN** storage service generates a presigned GET URL for a key with 4 hour expiry
- **THEN** system returns a presigned URL with 4 hour (14400 seconds) expiry

#### Scenario: Presigned URL contains required parameters
- **WHEN** storage service generates a presigned GET URL
- **THEN** URL MUST include AWSAccessKeyId, Expires, and Signature query parameters

### Requirement: Upload URL endpoints return storage references
Upload URL endpoints SHALL return `{bucket}/{key}` storage references instead of public URLs in their responses.

#### Scenario: Daily checkin upload URL endpoint returns storage reference
- **WHEN** client requests upload URL for daily checkin screenshot via POST /checkins/upload-url
- **THEN** response contains `key` field with value in format `{bucket}/{object-key}` (e.g., "tradesensei/daily-checkins/user-id/file.webp")
- **THEN** response does not contain `public_url` field

#### Scenario: Trade image upload URL endpoint returns storage reference
- **WHEN** client requests upload URL for trade screenshot via POST /trades/upload-image-url
- **THEN** response contains `key` field with value in format `{bucket}/{object-key}` (e.g., "tradesensei/trades/user-id/file.webp")
- **THEN** response does not contain `public_url` field

#### Scenario: Playbook attachment upload URL endpoint returns storage reference
- **WHEN** client requests upload URL for playbook attachment via POST /playbook-attachments/upload-url
- **THEN** response contains `key` field with value in format `{bucket}/{object-key}` (e.g., "tradesensei/playbook-attachments/user-id/file.webp")
- **THEN** response does not contain `public_url` field

### Requirement: Database stores bucket and key as combined reference
The database SHALL store `{bucket}/{object-key}` for all image references, enabling presigned URL generation independent of runtime configuration.

#### Scenario: Daily checkin stores screenshot storage references
- **WHEN** system saves a daily checkin with screenshots
- **THEN** `screenshot_urls` JSONB column contains array of strings in `{bucket}/{key}` format
- **THEN** values contain the bucket name as first path segment (e.g., "tradesensei/daily-checkins/...")

#### Scenario: Trade stores image storage references
- **WHEN** system saves a trade with images
- **THEN** `image_urls` JSONB column contains array of strings in `{bucket}/{key}` format
- **THEN** values contain the bucket name as first path segment

#### Scenario: Playbook attachment stores storage reference
- **WHEN** system saves a playbook attachment
- **THEN** `storage_url` VARCHAR column contains string in `{bucket}/{key}` format
- **THEN** value contains the bucket name as first path segment

#### Scenario: Stored reference is self-contained for URL generation
- **WHEN** system generates a presigned URL from a stored reference
- **THEN** bucket is extracted as the first path segment of the stored reference
- **THEN** object key is extracted as everything after the first slash
- **THEN** no runtime settings are required to resolve the reference

### Requirement: Read endpoints return presigned URLs
All GET endpoints that return resources with image fields SHALL generate presigned GET URLs from stored keys.

#### Scenario: Daily checkin read returns presigned URLs
- **WHEN** client fetches daily checkin via GET /checkins/{id}
- **THEN** response `screenshot_urls` field contains array of presigned URLs with expiry parameters
- **THEN** each presigned URL has 1 hour (3600 seconds) expiry

#### Scenario: Trade read returns presigned URLs
- **WHEN** client fetches trade via GET /trades/{id}
- **THEN** response `image_urls` field contains array of presigned URLs with expiry parameters
- **THEN** each presigned URL has 1 hour (3600 seconds) expiry

#### Scenario: Playbook attachment read returns presigned URL
- **WHEN** client fetches playbook attachment via GET /playbook-attachments/{id}
- **THEN** response `storage_url` field contains presigned URL with expiry parameters
- **THEN** presigned URL has 4 hour (14400 seconds) expiry

#### Scenario: List endpoints return presigned URLs
- **WHEN** client fetches list of resources (trades, checkins, playbooks) with images
- **THEN** each resource in the list has presigned URLs generated from stored keys
- **THEN** presigned URLs have appropriate expiry times based on resource type

### Requirement: Presigned URLs require no additional authentication
Presigned URLs SHALL be accessible without additional authentication headers once generated.

#### Scenario: Access image with presigned URL
- **WHEN** client makes GET request to presigned URL
- **THEN** S3 serves the image without requiring Authorization header
- **THEN** request succeeds if made before URL expiry

#### Scenario: Access image after presigned URL expires
- **WHEN** client makes GET request to presigned URL after expiry time
- **THEN** S3 returns 403 Forbidden error

### Requirement: Anonymous S3 access is disabled
SeaweedFS S3 storage SHALL not allow anonymous read access to any objects.

#### Scenario: Anonymous GET request is rejected
- **WHEN** client makes GET request to S3 object URL without presigned parameters
- **THEN** SeaweedFS returns 403 Forbidden error

#### Scenario: Presigned URL requests are allowed
- **WHEN** client makes GET request with valid presigned URL parameters
- **THEN** SeaweedFS serves the object successfully

### Requirement: Database migration backfills existing data as bucket/key references
The system SHALL provide an Alembic migration to convert existing full URLs to `{bucket}/{key}` storage references.

#### Scenario: Migration extracts bucket/key from daily checkin URLs
- **WHEN** migration runs on existing daily_checkins table
- **THEN** full URLs in `screenshot_urls` are converted by stripping only the host prefix (STORAGE_PUBLIC_URL + "/")
- **THEN** resulting value retains bucket name as first path segment (e.g., "tradesensei/daily-checkins/...")

#### Scenario: Migration extracts bucket/key from trade URLs
- **WHEN** migration runs on existing trades table
- **THEN** full URLs in `image_urls` are converted by stripping only the host prefix
- **THEN** resulting value retains bucket name as first path segment

#### Scenario: Migration extracts bucket/key from playbook attachment URLs
- **WHEN** migration runs on existing playbook_attachments table
- **THEN** full URLs in `storage_url` are converted by stripping only the host prefix
- **THEN** resulting value retains bucket name as first path segment

#### Scenario: Migrated reference is immediately usable for presigned URL generation
- **WHEN** migration completes and system generates presigned URL from migrated value
- **THEN** presigned URL is generated correctly without additional data lookups

#### Scenario: Migration handles missing or null URLs
- **WHEN** migration encounters null or empty URL values
- **THEN** migration preserves null/empty values without error
