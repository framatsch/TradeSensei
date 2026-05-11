## 1. AnnotationInput Component

- [x] 1.1 Create `frontend/components/trades/AnnotationInput.tsx` — accepts `definition: AnnotationDefinitionResponse` and `value: string | number | boolean | null`, renders: number input for `int`/`float` with `min`/`max` from `scale_labels`, toggle for `bool`, dropdown for `string_enum` (disabled with placeholder if options empty), passes `onChange` callback
- [x] 1.2 Add prop-types / TypeScript types to `AnnotationInput` — `AnnotationInputProps` interface with `definition`, `value`, `onChange`, `disabled` (view mode)

## 2. QualitativeMetadataPanel Component

- [x] 2.1 Create `frontend/components/trades/QualitativeMetadataPanel.tsx` — accepts `trade: TradeResponse`, `portfolioId: string`; renders card with header "Qualitative Analysis & Metadata" and `[✎ Edit]` button
- [x] 2.2 Implement edit mode state in `QualitativeMetadataPanel` — local `isEditing` boolean; `[Save]` and `[Cancel]` buttons visible only in edit mode
- [x] 2.3 Wire `useTaxonomies({ scope: 'trades' })` and `useAnnotationDefinitions({ scope: 'trades' })` into the panel for loading available definitions
- [x] 2.4 Render taxonomy multi-select in the panel — show all available taxonomy names as options; pre-select those in `trade.taxonomies`; filter out archived; handle empty state with placeholder "Select tags…"
- [x] 2.5 Render annotation inputs in the panel — one `AnnotationInput` per definition from `useAnnotationDefinitions`; pre-fill from `trade.annotations`; pass `disabled={!isEditing}`
- [x] 2.6 Render journal textarea in the panel — full-width, pre-filled with `trade.notes`; editable only in edit mode
- [x] 2.7 Implement `handleSave` in the panel:
  - Diff current taxonomy selections vs original → call `assignTaxonomy` for additions, `removeTaxonomy` for removals
  - For each changed annotation → call `assignAnnotation` (new) or `updateAnnotation` (existing)
  - If notes changed → call `updateTrade({ notes: draft.notes })`
  - On success: exit edit mode and invalidate trade query
- [x] 2.8 Implement `handleCancel` — reset draft state to last saved values and set `isEditing = false`
- [x] 2.9 Place Playbook field inside `QualitativeMetadataPanel` (move `InlinePlaybookField` logic into the panel; remove it from `page.tsx` inline definition)

## 3. Performance Card Layout Fix

- [x] 3.1 In `page.tsx`, move the Stop Loss and Take Profit `InlineNumberField` rows to the **top** of the Performance card, before the computed metrics (Realized R, Planned RRR, etc.)

## 4. Page Layout Restructure

- [x] 4.1 Remove `TradeImageGallery` import and render call from `page.tsx`
- [x] 4.2 Move `ExecutionLegsTable` out of the two-column `lg:grid-cols-3` grid — place it in a standalone `<section>` below the grid, full-width
- [x] 4.3 Add `QualitativeMetadataPanel` as a full-width section between the grid and the execution legs section

## 5. Legacy Code Cleanup

- [x] 5.1 Remove `InlineTagsField` inline component definition from `page.tsx`
- [x] 5.2 Remove `InlinePlaybookField` inline component definition from `page.tsx` (now inside `QualitativeMetadataPanel`)
- [x] 5.3 Remove `useTags` import and hook call from `page.tsx`
- [x] 5.4 Remove `usePlaybooks` import and hook call from `page.tsx` (hook now lives in `QualitativeMetadataPanel`)
- [x] 5.5 Remove `TagBadge` import from `page.tsx` if no longer used after cleanup
- [x] 5.6 Remove any state variables in `page.tsx` that were only used by the removed inline components (tag selection state, playbook state)
