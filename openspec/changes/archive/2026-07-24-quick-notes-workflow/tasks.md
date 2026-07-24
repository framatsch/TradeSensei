## 1. Rename main journal field `trade.notes` → `trade.journal`

> Scope: Trade entity only. Do NOT touch `DailyCheckin.notes` or any non-Trade `notes`. Verify each edit site belongs to the Trade entity.

- [x] 1.1 Backend: Create Alembic migration to rename column `trades.notes` → `trades.journal`. Provide a reversible `downgrade()`.
- [x] 1.2 Backend: Rename the ORM attribute `Trade.notes` → `Trade.journal` in `models/trade.py` (leave `Trade.trade_notes` untouched).
- [x] 1.3 Backend: Rename the `notes` field → `journal` on the Trade Pydantic schemas in `schemas/trade.py` (Create/Read/Update and any Trade filter/response schema). Update field descriptions.
- [x] 1.4 Backend: Update `trade_repository.py`, `trade_service.py`, and any Trade references in `daily_checkin_repository.py` — only where they read/write the Trade field; do not change `DailyCheckin.notes`.
- [x] 1.5 Backend: Delete the stray merge artifact `backend/app/schemas/trade.py.orig`.
- [x] 1.6 Frontend: Regenerate the OpenAPI client (`openapi-sync`) — do not hand-edit `*.gen.ts`. Then update `lib/types.ts`: rename the Trade `notes` field → `journal` on the Trade Read/Create/Update interfaces only (leave DailyCheckin types unchanged).
- [x] 1.7 Frontend: In `QualitativeMetadataPanel.tsx`, switch the draft state and save call to read/write `trade.journal` (rename `draftNotes` usage accordingly). Update any tests that assert on `trade.notes`.

## 2. Data migration for existing users

- [x] 2.1 Backend: Create an idempotent Alembic data migration that sets `features['enable_quick_notes'] = true` for all existing users, merging into the existing `features` JSON (never overwriting other flags). Provide a `downgrade()` that removes the key.

## 3. Feature flag registration & gating

- [x] 3.1 Frontend: Register `enable_quick_notes` in `lib/featureFlags.ts` — add it to the `FeatureFlagKey` union and the `FEATURE_FLAGS` array (label + description). It then renders automatically in `FeaturesSettings.tsx`.
- [x] 3.2 Frontend: Gate the Quick Notes button/badge in `TradeRow.tsx` behind `useFeatureFlag("enable_quick_notes")`.
- [x] 3.3 Frontend: Gate the `NoteList` render in `app/dashboard/trades/[id]/page.tsx` behind `useFeatureFlag("enable_quick_notes")`.

## 4. Quick Notes import into Journal (deferred delete on Save)

- [x] 4.1 Frontend: Add an "Import Quick Notes" button to `QualitativeMetadataPanel.tsx`, visible only in edit/"write" mode and when `trade.trade_notes` is non-empty.
- [x] 4.2 Frontend: On click, capture the IDs of the currently present Quick Notes into `importedNoteIds` state, format each note as a Markdown bullet (`* **[HH:MM, Emotion]** Content`, or `* **[HH:MM]** Content` when `emotion` is null; `HH:MM` from `created_at` in local time), and append to the journal draft. Disable the button after import until Save or `trade.id` reset.
- [x] 4.3 Frontend: In `handleSave`, after the `updateTrade` mutation succeeds, delete each note in `importedNoteIds` via `useDeleteNote()` (only those IDs; notes added after import are preserved). Surface delete errors instead of swallowing them, and clear `importedNoteIds` on success.
