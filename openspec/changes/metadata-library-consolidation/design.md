## Context

The backend already implements two parallel metadata systems:

1. **Modern 2x2 matrix** (`taxonomies` + `annotation_definitions`) — scope-aware (trades/checkins/both), fully implemented with CRUD APIs, used for trade/check-in assignment but not yet exposed in the Library UI for management.

2. **Legacy check-in system** (`market_phase_definitions` + `checkin_field_definitions`) — managed in Settings > Check-in; narrowly scoped to check-ins only; used by the Check-in form and analytics.

3. **Legacy trade tags** (`tags`) — managed in Library > Tags; trade-only; simple name+color.

The issue asks us to surface the modern system in the Library UI, enrich playbooks, and clean up Settings. Because the legacy systems are still wired to live data paths (check-in forms, analytics attribution), we cannot simply delete them — we need a careful UI handoff.

## Goals / Non-Goals

**Goals:**
- Add `content_markdown` and `target_winrate` to the Playbook model and API
- Build a markdown editor into the Playbook create/edit form
- Replace the Library > Tags page UI with a Taxonomy manager (backed by `taxonomies`)
- Add a new Library > Metrics page backed by `annotation_definitions`
- Strip Settings > Check-in down to Market Indexes only (remove Market Phases and Custom Metrics sections from the UI)
- Filter taxonomy/annotation dropdowns in Trade Detail and Check-in Detail by `scope`

**Non-Goals:**
- Migrating or deleting legacy `tags`, `market_phase_definitions`, or `checkin_field_definitions` data — this is a separate migration change
- Wiring the new taxonomy system into the Check-in form's phase selection (the check-in form still uses `market_phase_definitions` until a migration change deprecates them)
- Redesigning the Check-in system's data model
- Adding icon pickers to the UI (icons are stored as string identifiers; a picker component is out of scope)

## Decisions

### Decision 1: Replace Library > Tags URL in-place, not at a new route

The current `/dashboard/library/tags` page renders `TagList` backed by the legacy `tags` model. We will swap the component to `TaxonomyManager` at the same URL. This is a breaking UI change — users who created legacy tags will no longer see them here.

**Alternative considered:** Add a new `/library/taxonomies` route and keep `/library/tags` as-is. Rejected because it creates more fragmentation, not less.

**Prerequisite:** Before this task is implemented, verify whether any production data exists in the legacy `tags` table. If it does, a data migration (copy to `taxonomies` with `scope=trades`) must be written first and tracked in a separate Alembic migration change.

### Decision 2: Settings > Check-in cleanup is UI-only — no backend changes

We remove the Market Phases and Custom Metrics _UI sections_ from `CheckinSettings.tsx`. The backend endpoints and models remain intact. This unblocks the Library consolidation without risking data loss or breaking the Check-in form which still reads `market_phase_definitions`.

**Trade-off:** The Settings cleanup creates a temporarily orphaned backend (the old endpoints still exist but have no UI). This is intentional — the full deprecation will happen in a follow-up migration change.

### Decision 3: Playbook markdown editor uses a lightweight client-side approach

Use a controlled `<textarea>` for editing and a markdown renderer (e.g., `react-markdown`) for preview, toggled by a Preview button. No WYSIWYG editor dependency.

**Alternative considered:** A rich WYSIWYG editor (TipTap, Quill). Rejected for now — overkill for strategy notes; adds significant bundle weight.

### Decision 4: `target_winrate` stored as NUMERIC(5,4), validated 0–1

Stores values like `0.6000` (60%). The backend validates `0 <= value <= 1`. The UI displays it as a percentage input (0–100) and converts on submit/load.

### Decision 5: Taxonomy scope filtering in dropdowns uses the existing `?scope=` query param

The `taxonomies` and `annotation_definitions` list endpoints already support `?scope=trades|checkins|both`. Trade Detail passes `scope=trades`; Check-in Detail passes `scope=checkins`. The `both` scope appears in both contexts — this is correct by design.

## Risks / Trade-offs

- **[Risk] Legacy `tags` data loss** → Mitigation: Implement the UI swap ONLY after verifying no production data in `tags` table OR after a data migration. Add a guard check before merging.
- **[Risk] Check-in form breaks if Market Phase sections removed from Settings** → Mitigation: Settings cleanup is UI-only; the backend and the Check-in form itself are untouched. Phase selection in the Check-in form still reads `market_phase_definitions`.
- **[Risk] Users confused by "Tags" meaning taxonomies instead of the old tags** → Mitigation: Tab is labeled "Tags" consistently; old data warning can be shown if legacy tags exist.
- **[Risk] `react-markdown` or similar not yet in frontend dependencies** → Mitigation: Check `package.json` before implementing; add via `npm install` if needed.
- **[Trade-off] Metrics tab requires users to understand type/scope concepts** → Accept this complexity; it is inherent to the 2x2 matrix model.

## Migration Plan

1. Backend: Alembic migration to add `content_markdown` and `target_winrate` to `playbooks` table.
2. Backend: Update `PlaybookCreate`, `PlaybookUpdate`, `PlaybookRead` schemas.
3. Frontend (OpenAPI sync): Regenerate client after backend schema change.
4. Frontend: Build `TaxonomyManager` and `AnnotationManager` components.
5. Frontend: Replace `TagList` with `TaxonomyManager` at `/library/tags`.
6. Frontend: Add `/library/metrics` route with `AnnotationManager`.
7. Frontend: Update Library tab navigation.
8. Frontend: Update Playbook form with markdown editor + target_winrate field.
9. Frontend: Strip Market Phases and Custom Metrics from `CheckinSettings.tsx`.
10. Frontend: Wire scope filters into Trade Detail and Check-in Detail dropdowns.

**Rollback:** All changes are additive (backend columns nullable) or UI-only. No destructive DB changes.

## Open Questions

- **Q1: Does any production data exist in the legacy `tags` table?** If yes, a data migration to `taxonomies` is required before step 5 above. Must be resolved before implementing Task: Replace TagList.
- **Q2: Is `react-markdown` (or equivalent) already a dependency?** Check `frontend/package.json`. If not, confirm which library to add.
- **Q3: Should the Playbook markdown field be `content_markdown` (as in the issue) or `description` (renamed)?** The current `description` field is a plain-text 2000-char string. If we add `content_markdown` as a separate column, `description` becomes redundant. Proposal: keep `description` for backwards compatibility and add `content_markdown` as the new primary content field.
