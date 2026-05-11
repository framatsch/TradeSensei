## 1. Backend — User Scoped Taxonomies & Defaults

- [x] 1.1 Write Alembic migration to add `user_id` (UUID, nullable=False, FK to `users.id` with CASCADE) to both `taxonomies` and `annotation_definitions` tables (since we are doing greenfield, we can drop/recreate or just wipe data in the migration if necessary).
- [x] 1.2 Update the `Taxonomy` and `AnnotationDefinition` ORM models in `backend/app/models/` to include `user_id` relationship/mapped column.
- [x] 1.3 Update the `TaxonomyRepository` and `AnnotationDefinitionRepository` to filter by `user_id` for all operations.
- [x] 1.4 Update the backend User registration flow (`backend/app/services/user_service.py` or similar) to automatically create a set of default Taxonomies and Annotation Definitions for the new user.

## 2. Backend — Playbook Model Extension

- [x] 2.1 Write Alembic migration to add `content_markdown` (TEXT nullable) and `target_winrate` (NUMERIC(5,4) nullable, CHECK 0<=value<=1) columns to the `playbooks` table
- [x] 2.2 Add `content_markdown: str | None` and `target_winrate: Decimal | None` to `PlaybookCreate`, `PlaybookUpdate`, and `PlaybookRead` schemas in `backend/app/schemas/playbook.py`
- [x] 2.3 Add the two new columns to the `Playbook` ORM model in `backend/app/models/playbook.py`
- [x] 2.4 Regenerate the frontend OpenAPI client (`openapi-sync`) after backend changes are applied

## 3. Frontend — Library Navigation (Three Tabs)

- [x] 3.1 Add a Metrics tab link to the Library tab bar so it shows Playbooks / Tags / Metrics
- [x] 3.2 Update the Library default redirect in `frontend/app/dashboard/library/page.tsx` to remain `/library/playbooks`

## 4. Frontend — Playbook Form Enrichment

- [x] 4.1 Add a `target_winrate` percentage input (0–100) to the Playbook create/edit form; convert to/from 0–1 on load/submit
- [x] 4.2 Add a `content_markdown` editor section to the Playbook create/edit form using a controlled `<textarea>` for edit mode
- [x] 4.3 Add a "Preview" toggle button that renders the markdown using `react-markdown` with `remark-gfm`

## 5. Frontend — Library Tags Tab (Taxonomy Manager)

- [x] 5.1 Create `frontend/components/library/TaxonomyManager.tsx` — list, create, edit, archive/delete for taxonomies; uses existing `useTaxonomies` hooks; shows name, color swatch, scope badge, icon_identifier
- [x] 5.2 Add scope selector (Trades / Check-ins / Both) to the TaxonomyManager create/edit form
- [x] 5.3 Replace `TagList` with `TaxonomyManager` in `frontend/app/dashboard/library/tags/page.tsx`

## 6. Frontend — Library Metrics Tab (Annotation Manager)

- [x] 6.1 Create `frontend/components/library/AnnotationManager.tsx` — list, create, edit, archive/delete for annotation definitions; uses `useAnnotationDefinitions` hooks; shows name, type badge, scope badge, description
- [x] 6.2 Add type selector (Integer / Float / Boolean / Enum) to the AnnotationManager form; show scale_labels input only when type = Enum
- [x] 6.3 Create `frontend/app/dashboard/library/metrics/page.tsx` route rendering `AnnotationManager`

## 7. Frontend — Settings Check-in Cleanup

- [x] 7.1 Remove the Market Phases section from `frontend/components/settings/CheckinSettings.tsx`
- [x] 7.2 Remove the Custom Metrics section from `frontend/components/settings/CheckinSettings.tsx`
- [x] 7.3 Verify that Market Indexes section still renders correctly after the removals

## 8. Frontend — Scope Filtering in Trade Detail
(Moved to trade-detail-redesign)
