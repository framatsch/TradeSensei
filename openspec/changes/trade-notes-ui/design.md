## Context

The `notes` API (`GET/POST /trades/{id}/notes`, `PATCH/DELETE /trades/{id}/notes/{note_id}`) is fully implemented. The frontend has `NoteList`, `NoteForm` components and a `useNotes` hook. Notes are currently stored and displayed as plain text. The `TradeTable` has no note column or quick-add functionality.

## Goals / Non-Goals

**Goals:**
- Add server-side 5000-character limit to `TradeNoteCreate.content` and `TradeNoteUpdate.content`
- Add `react-markdown` + `remark-gfm` to frontend for Markdown rendering
- Update `NoteForm` to be a Markdown-aware textarea with character counter and live preview toggle
- Add `QuickNoteInput` component inside `TradeRow` for inline note creation without navigating away
- Display relative timestamps ("2 hours ago") on notes using `date-fns` (already a dependency)
- Split-view Markdown editor on the trade detail note panel (edit / preview tabs)

**Non-Goals:**
- Server-side Markdown sanitization (the frontend renders Markdown; XSS is prevented by `react-markdown`'s sanitization defaults)
- Markdown-to-plain-text search index
- Attachment/image support in notes
- Rich-text WYSIWYG editor (Markdown is sufficient for the target user base)
- Changes to the API response shape (notes are returned as raw Markdown strings; rendering is frontend-only)

## Decisions

### Markdown library: react-markdown vs marked

**Decision**: Use `react-markdown` with `remark-gfm`.

**Rationale**: `react-markdown` renders safely to React elements (no `dangerouslySetInnerHTML`), has built-in XSS protection, supports GitHub Flavored Markdown (tables, task lists, strikethrough) via `remark-gfm`, and is widely used in the React ecosystem. `marked` requires manual sanitization.

### Character limit: frontend-only vs server-side

**Decision**: Enforce the limit server-side (`max_length=5000` on the Pydantic schema) AND show a counter in the frontend.

**Rationale**: Frontend-only limits are trivially bypassed via direct API calls. The server must be the source of truth. The frontend counter improves UX by providing real-time feedback.

### Quick-note in trade row: inline vs modal

**Decision**: Inline expandable input in the `TradeRow` — clicking a "note" icon expands a textarea directly in the row.

**Rationale**: Modals interrupt flow; inline editing within the table is consistent with the existing inline `TradeEditForm`. The quick-note only creates a new note (no edit/delete from the table row — those remain in the detail page).

## Risks / Trade-offs

- [Table layout complexity] Expanding a note row in `TradeTable` increases visual complexity → Expansion is opt-in (click icon); collapsed by default; only shows the first note, not all
- [Character limit breaking change] If any existing note exceeds 5000 chars, the PATCH endpoint would start rejecting updates → Check DB for outliers before deploying; in practice, notes are short annotations
- [react-markdown bundle size] Adds ~15kb gzipped → Acceptable; loaded lazily with `next/dynamic` if needed
