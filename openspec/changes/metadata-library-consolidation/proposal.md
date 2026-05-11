## Why

The frontend Library and Settings currently expose three fragmented metadata systems that all serve similar purposes but operate in silos: the legacy `tags` table (trade-only labels), the legacy `market_phase_definitions` table (check-in-only labels), and the modern `taxonomies` / `annotation_definitions` 2x2 matrix (scoped to trades, check-ins, or both). This fragmentation means users configure the same conceptual thing in two places, and the codebase must maintain three separate CRUD stacks. Consolidating the Library into a three-pillar Metadata Library (Playbooks / Tags / Metrics) built entirely on the modern `taxonomies`+`annotation_definitions` backend eliminates that duplication and gives the Playbook entity the richer content model it needs for strategy documentation.

## What Changes

- **Playbook model extended**: add `content_markdown` (TEXT, optional) and `target_winrate` (NUMERIC 0–1, optional) columns via Alembic migration; update schemas and API.
- **Library > Tags tab**: replace `TagList` (backed by legacy `tags` table) with a new `TaxonomyManager` backed by `taxonomies` API; support `scope` (trades / check-ins / both), color, icon.
- **Library > Metrics tab (new)**: add `/dashboard/library/metrics` route and `AnnotationManager` component backed by `annotation_definitions` API; manage typed variables (int, float, bool, string_enum) with scale labels.
- **Library navigation**: update tab bar to show Playbooks / Tags / Metrics; default redirect to Playbooks.
- **Playbook tab enriched**: add markdown editor (`content_markdown`) and optional `target_winrate` field to the playbook create/edit form.
- **Settings > Check-in cleanup**: remove Market Phases and Custom Metrics sections from `CheckinSettings`; retain only Market Indexes.
- **Scope filtering**: Trade Detail and Check-in Detail views filter taxonomy/annotation dropdowns by `scope` so check-in-only items never appear in trade forms and vice versa.

> ⚠️ **Data Migration & Schema Updates:** No data migration from legacy `tags` is required (greenfield deployment approach). However, the `taxonomies` and `annotation_definitions` tables must be updated to be user-scoped (add `user_id`). Furthermore, logic must be added to generate default taxonomies and annotations when a new user registers.

> ⚠️ **Naming collision:** The issue document uses "Tags" to mean `taxonomies`, but the current Library already has a Tags page backed by the legacy `tags` model. Users and the codebase will have two things called "Tags" until the legacy table is retired. The new tab will replace the old page at the same URL (`/library/tags`).

## Capabilities

### New Capabilities
- `playbook-content-model`: Extend playbook entity with `content_markdown` and `target_winrate`; update API and form UI.
- `taxonomy-library-manager`: Replace legacy tags UI with taxonomy CRUD in the Library (scope-aware, color, icon).
- `annotation-library-manager`: New Library Metrics tab for managing `annotation_definitions` (typed variables, scale labels).

### Modified Capabilities
- `checkin-global-settings`: Remove Market Phases and Custom Metrics sections; retain only Market Indexes.
- `taxonomy-management`: Scope-filtering integration — Trade Detail and Check-in Detail filter by scope.
- `annotation-definition-management`: Scope-filtering integration — same as above for annotations.

## Impact

**Backend**
- `backend/app/models/playbook.py` — add 2 columns
- `backend/app/schemas/playbook.py` — expose new fields in Create/Update/Read
- `backend/app/api/v1/playbooks.py` — no structural change; new fields flow through schemas
- New Alembic migration for playbook columns

**Frontend**
- `frontend/app/dashboard/library/` — new `metrics/` route; update tab nav
- `frontend/components/playbooks/` — add markdown editor and target_winrate field
- `frontend/components/tags/TagList.tsx` — replace with taxonomy-backed manager (same route)
- `frontend/components/` — new `TaxonomyManager` and `AnnotationManager` components
- `frontend/components/settings/CheckinSettings.tsx` — remove market phases + custom metrics sections
- `frontend/hooks/useTaxonomies.ts`, `useAnnotationDefinitions.ts` — already exist; add mutation hooks if missing
- **No new backend endpoints required** — `taxonomies` and `annotation_definitions` APIs are already implemented
