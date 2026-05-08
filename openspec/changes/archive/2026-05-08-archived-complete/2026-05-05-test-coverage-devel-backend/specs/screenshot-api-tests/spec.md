## ADDED Requirements

### Requirement: Screenshot upload attaches image to trade
The system SHALL accept a multipart upload, store the file, and append the URL to `trade.image_urls`.

#### Scenario: POST uploads file and returns updated trade
- **WHEN** an authenticated owner POSTs a valid PNG file to `/trades/{trade_id}/screenshots`
- **THEN** the response is 201 and the returned `TradeRead.image_urls` contains the new URL

### Requirement: Screenshot upload enforces file size limit
The system SHALL reject uploads exceeding `SCREENSHOT_MAX_FILE_SIZE_MB` megabytes.

#### Scenario: Oversized file returns 413
- **WHEN** an authenticated user uploads a file exceeding the configured max size
- **THEN** the response is 413

### Requirement: Screenshot upload enforces allowed content types
The system SHALL reject uploads with a content type not in `{image/jpeg, image/png, image/gif, image/webp}`.

#### Scenario: Disallowed content type returns 415
- **WHEN** an authenticated user uploads a file with `content_type="application/pdf"`
- **THEN** the response is 415

### Requirement: Screenshot upload enforces trade ownership
The system SHALL return 404 when the trade does not belong to the requesting user.

#### Scenario: Non-owner upload returns 404
- **WHEN** a user uploads to a `trade_id` owned by a different user
- **THEN** the response is 404

### Requirement: Screenshot delete removes file URL from trade
The system SHALL remove the URL from `trade.image_urls` and delete the stored file when requested by the trade owner.

#### Scenario: DELETE removes URL from trade
- **WHEN** an authenticated owner DELETEs `/trades/{trade_id}/screenshots/{filename}`
- **THEN** the response is 200 and the URL is no longer in `image_urls`
