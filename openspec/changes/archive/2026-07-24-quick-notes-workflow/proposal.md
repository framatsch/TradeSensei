## Why

Users who want to track their thoughts during a trade use "Quick Notes" (a scratchpad) while those who want to perform an after-market review use the detailed "Journal". Currently, the Quick Notes are available to add in the trades table view, but they clutter the user experience for users who only want to use the main journal. Additionally, there is no smooth workflow to transfer the Quick Notes gathered during the day into the main Journal for end-of-day review. This change introduces a feature toggle to disable Quick Notes for purists, and an import workflow to move existing Quick Notes into the main Journal for those who use both.

There is also a naming collision in the data model: the main journal field is `trade.notes` while the Quick Notes relationship is `trade.trade_notes`. The UI already labels the main journal "Journal", so we align the model with the UI by renaming the main journal field `trade.notes` → `trade.journal`. Quick Notes keep their current names (`trade_notes` table, `TradeNote` model) — they are not renamed.

## What Changes

- **Rename the main journal field** `trade.notes` → `trade.journal` (DB column, ORM model, Pydantic schemas, generated OpenAPI client, TypeScript types, and the frontend edit state). This is scoped strictly to the Trade entity and MUST NOT touch `DailyCheckin.notes`, which is an unrelated field.
- **Keep Quick Notes as-is**: `trade_notes` table, `TradeNote` model, `trade.trade_notes` relationship, and the `NoteList`/`NoteForm`/`useNotes` components/hooks are unchanged.
- Register a new key `enable_quick_notes` in the existing feature-flag registry (`lib/featureFlags.ts` `FeatureFlagKey` union + `FEATURE_FLAGS` array) so it renders automatically in the Features settings tab (`FeaturesSettings.tsx`).
- Because the existing feature-flag system treats a missing flag as `false` (`useFeatureFlag` returns `Boolean(features?.[key])`), a **data migration** SHALL set `enable_quick_notes = true` for all existing users so current behavior is preserved.
- Conditionally hide the Quick Notes `+` button in `TradeRow.tsx` based on the flag (via `useFeatureFlag("enable_quick_notes")`).
- Conditionally hide the `NoteList` component in the `TradeDetails` page (`page.tsx`) based on the flag.
- Add an "Import Quick Notes" button in `QualitativeMetadataPanel.tsx` (visible only in edit/"write" mode and when the trade has Quick Notes).
- Clicking the import button appends the trade's Quick Notes to the journal draft textarea, formatted as Markdown bullets with timestamp and (optional) emotion. The button is disabled after import (until Save or Reset) to prevent duplicate appends.
- **Deferred delete on Save**: the import captures the IDs of the Quick Notes that existed at import time. When the user clicks "Save Trade", those exact Quick Notes are deleted (Quick Notes created after the import are preserved). If the user abandons the edit without saving, nothing is deleted.

## Capabilities

### New Capabilities
- `quick-notes-workflow`: Feature toggle to enable/disable Quick Notes visibility, UI integration to import Quick Notes into the main Journal text with deferred delete on Save, and renaming of the main journal field `trade.notes` → `trade.journal`.

### Modified Capabilities

## Impact

- **Database**: Alembic migration to rename the `trades.notes` column → `trades.journal`. Provide a reversible `downgrade()`. A second, idempotent data migration sets `features['enable_quick_notes'] = true` for all existing users (merging into the existing `features` JSON, never overwriting other flags).
- **Backend API**: Rename the `notes` field → `journal` on the Trade ORM model and on the Trade Pydantic schemas (Create/Read/Update and any Trade filter/response schema in `schemas/trade.py`). Update `trade_repository.py`, `trade_service.py`, and `daily_checkin_repository.py` **only where they reference the Trade field** — leave `DailyCheckin.notes` untouched.
  - `backend/app/models/trade.py`, `backend/app/schemas/trade.py`
  - `backend/app/repositories/trade_repository.py`, `backend/app/services/trade_service.py`, `backend/app/repositories/daily_checkin_repository.py` (Trade references only)
  - Remove stray merge artifact `backend/app/schemas/trade.py.orig`
- **Frontend**:
  - Regenerate the OpenAPI client (`lib/api/*.gen.ts`) after the backend rename — do **not** hand-edit generated files.
  - `frontend/lib/types.ts` (rename the Trade `notes` field → `journal` on the Trade Read/Create/Update interfaces; do not touch `DailyCheckin.notes`).
  - `frontend/lib/featureFlags.ts` (register `enable_quick_notes`).
  - `frontend/components/trades/QualitativeMetadataPanel.tsx` (rename `draftNotes` handling to read/write `trade.journal`; add import button + deferred-delete-on-save logic).
  - `frontend/components/trades/TradeRow.tsx` (flag-gate the Quick Notes button).
  - `frontend/app/dashboard/trades/[id]/page.tsx` (flag-gate `NoteList`).
