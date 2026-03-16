## ADDED Requirements

### Requirement: Markdown rendering for trade notes
The system SHALL render trade note content as Markdown in the frontend. The API SHALL continue to return note content as raw Markdown strings (no server-side rendering).

The frontend note display components SHALL use `react-markdown` with `remark-gfm` to render note content. Supported Markdown features include: bold, italic, inline code, code blocks, ordered/unordered lists, tables, task lists, and strikethrough.

The `NoteForm` component SHALL provide a character counter showing `current/5000` characters, and a preview toggle button that switches between editing the raw Markdown and viewing the rendered output.

#### Scenario: Note content is rendered as Markdown
- **WHEN** a note with Markdown content (e.g., `**bold** and _italic_`) is displayed in the note list
- **THEN** the rendered output shows bold and italic text (not raw Markdown syntax)

#### Scenario: Preview toggle shows rendered Markdown in the form
- **WHEN** the user clicks the "Preview" button in `NoteForm`
- **THEN** the textarea is replaced with the rendered Markdown output of the current content

#### Scenario: Edit toggle returns to editing mode
- **WHEN** the user is in preview mode and clicks "Edit"
- **THEN** the textarea is shown again with the original Markdown content

#### Scenario: Character counter updates as user types
- **WHEN** the user types in the note textarea
- **THEN** the character counter displays the current character count in real time
