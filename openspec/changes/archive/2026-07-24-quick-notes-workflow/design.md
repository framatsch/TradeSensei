## Context
TradeSensei supports two forms of qualitative data on a trade: Quick Notes (the `trade_notes` table / `TradeNote` model — inline short text + optional emotion) and the main markdown journal (currently the `trade.notes` field). The UI already labels the main journal "Journal" (`QualitativeMetadataPanel.tsx` → "Journal", "No journal entry."), but the data model still calls it `notes`, which collides confusingly with `trade.trade_notes`.

Some users prefer the main journal and find Quick Notes distracting, while others use Quick Notes during the day and summarize in the journal later. We want to support both workflows seamlessly, and remove the naming collision by aligning the model with the UI.

The codebase already has a per-user feature-flag system: `UserSettings.features: Record<string, boolean>`, a typed registry in `lib/featureFlags.ts` (`FeatureFlagKey` union + `FEATURE_FLAGS` array), the `useFeatureFlag` hook, and an auto-rendering `FeaturesSettings.tsx` UI. This change reuses that system.

## Goals / Non-Goals

**Goals:**
- Rename the main journal field `trade.notes` → `trade.journal` to match the UI and remove the `notes` vs `trade_notes` collision.
- Register a feature flag `enable_quick_notes` in the existing registry to hide/show Quick Notes.
- Add a button in `QualitativeMetadataPanel` to append formatted Quick Notes into the journal draft, then delete the imported Quick Notes when the trade is saved.

**Non-Goals:**
- Renaming Quick Notes (`trade_notes` / `TradeNote` / `NoteList` etc.) — they keep their current names.
- Touching `DailyCheckin.notes` — it is an unrelated field and stays as `notes`.
- Automatic/continuous syncing between Quick Notes and journal.
- A dedicated atomic backend import endpoint (import is orchestrated client-side; see decision below).

## Decisions

- **Rename target is the Trade journal field only**: `trade.notes` → `trade.journal`, scoped strictly to the Trade entity (column, ORM attribute, Trade Pydantic schemas, generated client, frontend Trade types, and the `QualitativeMetadataPanel` draft state). A repo-wide search-and-replace of `notes` is explicitly forbidden because `DailyCheckin.notes` and possibly other entities also use `notes`. Each change site must be verified to belong to the Trade entity.

- **Flag storage & registry**: The toggle is a key in the existing `UserSettings.features` dict, registered as `enable_quick_notes` in `lib/featureFlags.ts`. Components read it via `useFeatureFlag("enable_quick_notes")`. No new settings schema field is introduced — `features` already exists on both backend and frontend.

- **Default semantics — migrate, do not special-case**: The existing `useFeatureFlag` returns `Boolean(features?.[key])`, i.e. a **missing flag is `false`**. To avoid diverging from this convention, we do **not** invert the check to `!== false`. Instead, an Alembic **data migration** sets `features['enable_quick_notes'] = true` for every existing user, preserving today's behavior. This keeps a single, consistent flag-reading convention across the app.

- **Import → deferred delete on Save**:
  - On "Import Quick Notes", the component captures the array of Quick Note IDs present at that moment (`importedNoteIds`) and appends their formatted content to the journal draft.
  - The "Import Quick Notes" button is disabled after import (until Save or Reset/`trade.id` change) to prevent duplicate appends.
  - Quick Notes are **not** deleted immediately. Deletion happens inside `handleSave`, after the `updateTrade` mutation persists the journal draft, by iterating `importedNoteIds` and calling `useDeleteNote()` per ID. This matches the existing sequential-mutation pattern in `QualitativeMetadataPanel.handleSave`.
  - Only the captured `importedNoteIds` are deleted — Quick Notes created after the import are preserved.
  - If the user abandons the edit (no Save), nothing is deleted and the journal draft changes are discarded on the next `trade.id` effect reset.

- **Import format**: Imported notes are appended as Markdown bullets:
  - With emotion: `* **[HH:MM, Emotion]** Content`
  - Without emotion (`emotion` is nullable): `* **[HH:MM]** Content`
  Timestamps use the note's `created_at` rendered in the user's local time as `HH:MM`.

## Risks / Trade-offs
- **Rename blast radius**: `notes` is an overloaded name (`trade.notes`, `DailyCheckin.notes`). The mitigation is a per-site review rather than a global replace; the Trade-only scope is a hard rule in the tasks.
- **Overwriting journal text**: Import strictly *appends* to the journal draft; it never replaces existing content.
- **Non-atomic delete**: Because delete is a separate call after `updateTrade`, a failure of an individual delete leaves that Quick Note in place while its content is already in the journal → a subsequent re-import could duplicate it. Mitigation: the import button stays disabled after import within the edit session, and delete errors are surfaced (not silently swallowed) so the user can retry. A fully atomic backend endpoint was considered and rejected as over-engineering for this stage.
- **API break**: Renaming the Trade `notes` field → `journal` is a breaking change to the Trade API contract (request and response). Acceptable at this stage; the generated frontend client is regenerated accordingly.
- **Migration reversibility**: The column rename and the user-backfill migration must both provide a working `downgrade()`, and the backfill must merge into existing `features` JSON rather than overwriting it.
