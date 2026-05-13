## 1. Database Migration

- [x] 1.1 Create Alembic migration: add `playbook_taxonomies` table (playbook_id FK CASCADE, taxonomy_id FK CASCADE, unique constraint)
- [x] 1.2 Create Alembic migration: add `playbook_attachments` table (id UUID PK, playbook_id FK CASCADE, user_id, filename, storage_url, content_type, created_at)
- [x] 1.3 Create Alembic migration: add `playbook_links` table (id UUID PK, playbook_id FK CASCADE, user_id, label VARCHAR(200) NOT NULL, url TEXT NOT NULL, created_at)

## 2. Taxonomy Scope Extension

- [x] 2.1 Update `ScopeType` in `backend/app/schemas/taxonomy.py` from `Literal["trades", "checkins", "both"]` to `Literal["trades", "checkins", "playbook", "both"]`
- [x] 2.2 Update scope filter query in `taxonomy_service.py` to include `scope = playbook` results when `?scope=playbook` filter is applied
- [x] 2.3 Update scope narrowing validation in `taxonomy_service.py` to check `playbook_taxonomies` before allowing narrowing away from `playbook` or `both`
- [x] 2.4 Update smart-delete logic in `taxonomy_service.py` to check `playbook_taxonomies` count alongside trade/checkin counts

## 3. ORM Models

- [x] 3.1 Create `backend/app/models/playbook_taxonomy.py` (mirrors `checkin_taxonomy.py` pattern)
- [x] 3.2 Create `backend/app/models/playbook_attachment.py`
- [x] 3.3 Create `backend/app/models/playbook_link.py`
- [x] 3.4 Add relationships to `Playbook` model: `taxonomy_assignments`, `attachments`, `links`
- [x] 3.5 Register new models in `backend/app/models/__init__.py`

## 4. Pydantic Schemas

- [x] 4.1 Create `backend/app/schemas/playbook_taxonomy.py`: `PlaybookTaxonomyCreate`, `PlaybookTaxonomyResponse`
- [x] 4.2 Create `backend/app/schemas/playbook_attachment.py`: `PlaybookImageUploadRequest`, `PlaybookImageRegisterRequest`, `PlaybookImageResponse`, `PlaybookImageUploadUrlResponse`
- [x] 4.3 Create `backend/app/schemas/playbook_link.py`: `PlaybookLinkCreate` (label + url), `PlaybookLinkResponse`

## 5. Storage Service

- [x] 5.1 Add `generate_playbook_upload_url()` method to `StorageService` using `playbooks/` key prefix (no new content types — reuse existing `_ALLOWED_CONTENT_TYPES`)

## 6. Repositories

- [x] 6.1 Create `backend/app/repositories/playbook_taxonomy_repository.py`: assign, list, remove, exists
- [x] 6.2 Create `backend/app/repositories/playbook_attachment_repository.py`: create, list, get, delete
- [x] 6.3 Create `backend/app/repositories/playbook_link_repository.py`: create, list, get, delete

## 7. Services

- [x] 7.1 Create `backend/app/services/playbook_taxonomy_service.py`: assign (scope/archive validation), list, remove
- [x] 7.2 Create `backend/app/services/playbook_attachment_service.py`: generate_upload_url (images only), register (URL trust check), list, delete
- [x] 7.3 Create `backend/app/services/playbook_link_service.py`: create (HttpUrl validation, deduplicate), list, delete

## 8. API Routes

- [x] 8.1 Create `backend/app/api/v1/playbook_taxonomies.py` router with: `GET /playbooks/{id}/taxonomies`, `POST /playbooks/{id}/taxonomies`, `DELETE /playbooks/{id}/taxonomies/{taxonomy_id}`
- [x] 8.2 Create `backend/app/api/v1/playbook_attachments.py` router with: `POST /playbooks/{id}/attachments/upload-url`, `POST /playbooks/{id}/attachments`, `GET /playbooks/{id}/attachments`, `DELETE /playbooks/{id}/attachments/{attachment_id}`
- [x] 8.3 Create `backend/app/api/v1/playbook_links.py` router with: `GET /playbooks/{id}/links`, `POST /playbooks/{id}/links`, `DELETE /playbooks/{id}/links/{link_id}`
- [x] 8.4 Register three new routers in `backend/app/api/v1/__init__.py` or the main router include file

## 9. OpenAPI Sync

- [x] 9.1 Run `openapi-sync` skill to regenerate frontend TypeScript client from updated FastAPI spec

## 10. Frontend — Playbook Editor Page

- [x] 10.1 Audit existing playbook editor page location and component structure; identify reusable components (taxonomy multi-select, attachment uploader)
- [x] 10.1a Create editor route `frontend/app/dashboard/library/playbooks/[id]/page.tsx` and add navigation from the list view (row click or Edit button)
- [x] 10.2 Implement split-pane layout (35/65) with toolbar (inline name edit, target winrate field, back control) — no page heading
- [x] 10.3 Implement taxonomy assignment section: multi-select filtered to `scope=playbook`, removable chips, add/remove calls to API
- [x] 10.4 Implement image upload zone: adapt `TradeScreenshotUploader` pattern (drag, drop, paste; PNG/JPG/GIF/WebP; presigned PUT flow; register on completion)
- [x] 10.5 Implement image list: filename display, thumbnail with lightbox on click (adapt `TradeImageGallery` pattern), delete button
- [x] 10.6 Implement URL link list: URL input + add button (Enter key supported), truncated anchor list with remove — matches checkin news-links UI exactly
- [x] 10.7 Implement Markdown editor with Write/Preview tabs; in Preview mode, resolve `ref:<uuid>` placeholders to `storage_url` from loaded attachment list; render placeholder for missing refs
- [x] 10.8 Wire Save button to update `content_markdown` (and any other changed playbook fields) via existing PATCH/PUT playbook endpoint
