## Why

Traders need to capture visual context (chart screenshots, execution details) directly attached to their trades. Building on the `daily-checkin-system`'s established S3 infrastructure, attaching images directly to a trade provides deep contextual memory for review and journaling processes.

## What Changes

- Implement S3 presigned URL generation for trade image uploads (mirroring the daily check-in flow).
- Update the Trade database model to track multiple attached image URLs.
- Update Trade API endpoints to handle image metadata.
- Implement UI capabilities in the trade detail view to upload, preview, and delete trade images.

## Capabilities

### New Capabilities
- `trade-attachment-system`: Defines the requirements for uploading, associating, and viewing images tied to a specific trade.

### Modified Capabilities
- `trade-management`: Requires updating the Trade entity to accept `image_urls` and managing them via CRUD operations.

## Impact

- **Database**: Adds an array/JSON field for `image_urls` (or a related entity table) to the Trade model.
- **Backend**: New endpoint for trade image presigned URLs; updates to Trade schemas and repositories.
- **Frontend**: Trade detail component requires image upload widget (reuse from check-ins where possible) and an image gallery/lightbox.
- **Infrastructure**: Reuses existing `STORAGE_PUBLIC_URL` and S3 settings.
