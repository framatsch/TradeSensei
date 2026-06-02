## 1. Storage Service Changes

- [x] 1.1 Add `generate_presigned_get_url(storage_ref: str, expires_in: int = 3600) -> str` method to StorageService that splits `{bucket}/{key}` and calls `s3_client.generate_presigned_url()`
- [x] 1.2 Modify `_generate_upload_url()` to return `(presigned_put_url, storage_ref)` where `storage_ref = f"{settings.storage_bucket}/{object_key}"`
- [x] 1.3 Modify `upload_file_content()` to return `storage_ref` (`{bucket}/{key}`) instead of `public_url`
- [x] 1.4 Write unit tests for `generate_presigned_get_url()` verifying default (1h) and custom (4h) expiry times
- [x] 1.5 Write unit tests verifying `generate_presigned_get_url()` correctly splits `{bucket}/{key}` and passes both to S3 client
- [x] 1.6 Write unit test verifying `_generate_upload_url()` returns `storage_ref` with bucket as first segment

## 2. Schema Changes

- [x] 2.1 Update `UploadURLResponse` in `app/schemas/daily_checkin.py`: rename `public_url` to `key`
- [x] 2.2 Add `model_validator(mode='after')` to `DailyCheckinRead` to generate presigned URLs from keys with 1h expiry
- [x] 2.3 Update `TradeImageUploadResponse` in `app/schemas/trade.py`: rename `public_url` to `key`
- [x] 2.4 Add `model_validator(mode='after')` to `TradeRead` to generate presigned URLs from keys with 1h expiry
- [x] 2.5 Update `AttachmentUploadResponse` in `app/schemas/playbook_attachment.py`: rename `public_url` to `key`
- [x] 2.6 Add `model_validator(mode='after')` to `PlaybookAttachmentRead` to generate presigned URLs from keys with 4h expiry
- [x] 2.7 Inject `storage_service` into schema validators via context (model_config with arbitrary_types_allowed)

## 3. Service Layer Changes

- [x] 3.1 Update checkin service to store keys instead of full URLs in `screenshot_urls`
- [x] 3.2 Update trade service to store keys instead of full URLs in `image_urls`
- [x] 3.3 Update playbook attachment service to store keys instead of full URLs in `storage_url`
- [x] 3.4 Ensure services pass `storage_service` in serialization context when creating read schemas

## 4. API Endpoint Changes

- [x] 4.1 Verify `POST /checkins/upload-url` returns `key` field instead of `public_url`
- [x] 4.2 Verify `POST /trades/upload-image-url` returns `key` field instead of `public_url`
- [x] 4.3 Verify `POST /playbook-attachments/upload-url` returns `key` field instead of `public_url`
- [x] 4.4 Ensure `GET /checkins/{id}` response includes presigned URLs in `screenshot_urls`
- [x] 4.5 Ensure `GET /checkins` (list) response includes presigned URLs for all checkins
- [x] 4.6 Ensure `GET /trades/{id}` response includes presigned URLs in `image_urls`
- [x] 4.7 Ensure `GET /trades` (list) response includes presigned URLs for all trades
- [x] 4.8 Ensure `GET /playbook-attachments/{id}` response includes presigned URL in `storage_url`

## 5. Database Migration

- [x] 5.1 Create Alembic migration that strips host prefix only (`{STORAGE_PUBLIC_URL}/`) from `daily_checkins.screenshot_urls`, leaving `{bucket}/{key}` intact
- [x] 5.2 Create Alembic migration that strips host prefix only from `trades.image_urls`
- [x] 5.3 Create Alembic migration that strips host prefix only from `playbook_attachments.storage_url`
- [x] 5.4 Add migration logic to handle null/empty URL values gracefully
- [x] 5.5 Test migration locally (docker-compose): insert sample full URLs, run migration, verify `{bucket}/{key}` format
- [x] 5.6 Verify migration downgrade reconstructs full URLs from `{bucket}/{key}` + `STORAGE_PUBLIC_URL`
- [x] 5.7 Write migration test verifying roundtrip: full URL → migrate → `{bucket}/{key}` → generate presigned URL → accessible

## 6. Backend Tests (Local Docker Compose)

- [ ] 6.1 Write integration test: POST /checkins/upload-url returns valid key and presigned PUT URL (runs against local SeaweedFS)
- [ ] 6.2 Write integration test: Upload file via presigned PUT URL to local SeaweedFS, verify it's accessible
- [ ] 6.3 Write integration test: GET /checkins/{id} returns presigned URLs that work against local SeaweedFS
- [ ] 6.4 Write integration test: Presigned URL from GET endpoint allows image download without auth headers from local SeaweedFS
- [ ] 6.5 Write integration test: POST /trades/upload-image-url → upload → GET /trades/{id} full flow against local stack
- [ ] 6.6 Write integration test: POST /playbook-attachments/upload-url → upload → GET /playbook-attachments/{id} full flow against local stack
- [ ] 6.7 Write integration test: Verify presigned URLs expire after configured time (mock time or use very short expiry)
- [ ] 6.8 Write integration test: Verify anonymous GET to S3 URL without presigned params returns 403 (test after local security.json update)
- [x] 6.9 Write unit test: Database stores `{bucket}/{key}` format (not full URL, not key-only) in all three tables
- [x] 6.10 Write unit test: List endpoints (GET /checkins, GET /trades) return presigned URLs for multiple resources
- [ ] 6.11 Write unit test: Stored `{bucket}/{key}` reference generates correct presigned URL when bucket name differs from settings
- [x] 6.12 Ensure pytest fixtures properly configure docker-compose environment (TimescaleDB + SeaweedFS + backend)

## 7. Frontend Impact Analysis

- [x] 7.1 Audit frontend code for long-term caching of image URLs in localStorage or Redux
- [x] 7.2 Verify frontend doesn't cache image URLs beyond React Query default TTL
- [x] 7.3 Update OpenAPI TypeScript client with new schema (run openapi-sync skill)
- [x] 7.4 Update frontend upload components to use `key` field instead of `public_url`
- [ ] 7.5 Test image display in Trade detail view
- [ ] 7.6 Test image display in Daily Checkin view
- [ ] 7.7 Test image display in Playbook attachments view
- [ ] 7.8 Test image refresh after 1 hour (verify page reload fetches new presigned URLs)

## 8. Infrastructure Verification (Local Docker Compose)

- [ ] 8.1 Update local SeaweedFS `security.json` (in docker-compose volume/config) to remove anonymous identity
- [ ] 8.2 Restart docker-compose SeaweedFS container with updated config
- [ ] 8.3 Write integration test: anonymous GET to S3 object URL returns 403 Forbidden with updated security.json
- [ ] 8.4 Write integration test: presigned URL requests succeed against SeaweedFS with anonymous access disabled
- [ ] 8.5 Update `seaweed-security.json` in k3s-deploy repo (infra change for production deployment — done separately by you)

## 9. Local End-to-End Verification

- [x] 9.1 Run database migration against local docker-compose TimescaleDB
- [x] 9.2 Run full pytest suite against local docker-compose stack — all tests pass
- [x] 9.3 Run openapi-sync to regenerate TypeScript client from updated FastAPI spec
- [x] 9.4 Verify frontend builds without TypeScript errors after client update

## 10. Documentation

- [x] 10.1 Update API documentation to reflect `key` field (`{bucket}/{object-key}` format) in upload responses
- [x] 10.2 Document presigned URL expiry times in API docs
- [x] 10.3 Update AGENTS.md storage service patterns if changed
- [x] 10.4 Add entry to CHANGELOG [Unreleased] section
