## ADDED Requirements

### Requirement: S3 Presigned URL Generation for Trades
The system SHALL provide an endpoint to generate a presigned PUT URL for uploading trade images.

#### Scenario: Successful URL generation
- **WHEN** an authenticated user requests an upload URL with a valid file name and content type
- **THEN** the system returns a presigned S3 PUT URL and a public read URL

#### Scenario: Storage not configured
- **WHEN** the system lacks S3 configuration (`STORAGE_PUBLIC_URL` is empty)
- **THEN** requesting a presigned URL fails with HTTP 503 Service Unavailable

### Requirement: Trade Image URL Validation
The system SHALL accept a list of `image_urls` when updating or creating a trade, and validate their provenance.

#### Scenario: Appending valid image URLs
- **WHEN** a user updates a trade with an `image_urls` array containing URLs that match the `STORAGE_PUBLIC_URL` prefix
- **THEN** the trade is successfully updated

#### Scenario: Rejecting untrusted URLs
- **WHEN** a user provides URLs that do not match the configured `STORAGE_PUBLIC_URL`
- **THEN** the API rejects the request with HTTP 422 Unprocessable Entity

#### Scenario: Rejecting images when unconfigured
- **WHEN** `STORAGE_PUBLIC_URL` is absent, and the user submits a non-empty `image_urls` array
- **THEN** the API rejects the request with HTTP 422, preventing unverified storage usage
