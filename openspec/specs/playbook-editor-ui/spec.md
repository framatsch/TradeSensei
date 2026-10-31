# playbook-editor-ui Specification

## Purpose
Define the document-first layout and editing behavior of the playbook detail and editor view.

## Requirements

### Requirement: Playbook detail and editor uses unified full-width layout with right side pane and natural page scrolling
The system SHALL render the playbook detail and editor view (`/dashboard/library/playbooks/[id]`) using a full-width document-first layout that scrolls naturally with the parent `<main>` viewport without nested `overflow-hidden` scroll traps.
- At the top, a full-width Header Card SHALL display:
  - Row 1: `Back to playbooks` button, playbook name (inline-editable in edit mode), and action buttons (`Delete` and `Edit` in read mode; `Cancel`, `Save`, and `Save & Close` in edit mode).
  - Row 2: `Status` toggle badge (`Active` / `Inactive`) and `Target Win Rate` display/input.
- On desktop viewports (`lg` and above), the body below the Header Card SHALL render two columns side by side:
  - **Left Main Pane (`flex-1`)**: Strategy Documentation card (Markdown reader/editor).
  - **Right Side Pane (`w-[360px] xl:w-[420px]`)**: Three stacked cards/sections in fixed order: `Tags`, `Images`, and `External Links`.

#### Scenario: Natural page scrolling without nested scrollbars in read mode
- **WHEN** a user views a playbook with long Markdown content
- **THEN** the Strategy Documentation card expands to fit its full rendered Markdown content and scrolls with the main page without an internal nested scrollbar

#### Scenario: Clicking Save or pressing Cmd/Ctrl+S persists changes and stays in edit mode
- **WHEN** a user clicks `Save` or presses `Cmd/Ctrl + S` in edit mode
- **THEN** the playbook and any staged attachment changes are persisted and `isEditMode` remains `true`

#### Scenario: Clicking Save & Close persists changes, exits edit mode, and cleans URL query parameter
- **WHEN** a user clicks `Save & Close` in edit mode
- **THEN** the playbook and any staged attachment changes are persisted, `isEditMode` transitions to `false`, and the URL query parameters `?edit=true` and `?draft=true` are removed

### Requirement: Playbook mobile view provides a segmented switcher between Document and Details & Media
On viewports below `lg` (`< 1024px`), the system SHALL render a segmented 2-tab switcher (`Document` and `Details & Media` with a total item count badge) directly below the Header Card. Both panes SHALL remain mounted in the DOM so switching tabs preserves unsaved state.

#### Scenario: Mobile defaults to Document tab and switches to Details & Media
- **WHEN** a user opens `/dashboard/library/playbooks/[id]` on a mobile viewport (`< lg`)
- **THEN** the `Document` tab is active by default showing the Strategy Documentation pane, and clicking `Details & Media` reveals the Side Pane (`Tags`, `Images`, `External Links`)

### Requirement: Markdown editor supports auto-growing write, preview, and desktop split modes
The system SHALL provide a Markdown editor in the Left Main Pane when in edit mode, supporting `Write`, `Preview`, and desktop `Split` (side-by-side Write + Preview) tabs, with a minimum height of `480px` and automatic vertical growth to match content length.

#### Scenario: Write mode auto-grows with content
- **WHEN** the user types or pastes multi-page Markdown in `Write` mode
- **THEN** the textarea maintains at least `480px` height and expands vertically without trapping the user in a collapsed inner scroll container

#### Scenario: Split mode displays editor and live preview side by side
- **WHEN** the user selects the `Split` tab in edit mode on a desktop viewport
- **THEN** the Markdown textarea and the sanitized GFM preview are rendered side by side

#### Scenario: Markdown preview resolves image refs
- **WHEN** the user views the playbook or selects `Preview` / `Split` mode and the Markdown contains `![alt](ref:<uuid>)`
- **THEN** the preview resolves `ref:<uuid>` to the matching attachment's `storage_url` or renders `[attachment deleted]` if not found

### Requirement: Visual reference chart gallery in playbook side pane
The system SHALL render playbook image attachments in the Right Side Pane as visual 16:9 thumbnail cards (`aspect-video`) rather than compact 40×40px filename rows, allowing users to inspect strategy setup charts alongside their rules and open them in a full-screen lightbox.

#### Scenario: Attachments render as visual thumbnail cards
- **WHEN** a playbook has one or more image attachments
- **THEN** the Images section in the right side pane displays each image as a 16:9 visual card with filename caption, lightbox click action, and (in edit mode) a delete button and copy-markdown-ref action

#### Scenario: Image upload zone in edit mode
- **WHEN** the playbook is in edit mode
- **THEN** the Images section displays a drag-and-drop / click / clipboard-paste (`Cmd/Ctrl + V`) upload zone above the thumbnail grid

### Requirement: Taxonomy and external link management in playbook side pane
The system SHALL allow viewing and managing taxonomy tags and external reference links in the Right Side Pane.

#### Scenario: Taxonomy chips and selector
- **WHEN** the playbook is in edit mode
- **THEN** assigned tags show a remove button and an `+ Add tag…` selector is available for unassigned active `playbook` taxonomies

#### Scenario: External links list and creation form
- **WHEN** links exist or the user is in edit mode
- **THEN** the External Links section lists each link as an external anchor (`http://` or `https://` only) and, in edit mode, provides a Label + URL form to add or delete links
