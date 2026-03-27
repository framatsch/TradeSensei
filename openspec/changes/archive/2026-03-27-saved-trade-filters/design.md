## Context
Saved trade filters should be persisted as named views so users can reuse common trade queries. Filters must be limited to existing trade query fields, be identifiable by UUID, and support both system-provided (read-only) and user-owned entries. System filters are seeded and updated as fixes without versioning.

## Goals
- Persist saved trade filters with UUID identifiers and structured definitions.
- Expose both system and user scopes; enforce read-only system filters.
- Allow name collisions while keeping UUIDs as primary IDs.
- Flag filters that require manual review when field mappings break.
- Keep implementation pragmatic and aligned with existing trade query semantics.

## Non-Goals
- Introducing a new query DSL beyond the current trade query fields.
- Versioning of saved filters or history tracking.
- Complex sharing or team-level scoping beyond system/user.

## Proposed Design

### Data Model
Create a `saved_trade_filters` table with:
- `id` (UUID, primary key)
- `name` (string)
- `scope` (enum: `user`, `system`)
- `definition` (JSONB)
- `owner_id` (UUID, nullable for system)
- `needs_review` (boolean, default false)
- `created_at`, `updated_at` (timestamps)

System filters are identified by `scope = system` and `owner_id = null`. User filters are `scope = user` and `owner_id = <user_id>`.

### Definition Schema
The `definition` is a JSON object that mirrors existing `GET /trades` query parameters. Only supported fields are allowed. No free-form query strings or arbitrary fields.

Example:
```json
{
  "symbol": "AAPL",
  "asset_class": "EQUITY",
  "direction": "LONG",
  "opened_at_from": "2025-01-01T00:00:00Z",
  "opened_at_to": "2025-03-31T23:59:59Z",
  "tag_ids": ["<uuid>", "<uuid>"],
  "tag_filter_mode": "and"
}
```

### API Behavior
- List endpoint returns all system filters and user-owned filters.
- Create allowed only for user scope; system filters are seeded.
- Update/delete allowed only for user-owned filters.
- System filters are read-only; attempts to update/delete return a permission error.

### Field Changes
When query field names change, a migration mapping updates filter definitions. If a field cannot be mapped, the filter is marked `needs_review = true` and returned as such. UI shows a warning badge and prompts the user to edit.

### Seeding
Seed system filters with a stable key (e.g., `system_key`) during migrations or startup tasks. Updates are simple upserts; no versioning.

### UI
Saved filters appear in Trades navigation as Views. System filters show a lock icon and are read-only. Name collisions are permitted; scope and lock icon help disambiguate.

## Risks and Mitigations
- **Field renames**: use a small mapping table in migrations; fallback to `needs_review`.
- **Schema evolution**: keep fields optional and validate strictly; avoid breaking changes.
- **Caching**: clients should invalidate list caches based on `updated_at`.
- **User confusion**: display scope/lock and a warning for `needs_review`.

## Open Questions
- Should `needs_review` be exposed in list responses only, or also on detail? (Default: both.)
- Where should system filter seeds live (migration vs. startup seed job)? (Default: migration.)
