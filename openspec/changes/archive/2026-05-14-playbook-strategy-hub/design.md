## Context

Playbooks have `id`, `name`, `description`, `content_markdown`, `target_winrate`, `is_active`. They are user-scoped. The platform already has:

- **Taxonomy system** (`taxonomies` table, `ScopeType = Literal["trades", "checkins", "both"]`): used by trades and check-ins. Scope is a plain string column — not a DB enum.
- **Trade/checkin image upload** (`StorageService`, `TradeScreenshotUploader`, `ScreenshotUploader`): presigned PUT via S3/MinIO, allows `image/png`, `image/jpeg`, `image/webp` (and `image/gif` accepted by the uploader components). Drag-and-drop + paste. Checkin links use a flat URL-only array (`news_links: string[]`) with no label field.
- **Trade taxonomy assignment** (`trade_taxonomies`): join table with scope validation in the service layer.

## Goals / Non-Goals

**Goals**
- Add taxonomy assignment to playbooks (`scope = playbook` or `scope = both`).
- Add image upload/list/delete for playbooks (PNG, JPG, GIF, WebP) — same pattern as trade screenshots.
- Add labeled URL link list for playbooks (label + URL pairs) — deviates from checkin pattern to match mockup UX.
- Enable embedding attachment images in `content_markdown` via stable `ref:<id>` placeholders rendered in preview.
- Refactor the playbook editor UI to the established split-pane layout.

**Non-Goals**
- PDF or document upload — images only.
- Labeled links with rich metadata beyond label + URL.
- Full-text search over image content.
- Attachment ordering/reordering.
- Sharing playbooks between users.

## Decisions

### 1. Taxonomy scope: add `"playbook"` to `ScopeType` — do NOT use `"both"`

**Decision**: `ScopeType` becomes `Literal["trades", "checkins", "playbook", "both"]` where `"both"` means trades + checkins only (existing behavior unchanged). A separate `"playbook"` value is explicit and avoids bloating `"both"` semantics.

**Alternatives considered**:
- Extend `"both"` to mean all three contexts → rejected: it silently changes what existing `"both"` taxonomies are assignable to, breaking scope narrowing logic and existing tests.
- Add `"all"` as an alias → rejected: two "include everything" values is confusing.

**Impact**: `ScopeType` literal must be updated in `schemas/taxonomy.py`, scope-filtering queries in `taxonomy_service.py`, and scope-narrowing validation (must check `playbook_taxonomies` before allowing narrowing from `"playbook"` or `"both"`-extended).

**Risk**: scope narrowing logic currently checks `trade_taxonomies` and `checkin_taxonomies`. It must be extended to also check `playbook_taxonomies`. Missing this causes data integrity violations. → Mitigation: add a spec requirement covering this scenario.

### 2. Playbook image uploads: new `playbook_attachments` table, reuse `StorageService` unchanged

**Decision**: New table `playbook_attachments` with columns: `id (UUID PK)`, `playbook_id (FK → playbooks.id CASCADE)`, `user_id`, `filename`, `storage_url`, `content_type`, `created_at`. Upload flow: client requests presigned PUT URL → uploads directly to S3 → POSTs the returned public URL to register. Images only: PNG, JPG, GIF, WebP. `StorageService._ALLOWED_CONTENT_TYPES` is not changed — the existing set already covers these types.

**Alternatives considered**:
- Add image URLs as a flat array on the `Playbook` row (like trade `image_urls`) → rejected: no per-image metadata, deletion requires URL equality matching, can't support `ref:<id>` in Markdown.
- Multipart upload endpoint → rejected: presigned pattern is established; consistency wins.

**Risk**: `StorageService._generate_upload_url` uses a shared key prefix — playbook images must use a distinct prefix (`playbooks/`) to avoid collisions with trade and checkin objects. → Mitigation: dedicated `generate_playbook_upload_url` method.

### 3. Playbook links: labeled URL list (label + URL)

**Decision**: Store links as a `playbook_links` table: `id (UUID PK)`, `playbook_id (FK CASCADE)`, `user_id`, `label (VARCHAR(200) NOT NULL)`, `url (TEXT NOT NULL)`, `created_at`. Label is required — the mockup shows named entries like "Technical Study" and "Video Tutorial" that cannot be derived from URLs.

**Deviation from checkin pattern**: Checkin `news_links` are URL-only arrays. Playbook links require labels because they reference external studies, tutorials, and broker resources where the URL itself is not user-readable. Consistency with checkins was less important than usability here.

**Why a table and not a JSONB/array column on `playbooks`?** Separate table gives clean per-link DELETE endpoints, consistent audit logging, and avoids full-row updates to mutate a single link.

### 4. Image refs in Markdown: `ref:<attachment_id>` → resolved at render time

**Decision**: Users write `![alt](ref:<uuid>)` in `content_markdown`. The frontend preview renderer intercepts `ref:` URLs and substitutes the `storage_url` from the loaded attachment list. The backend stores the raw markdown as-is — no server-side URL rewriting.

**Why frontend resolution?** Presigned URLs expire. Storing resolved URLs in markdown creates stale links. The frontend already has the attachment list loaded; substitution is O(n) over `<img>` tags.

**Risk**: If the attachment is deleted, `ref:<id>` renders as a broken image. → Mitigation: show a placeholder ("attachment deleted") rather than a broken `<img>`. Out of scope for this change to block on.

### 5. UI layout: 35/65 split, no page heading

**Decision**: Match the established full-width layout pattern (toolbar-integrated title). Left pane: taxonomy multi-select (reuse checkin taxonomy component), image upload zone (`TradeScreenshotUploader` pattern — drag, drop, paste, image-only), URL link list (checkin news-links pattern — input + add button, URL anchors with remove). Right pane: Markdown editor with Write/Preview tabs.

**No new shared components** unless the taxonomy multi-select and attachment uploader are already fully reusable — check existing implementations before creating new abstractions.

## Risks / Trade-offs

- **StorageService unchanged**: no PDF, no new content types. Playbook images use the exact same allowed set as trade images. No risk of breaking existing callers.
- **Taxonomy scope narrowing regression**: extending `ScopeType` affects validation in `taxonomy_service.py`. Any CHECK constraint or validation that does `scope in ("trades", "checkins", "both")` will silently pass `"playbook"` through or reject it depending on implementation. → Mitigation: review all scope validation paths in the service and update together.
- **Ref resolver performance**: if a playbook has 50+ attachments, the frontend resolver iterates the full list per `<img>` tag on every preview render. For normal playbook sizes this is negligible. → No mitigation needed now.

## Migration Plan

1. Alembic migration: add `playbook_taxonomies`, `playbook_attachments`, `playbook_links` tables. Update any DB-level scope check constraints if they exist (verify — scope is a plain `VARCHAR`, no DB enum).
2. Backend: update `ScopeType`, extend `taxonomy_service` scope logic, add three new routers and services.
3. Frontend: regenerate OpenAPI client, implement editor page.
4. No data backfill required. No rollback complexity — all new tables, additive API.

## Open Questions

- Does the existing checkin taxonomy assignment UI component exist as a reusable component, or is it page-specific? Answer determines whether a new component is needed or just a reuse.
- Should `target_winrate` move from the playbook toolbar into the left metadata pane? The issue mockup shows it in the toolbar — follow the mockup.
