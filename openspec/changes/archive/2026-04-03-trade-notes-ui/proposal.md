## Why

Trade notes (psychological annotations, setup rationale, post-trade reflections) are a core part of the journal's behavioral analysis feature. The current note UI is functional but minimal: notes are plain text, there is no inline editing in the trade list, and the note panel is only accessible from the trade detail page. Traders write richer notes when the interface supports formatting — and inline note-taking in the trade list reduces friction for quick post-trade annotations.

## What Changes

- Trade notes support **Markdown** formatting (stored as Markdown, rendered as HTML in the frontend)
- A **quick-note** input field is added to the trade row in the `TradeTable` for rapid inline annotation without navigating to the detail page
- The note panel on the trade detail page gets a **split-view editor** (raw Markdown on the left, rendered preview on the right)
- Notes display a **character count** and enforce a 5000-character limit (currently unconstrained)
- Notes show **created/edited timestamps** in a human-readable relative format ("2 hours ago")

## Capabilities

### New Capabilities

- `note-markdown-rendering`: Markdown support in trade notes — stored as Markdown, rendered to HTML in the frontend
- `note-inline-quick-add`: Inline note input directly in the trade table row for rapid annotation
- `note-character-limit`: Server-side 5000-character limit enforced on note create and update

### Modified Capabilities

<!-- none — backend API shape is unchanged; all changes are additive -->

## Impact

- **Backend**: Add `max_length=5000` validation to `TradeNoteCreate` and `TradeNoteUpdate` Pydantic schemas; no DB schema changes (content already a text column)
- **Frontend**: Add Markdown renderer (`react-markdown` or `marked`); update `NoteList` and `NoteForm` components; add `QuickNoteInput` component in `TradeRow`; update `TradeTable` to support note expansion
- **Dependencies**: `react-markdown` (frontend) + `remark-gfm` for GitHub Flavored Markdown support
- **Breaking**: None — additive + validation tightening (existing notes already within 5000 chars in practice)
