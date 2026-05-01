## 1. Database & Backend Models

- [x] 1.1 Create Alembic migration to add JSONB `image_urls` (defaulting to empty list `[]`) to the `trades` table.
- [x] 1.2 Update SQLAlchemy `Trade` model to include the `image_urls` column.
- [x] 1.3 Update Pydantic schemas (`TradeCreate`, `TradeUpdate`, `TradeRead`) to support `image_urls` as `list[str]`.

## 2. API Endpoints & Validation

- [x] 2.1 Implement `/api/v1/trades/upload-url` endpoint (POST) for generating S3 presigned PUT URLs, reusing existing S3 service logic.
- [x] 2.2 Add Pydantic validation to ensure incoming `image_urls` in updates start with the configured `STORAGE_PUBLIC_URL` when present.
- [x] 2.3 Ensure API returns HTTP 501 when requesting an upload URL and `STORAGE_PUBLIC_URL` is empty.
- [x] 2.4 Ensure API returns HTTP 422 if a user sends a non-empty `image_urls` list while storage is not configured.
- [x] 2.5 Write pytest unit tests covering URL generation, URL validation, and HTTP error scenarios.

## 3. Frontend Integration

- [x] 3.1 Regenerate frontend API client (`openapi-ts`) using `openapi-sync` to expose the new upload endpoint and `image_urls` fields.
- [x] 3.2 Update trade detail UI component to display uploaded images using an image gallery/lightbox.
- [x] 3.3 Add image upload widget to the trade form (or edit mode), handling the 2-step S3 upload (request presigned URL -> PUT file).
- [x] 3.4 Support removing an image from the UI (which updates the `image_urls` array on save).
- [x] 3.5 Write React Testing Library and/or Playwright tests for uploading and viewing trade images.

## 4. Deployment & Documentation

- [x] 4.1 Update `docker-compose.yml` and related environment templates (`.env.example`) to ensure S3/MinIO storage backend configurations are clearly documented for trade image uploads.
- [x] 4.2 Update `README.md` to document the new trade attachment feature and necessary S3 configuration requirements.
- [x] 4.3 Update architecture documentation (e.g. `docs/dev-guide.md` or `AGENTS.md`) to reflect the reusable S3 upload flow across different domain entities (Check-ins and Trades).
