## Why

The Playbook detail/editor view (`PlaybookEditorClient`) currently uses a fixed `h-full` split-pane layout (35% left / 65% right) with nested scroll containers inside `<main className="flex-1 overflow-y-auto p-4 sm:p-6">`, causing competing scrollbars, collapsed or cramped Markdown editor heights, and wasted space in read mode. Meanwhile, the Market Check-in detail/editor view (`CheckinDateClient` / `CheckinForm`) centers everything in a narrow single-column `max-w-3xl` container that wastes horizontal screen space on maximized windows, stacks 6 sections vertically so users cannot see their screenshots/annotations while reading or writing notes, has inconsistent save behavior compared to Playbooks, and drops buffered tags/annotations on initial creation. Unifying both detail views around a shared full-width Document-First layout (Left: Markdown Main Pane, Right: Context & Media Side Pane on desktop; segmented `Document` | `Details & Media` tabs on mobile) creates a consistent, ergonomic reading and editing experience across the platform.

## What Changes

- **Unified Full-Width Desktop Layout (`lg+`) for Playbook Details & Check-in Details**:
  - Remove nested `overflow-hidden` / `h-full` scroll traps in `PlaybookEditorClient` and remove the narrow `max-w-3xl` constraint in `CheckinDateClient` so both views use the full available width with natural page scrolling inside `<main>`.
  - **Shared Header Card**:
    - Row 1: `Back` button, inline-editable Playbook name (or formatted Check-in Date with `< Previous Entry` / `Next Entry >` buttons that jump to the previous/next existing check-in entry), and consistent action buttons: `Edit` + `Delete` in read mode; `Cancel`, `Save` (persists and stays in edit mode, also bound to `Cmd/Ctrl + S`), and `Save & Close` (persists, exits edit mode, and strips `?edit=true` / `?draft=true` from URL) in edit mode.
    - Row 2 (Compact Header Meta Bar): Playbook `Status` toggle badge + `Target Win Rate`; Check-in `Target Market Indexes` pills (with clickable TradingView chart links in read mode).
  - **Left Main Pane (`flex-1` / ~65% width)**:
    - Dedicated to the Markdown document (`Strategy Documentation` for Playbooks, `Market Notes` for Check-ins) rendered in a `solid-card`.
    - Read mode expands naturally to full document height without internal scrollbars.
    - Edit mode provides an auto-growing Markdown `<textarea>` with `Write`, `Preview`, and desktop `Split` (side-by-side Write + Preview) tabs using GFM (`remark-gfm`) and HTML sanitization (`rehype-sanitize`).
  - **Right Side Pane (`w-full lg:w-[360px] xl:w-[420px] shrink-0`)**:
    - Identical vertical section order across both Playbooks and Check-ins:
      1. **Tags & Annotations Card**: Assigned taxonomy chips + add/toggle controls (plus typed `AnnotationEditor` fields for Check-ins).
      2. **Images / Screenshots Card**: Visual 16:9 thumbnail grid (`aspect-video`) with lightbox preview on click, delete controls, copy-markdown-ref action (for Playbooks), and drag-and-drop / click / clipboard-paste (`Cmd/Ctrl + V`) upload zone in edit mode.
      3. **Links Card**: External strategy links (Playbooks) or News & Catalyst links (Check-ins) with add/remove controls in edit mode.
- **Unified Mobile & Tablet View (`< lg`)**:
  - Render a sticky/compact 2-tab segmented switcher (`[ Document | Details & Media (count) ]`) directly below the Header Card on viewports below `lg` (`lg:hidden`).
  - `Document` tab (default) displays the Main Pane (Markdown reader/editor) immediately without scrolling past metadata.
  - `Details & Media` tab displays the Side Pane (Tags/Annotations, 16:9 Images/Screenshots, Links) while preserving all component state via CSS visibility classes (`hidden lg:flex`).
- **Bug Fix — Buffered Check-in Tags & Annotations on Create**:
  - Persist buffered tags and annotations immediately after `POST /api/v1/checkins` succeeds when saving a new check-in via `Save` or `Save & Close`.

## Capabilities

### New Capabilities
- `playbook-editor-ui`: Unified full-width document-first Playbook detail/editor layout (Header Card, Left Markdown Main Pane with Write/Preview/Split, Right Side Pane for Tags, 16:9 Images & Links, Mobile `Document` | `Details & Media` switcher, and `Save` + `Save & Close` workflow).

### Modified Capabilities
- `checkin-hub-ui`: Upgrade Daily Check-in detail/editor view (`/dashboard/checkins/[date]`) to the unified full-width document-first layout matching Playbooks (Header Card with `< Prev` / `Next >` date navigation and `Save` + `Save & Close`, Left Markdown Main Pane with Write/Preview/Split, Right Side Pane for Tags/Annotations, 16:9 Screenshots & News Links, and Mobile `Document` | `Details & Media` switcher).
- `checkin-form-tags-annotations`: Persist buffered tags and annotations upon new check-in creation when clicking `Save` or `Save & Close`.

## Impact

- **Frontend Components**:
  - `frontend/components/playbooks/PlaybookEditorClient.tsx`
  - `frontend/app/dashboard/checkins/[date]/CheckinDateClient.tsx`
  - `frontend/components/checkin/CheckinForm.tsx`
- **Tests**:
  - `frontend/__tests__/components/playbooks/PlaybookEditorClient.test.tsx`
  - `frontend/__tests__/components/checkin/`
  - `frontend/tests/specs/playbook-strategy-hub.spec.ts`
  - `frontend/tests/specs/checkin-metadata.spec.ts`
- **Backend / API**: No backend schema or endpoint changes required.
