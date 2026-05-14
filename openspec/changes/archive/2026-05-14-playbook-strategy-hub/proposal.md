## Why

Playbooks currently store a name, markdown content, and a target winrate — but lack the organizational and reference infrastructure traders actually use: categorization by strategy type, supporting files (charts, studies), and links to external references. The gap between a playbook entry and a real strategy document makes the feature under-utilized.

## What Changes

- **Taxonomy assignment for playbooks**: introduce `scope = playbook` (or extend to `scope = both` where needed) to the taxonomy system, plus a `playbook_taxonomies` join table and assignment API — mirroring the existing `trade_taxonomies` pattern exactly.
- **Playbook image uploads**: new `playbook_attachments` table for image uploads (PNG, JPG, GIF, WebP) stored in S3/MinIO via presigned URLs — reuses the same `StorageService` and upload pattern as trade and checkin screenshots.
- **Playbook links**: list of external URLs stored on the playbook — same pattern as checkin `news_links` (URL-only, no label field).
- **Image reference in Markdown**: images uploaded as attachments can be embedded in `content_markdown` using a stable `ref:` placeholder (`![alt](ref:<attachment_id>)`) that the preview renderer resolves to the actual URL.
- **Playbook editor UI refactor**: split-pane layout (35/65) with metadata/resources left and Markdown editor right, replacing the current form layout.

**No breaking API changes to existing `/playbooks` endpoints.** New sub-resources are additive.

## Capabilities

### New Capabilities

- `playbook-taxonomy-assignment`: Assign/remove taxonomy tags to a playbook. Requires taxonomy `scope = playbook` or `scope = both`. Mirrors `trade-metadata-assignment` patterns. Creates `playbook_taxonomies` table.
- `playbook-attachment-system`: Upload, list, and delete images scoped to a playbook. S3 presigned PUT flow; supports PNG, JPG, GIF, WebP (same as trade screenshots). Creates `playbook_attachments` table.
- `playbook-link-manager`: Add, list, and delete external URLs for a playbook. URL-only (no label), same pattern as checkin `news_links`. Stored on the playbook row as an array or in a `playbook_links` table.
- `playbook-editor-ui`: Full-width split-pane editor page with taxonomy multi-select, image upload zone (reusing `TradeScreenshotUploader` pattern), URL link list (reusing checkin news-links pattern), and Markdown editor with preview. Uploaded images can be referenced by ID in Markdown preview.

### Modified Capabilities

- `taxonomy-management`: Add `playbook` as a valid `scope` value (currently `trades`, `checkins`, `both` are valid). Scope narrowing rules and delete logic must account for `playbook_taxonomies` assignments.

## Impact

- **Backend**: 3 new tables (`playbook_taxonomies`, `playbook_attachments`, `playbook_links`), Alembic migration, 3 new routers, updated taxonomy scope enum and validation.
- **Frontend**: New playbook editor page, taxonomy multi-select component, file drop zone (reuse or adapt trade attachment UI), link list component, Markdown preview with ref-resolver.
- **Storage**: S3/MinIO dependency for attachments — same config as trade attachments (`STORAGE_PUBLIC_URL`). No new infra.
- **API client**: OpenAPI sync required after backend changes.
