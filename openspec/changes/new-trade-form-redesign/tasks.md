## 1. Schema and State Management

- [ ] 1.1 Remove `currency` field from `formSchema` Zod schema in `TradeForm.tsx`
- [ ] 1.2 Add `selectedTaxonomyIds` state (`string[]`) and `annotationValues` state (`Record<string, string | number | boolean>`) to `TradeForm`
- [ ] 1.3 Update `formSchema` refine: when `isAdvancedMode === true`, require `executions.length >= 1` (validation error: "At least one execution leg is required in Advanced Mode")
- [ ] 1.4 Add COMBO → Advanced Mode lock logic: when `is_combo` changes to `true`, call `setValue("isAdvancedMode", true)`; render the Advanced Mode toggle as `disabled` when `isCombo === true`
- [ ] 1.5 Extend the existing `useEffect` that syncs leg data: when `isAdvancedMode` and legs exist, compute `min(executed_at)` → `setValue("opened_at", ...)` and `max(executed_at)` → `setValue("closed_at", ...)` (clear `closed_at` when only one leg)
- [ ] 1.6 Disable `opened_at` and `closed_at` inputs when `isAdvancedMode === true`

## 2. Form Layout and Instrument Section

- [ ] 2.1 Wrap the form page container in a full-width layout (remove max-width constraint on the New Trade page/form wrapper)
- [ ] 2.2 Remove the currency `<input>` and `<label>` from the Instrument section
- [ ] 2.3 Add a read-only currency label next to the account selector: derive currency from the selected account object (`accounts.find(a => a.id === accountId)?.currency`)

## 3. Drag-and-Drop Screenshot Uploader

- [ ] 3.1 Create `frontend/components/trades/TradeScreenshotUploader.tsx` — mirrors `ScreenshotUploader` drag-and-drop UI but uses `useTradeImageUploadUrl` hook for upload URL generation
- [ ] 3.2 Support click-to-browse, drag-and-drop, and clipboard paste (⌘V/Ctrl+V); accepted types: image/*; max 20 MB
- [ ] 3.3 Replace the existing `<input type="file">` section in `TradeForm.tsx` with `<TradeScreenshotUploader>` (pass `onUploaded` callback and current `imageUrls`)
- [ ] 3.4 Retain thumbnail grid with remove buttons (existing logic kept, just fed from the new uploader)

## 4. 2x2 Metadata Matrix Panel

- [ ] 4.1 Add `useGetTaxonomies("trades")` call in `TradeForm.tsx` (pass scope param to filter to `trades` + `both` only)
- [ ] 4.2 Add `useGetAnnotationDefinitions("trades")` call in `TradeForm.tsx`
- [ ] 4.3 Create `frontend/components/trades/TaxonomySelector.tsx` — chip-style multi-select panel; accepts `taxonomies`, `selectedIds`, `onChange`; shows empty state when no items
- [ ] 4.4 Create `frontend/components/trades/AnnotationInputs.tsx` — renders one input per definition based on `input_type`: toggle for `bool`, slider/number input for `int`/`float`, select for `string_enum`; accepts `definitions`, `values`, `onChange`
- [ ] 4.5 Replace "Tags & Playbook" section in `TradeForm.tsx` with a "Qualitative Data" section containing `<TaxonomySelector>` and `<AnnotationInputs>` side-by-side

## 5. Post-Creation Metadata Assignment

- [ ] 5.1 After `createMutation.mutate()` succeeds in `onSubmit`, fire `POST /api/v1/trades/{id}/taxonomies` for each `selectedTaxonomyId` (use `assignTradeTaxonomyApiV1TradesTradeIdTaxonomiesPost` from generated client)
- [ ] 5.2 Fire `POST /api/v1/trades/{id}/annotations/{definition_id}` for each non-empty `annotationValues` entry (use `assignTradeAnnotationApiV1TradesTradeIdAnnotationsAnnotationDefinitionIdPost`)
- [ ] 5.3 Run taxonomy and annotation assignments in parallel (`Promise.allSettled`)
- [ ] 5.4 If any assignment rejects, display a non-blocking error notice (e.g. inline warning below the form or a toast); navigate to the trade detail page regardless

## 6. Legacy Cleanup

- [ ] 6.1 Remove `useTags` import and `selectedTagIds` state from `TradeForm.tsx`
- [ ] 6.2 Remove `usePlaybooks` import and `playbook_id` field from the form UI (keep `playbook_id: null` in `onSubmit` payload for API compatibility)
- [ ] 6.3 Remove `TagBadge` import from `TradeForm.tsx` (if unused after removal of Tags section)
- [ ] 6.4 Remove the debug `<div id="debug-executions">` element

## 7. Tests

- [ ] 7.1 Update `frontend/__tests__/components/trades/` — existing TradeForm tests that reference currency input, tags, or playbook fields; update expectations
- [ ] 7.2 Add unit test: COMBO checkbox → Advanced Mode toggle becomes disabled and `isAdvancedMode` is `true`
- [ ] 7.3 Add unit test: execution legs timestamps → `opened_at`/`closed_at` auto-derived and fields are disabled
- [ ] 7.4 Add unit test: zero legs in Advanced Mode → form submit blocked with validation error
- [ ] 7.5 Add unit test: `TaxonomySelector` renders chips and toggles selection
- [ ] 7.6 Add unit test: `AnnotationInputs` renders correct input type per definition
