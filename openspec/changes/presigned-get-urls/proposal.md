## Why

Currently all uploaded images (trade screenshots, daily checkin screenshots, playbook attachments) are stored with static public URLs accessible anonymously. SeaweedFS S3 has `anonymous: Read` configured, allowing unauthenticated GET requests to any object. Trade screenshots containing P&L and positions are publicly readable forever, and leaked URLs expose images to anyone without any way to revoke access. This creates a significant security and privacy risk for sensitive trading data.

## What Changes

- Store `{bucket}/{key}` storage references in the database instead of full public URLs
- Generate short-lived presigned GET URLs on every read request
- Require authenticated API calls to access any image
- Remove anonymous read access from SeaweedFS S3 security configuration
- Migrate existing full URLs in database to S3 keys only
- Update backend services to generate presigned URLs with configurable expiry times
- Update frontend to handle expiring URLs (no long-term caching)

## Capabilities

### New Capabilities
- `presigned-get-urls`: Generate short-lived presigned S3 GET URLs for authenticated image access with configurable expiry times

### Modified Capabilities
<!-- No existing spec-level requirements are changing - this is adding new functionality to existing upload/storage flow -->

## Impact

**Backend**
- `app/services/storage_service.py`: Add presigned GET URL generation, modify upload URL methods to return keys
- `app/schemas/daily_checkin.py`: Change `UploadURLResponse.public_url` to `key`, add presigned URL generation to `DailyCheckinRead`
- `app/schemas/trade.py`: Change `TradeImageUploadResponse.public_url` to `key`, add presigned URL generation to `TradeRead`
- `app/schemas/playbook_attachment.py`: Change `AttachmentUploadResponse.public_url` to `key`, add presigned URL generation to `PlaybookAttachmentRead`
- `app/api/` endpoints: Update upload-url endpoints to return keys, add presigned URL generation to all GET endpoints
- Services: Update checkin, trade, and playbook attachment services to store keys and generate presigned URLs on read

**Database**
- Alembic migration to backfill `daily_checkins.screenshot_urls`, `trades.image_urls`, `playbook_attachments.storage_url` (strip host prefix only, retain `{bucket}/{key}`)


**Frontend**
- Update all components consuming image URLs to handle expiring URLs
- Remove long-term caching of image URLs in localStorage/state
- Ensure fresh API calls on page reload to get new presigned URLs
