## 1. Playbook Filter Bar Component

- [x] 1.1 Create `frontend/components/playbooks/PlaybookFilterBar.tsx` with collapsible header, active filter counter, status filter ("Active" / "Inactive" / "All"), tag selector, search input, and "Clear all" button
- [x] 1.2 Add unit tests for `PlaybookFilterBar` in `frontend/__tests__/components/playbooks/PlaybookFilterBar.test.tsx`

## 2. Playbook Overview Table Updates

- [x] 2.1 Remove the row delete button and inline confirmation logic from `frontend/components/playbooks/PlaybookList.tsx`, keeping `Edit` as the sole row action
- [x] 2.2 Make the `Status` column in `PlaybookList.tsx` an interactive toggle button that flips `is_active` via `useUpdatePlaybook` with optimistic cache update
- [x] 2.3 Integrate `PlaybookFilterBar` into `PlaybookList.tsx` with client-side filtering by status, tags, and search query
- [x] 2.4 Add interactive column sorting (Name, Created, Status) with direction indicators to `PlaybookList.tsx`
- [x] 2.5 Update unit tests in `frontend/__tests__/components/playbooks/PlaybookList.test.tsx` verifying removal of delete, interactive status toggling, filtering, and sorting

## 3. Playbook Editor Active / Inactive Toggle Flag

- [x] 3.1 Add an "Active / Inactive" toggle control to `frontend/components/playbooks/PlaybookEditorClient.tsx`
- [x] 3.2 Connect the toggle to `useUpdatePlaybook` to persist changes to `is_active`
- [x] 3.3 Ensure the permanent Delete button remains present and functioning in `PlaybookEditorClient.tsx`
- [x] 3.4 Update unit tests in `frontend/__tests__/components/playbooks/PlaybookEditorClient.test.tsx` verifying toggle behavior

## 4. Trade Assignment Selectors Filtering

- [x] 4.1 Filter playbook options in `frontend/components/trades/QualitativeMetadataPanel.tsx` to active playbooks for new selections
- [x] 4.2 Preserve and display assigned inactive playbooks labeled as `(Inactive)` when viewing historical trades
- [x] 4.3 Add tests for playbook filtering in qualitative metadata panel

## 5. Verification

- [x] 5.1 Run frontend unit tests and type checks (`npm test`, `npm run lint`, `npx tsc --noEmit`)
- [x] 5.2 Validate end-to-end user experience across filter bar, list sorting, status toggle, editor, and trade detail
