## ADDED Requirements

### Requirement: Playbook stores rich markdown content
The system SHALL persist a `content_markdown` TEXT column on the `playbooks` table to store strategy documentation in Markdown format. The field is optional (nullable). No length cap is enforced at the database level.

#### Scenario: Create playbook with content_markdown
- **WHEN** a POST request is sent with a valid `content_markdown` string
- **THEN** the system returns 201 with the created playbook including the stored `content_markdown` value

#### Scenario: Create playbook without content_markdown
- **WHEN** a POST request omits `content_markdown`
- **THEN** the system returns 201 with `content_markdown: null`

#### Scenario: Update content_markdown
- **WHEN** a PATCH/PUT request sets `content_markdown` to a non-empty string
- **THEN** the system returns 200 with the updated playbook and refreshed `updated_at`

#### Scenario: Clear content_markdown
- **WHEN** a PATCH/PUT request sets `content_markdown` to null
- **THEN** the system returns 200 and the field is stored as NULL

### Requirement: Playbook stores optional target win rate
The system SHALL persist a `target_winrate` NUMERIC(5,4) column on the `playbooks` table representing a benchmark win rate (0.0000–1.0000). The field is optional (nullable). Values outside [0, 1] SHALL be rejected with 422.

#### Scenario: Create playbook with target_winrate
- **WHEN** a POST request sends `target_winrate: 0.6`
- **THEN** the system returns 201 with `target_winrate: 0.6000`

#### Scenario: Reject target_winrate out of range
- **WHEN** a POST request sends `target_winrate: 1.5`
- **THEN** the system returns 422 Unprocessable Entity

#### Scenario: Create playbook without target_winrate
- **WHEN** a POST request omits `target_winrate`
- **THEN** the system returns 201 with `target_winrate: null`

### Requirement: Playbook editor shows markdown editor with preview toggle
The system's frontend SHALL provide a markdown editor for `content_markdown` in the Playbook create/edit form. A toggle button SHALL switch between "Edit" and "Preview" modes. Preview renders the markdown as HTML using a client-side renderer.

#### Scenario: Edit mode shows textarea
- **WHEN** the user opens a playbook form and the editor is in Edit mode
- **THEN** a textarea is visible containing the raw markdown source

#### Scenario: Preview mode renders markdown
- **WHEN** the user clicks the "Preview" button
- **THEN** the textarea is replaced by a rendered HTML view of the markdown content

#### Scenario: Target winrate field shown as percentage
- **WHEN** the playbook form is rendered
- **THEN** the `target_winrate` field is displayed as a numeric percentage input (0–100)
- **AND** the stored value is divided by 100 on load and multiplied by 100 on submit
