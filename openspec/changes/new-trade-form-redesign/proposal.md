## Why

The "New Trade" form has accumulated logical inconsistencies: currency is editable despite being account-owned, the COMBO + Advanced Mode interaction is unconstrained, timestamps are manually entered even when legs provide authoritative data, and the legacy Tags & Playbook UI has been superseded by the 2x2 metadata matrix (Taxonomies + Annotations). The form needs a targeted refactor to close these gaps and align with the current metadata architecture.

## What Changes

- **Remove currency input field**: Currency is a fixed attribute of the linked account and must not be editable during trade creation. Display the account's currency as a read-only label in the header instead.
- **COMBO locks Advanced Mode**: Checking "COMBO position" forces `Advanced Mode (Manual Legs)` to `true` and disables the toggle. Complex multi-leg strategies cannot be represented by a single entry/exit price pair.
- **Timestamp auto-sync in Advanced Mode**: When Advanced Mode is active, `Opened At` and `Closed At` fields are derived automatically from the min/max `executed_at` timestamps across all execution legs. Manual editing of these fields is disabled.
- **Replace Tags & Playbook section with 2x2 Metadata Matrix**: The "Tags & Playbook" panel is replaced by `Trade Taxonomies` (multi-select tags scoped to trades) and `Trade Annotations` (typed key-value inputs: slider, toggle, enum dropdown). Metadata assignment after creation uses existing separate API endpoints.
- **Drag-and-drop screenshot uploader**: Replace the plain `<input type="file">` with a drag-and-drop zone matching the Check-in UI (`ScreenshotUploader` component pattern).
- **Full-width layout**: Widen the form to accommodate the execution legs table without horizontal compression.
- **Schema validation updates**: Update Zod schema refines to correctly handle the COMBO + Advanced Mode combination (no asset_class, no manual qty/price required).

**BREAKING**: The `playbook_id` and `tag_ids` fields are removed from the New Trade form UI. (Note: `tag_ids` will be completely deprecated and removed in subsequent cleanup changes).

## Capabilities

### New Capabilities

- `new-trade-form-redesign`: Overhauled "New Trade" form with corrected COMBO/Advanced-Mode logic, timestamp auto-sync, 2x2 metadata matrix integration, drag-and-drop screenshot upload, and currency as read-only label.

### Modified Capabilities

- `combo-positions`: Requirement change — COMBO now forces Advanced Mode; the toggle cannot be disabled independently.
- `execution-leg-editor`: Requirement change — execution leg timestamps must drive `opened_at`/`closed_at` when Advanced Mode is active.
- `trade-metadata-assignment`: Requirement change — Taxonomies and Annotations are now assignable at trade creation time via a two-step flow (create trade, then assign metadata).

## Impact

- **Frontend only** (no backend schema changes required)
- `frontend/components/trades/TradeForm.tsx` — primary change target
- `frontend/components/trades/` — potential new sub-components (TaxonomySelector, AnnotationInputs, DragDropUploader)
- `frontend/hooks/useTaxonomies.ts`, `useAnnotationDefinitions.ts` — reused for 2x2 panel data fetching
- `frontend/lib/api/types.gen.ts` — no changes (API already supports taxonomy/annotation assignment endpoints)
- Existing `ScreenshotUploader` from `frontend/components/checkin/ScreenshotUploader.tsx` — reused or adapted
- `frontend/__tests__/` — trade form tests will require updates
