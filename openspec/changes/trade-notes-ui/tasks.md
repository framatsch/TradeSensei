## 1. Backend Schema Changes

- [x] 1.1 Add `max_length=5000` to `TradeNoteCreate.content` in `backend/app/schemas/note.py`
- [x] 1.2 Add `max_length=5000` to `TradeNoteUpdate.content` in `backend/app/schemas/note.py`
- [x] 1.3 Add constant `NOTE_MAX_LENGTH = 5000` to `backend/app/core/constants.py`

## 2. Backend Tests

- [x] 2.1 Write API test for `POST /trades/{id}/notes` with content of exactly 5000 chars → 201
- [x] 2.2 Write API test for `POST /trades/{id}/notes` with content of 5001 chars → 422
- [x] 2.3 Write API test for `PATCH /trades/{id}/notes/{note_id}` with content of 5001 chars → 422

## 3. Frontend Dependencies

- [x] 3.1 Add `react-markdown` and `remark-gfm` to `frontend/package.json` via `npm install react-markdown remark-gfm`

## 4. Markdown Rendering Components

- [x] 4.1 Create `frontend/components/notes/MarkdownRenderer.tsx` — wraps `react-markdown` with `remark-gfm`, applies Tailwind `prose` styles for rendered output
- [x] 4.2 Update `NoteList` component in `frontend/components/notes/NoteList.tsx` to render each note's `content` field via `MarkdownRenderer` instead of a plain `<p>` or `<pre>`
- [x] 4.3 Add relative timestamp display to each note in `NoteList` using `date-fns formatDistanceToNow` (e.g., "3 hours ago")

## 5. Note Form with Markdown Support

- [x] 5.1 Update `NoteForm` component in `frontend/components/notes/NoteForm.tsx`:
  - Add character counter (`{length}/5000`) below the textarea
  - Apply `text-amber-500` styling when content length ≥ 4500
  - Apply `text-red-500` and disable the save button when content length > 5000
  - Add "Edit / Preview" tab toggle — "Preview" tab renders content via `MarkdownRenderer`

## 6. Inline Quick-Note Component

- [x] 6.1 Create `frontend/components/notes/QuickNoteInput.tsx` — collapsible inline form: textarea + "Save" / "Cancel" buttons; "Save" disabled when textarea is empty; on save, calls `useNotes` mutation for `POST /trades/{id}/notes`
- [x] 6.2 Update `TradeRow` component in `frontend/components/trades/TradeRow.tsx`:
  - Add a note icon button (use an icon indicating "has notes" vs. "no notes")
  - Clicking expands `QuickNoteInput` below the row
  - Pass `hasNotes={trade.note_count > 0}` or equivalent to the icon for the filled/outline state

## 7. Trade Table Integration

- [x] 7.1 Verify that the `Trade` response schema includes a `note_count` field (or `has_notes: bool`); add it to the backend `TradeResponse` schema if missing
- [x] 7.2 If `note_count` is missing from backend, add it to `TradeResponse` in `backend/app/schemas/trade.py` and update the repository query to include a notes count subquery
- [x] 7.3 If backend change was needed: run `openapi-sync` skill to regenerate the frontend API client

## 8. Tests

- [ ] 8.1 Write React Testing Library tests for `NoteForm` — character counter updates, preview toggle, save disabled when over limit
- [ ] 8.2 Write React Testing Library tests for `QuickNoteInput` — save disabled when empty, note creation call on save
- [ ] 8.3 Write React Testing Library tests for `MarkdownRenderer` — renders bold/italic/code correctly

## 9. Lint, Types, and Commit

- [ ] 9.1 Run `lint-check` skill — fix all ruff and mypy errors
- [ ] 9.2 Run `unit-test` skill — ensure all tests pass
- [ ] 9.3 Create git commit using `commit-helper` skill
