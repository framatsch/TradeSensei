## ADDED Requirements

### Requirement: Playbook editor displays split-pane layout
The system SHALL render the playbook editor in a full-width split-pane layout with no page heading, following the established UI pattern.

```
+---------------------------------------------------------------------------------------------------+
| LIBRARY > PLAYBOOKS > [ Breakout Pattern ] [✎]    [Target Winrate: 60%]                   [✕] |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  METADATA & RESOURCES (35%)                  STRATEGY DOCUMENTATION (65%)                        |
|                                                                                                   |
|  Tags                                        [ Write ] [ Preview ]                               |
|  +---------------------------+               +-------------------------------------------------+ |
|  | [ Trend Following  ✕ ]    |               | # Breakout Setup Rules                          | |
|  | [ Momentum  ✕ ]     [ + ] |               |                                                 | |
|  +---------------------------+               | ## Entry Criteria                               | |
|                                              | 1. Volume must be > 1.5x average                | |
|  Images                                      | 2. Price closes above resistance                | |
|  +---------------------------+               |                                                 | |
|  |                           |               | ![Setup](ref:pb_img_01)                         | |
|  |   Click or drag & drop    |               |                                                 | |
|  |   ⌘V to paste             |               | ## Risk Management                              | |
|  |   PNG, JPG, GIF, WebP     |               | - Hard stop at recent swing low.                | |
|  +---------------------------+               +-------------------------------------------------+ |
|                                              |                                                   |
|  [▣] setup_ex.png      [✕]                   |                                                   |
|  [▣] chart_study.png   [✕]                   |                                                   |
|                                              |                                                   |
|  External Links                              |                                                   |
|  Label: [Technical Study    ]                |                                                   |
|  URL:   [https://source.com ] [ + ]          |                                                   |
|  [↗] Technical Study  [✕]                   |                                                   |
|  [↗] Video Tutorial   [✕]                   |                                              [ Save ] |
+---------------------------------------------------------------------------------------------------+
```

#### Scenario: Layout renders on navigation to edit playbook
- **WHEN** a user navigates to the playbook edit page
- **THEN** the page displays a toolbar with the playbook name (editable inline), target winrate field, and a close/back control; below the toolbar a left pane (35% width) and a right pane (65% width) are rendered side by side

#### Scenario: Left pane contains metadata and resources sections
- **WHEN** the playbook editor is rendered
- **THEN** the left pane contains: a Tags section with taxonomy chips and add control, an Images section with upload zone and image list, and an External Links section with label+URL form and link list

#### Scenario: Right pane contains Markdown editor with preview toggle
- **WHEN** the playbook editor is rendered
- **THEN** the right pane contains a Markdown editor with Write and Preview tabs, and a Save button

### Requirement: Taxonomy multi-select in playbook editor
The system SHALL display assigned taxonomies and allow adding or removing them in the playbook editor.

#### Scenario: Displays current taxonomy assignments
- **WHEN** the editor loads for a playbook with assigned taxonomies
- **THEN** the Tags section shows each assigned taxonomy as a removable chip with its name and color

#### Scenario: User can add taxonomy via selector
- **WHEN** the user opens the taxonomy add control
- **THEN** available taxonomies with `scope = playbook` or `scope = both` are listed and can be selected

#### Scenario: Assigned taxonomy removed on chip dismiss
- **WHEN** the user clicks the remove control on a taxonomy chip
- **THEN** the taxonomy assignment is deleted via API and the chip is removed from the UI

### Requirement: Image upload zone in playbook editor
The system SHALL display an image upload zone matching the trade screenshot uploader pattern (drag-and-drop, click, paste).

#### Scenario: Image dropped or pasted triggers upload
- **WHEN** a user drops or pastes an image (PNG, JPG, GIF, WebP) onto the upload zone
- **THEN** the system requests a presigned URL, uploads the file directly to S3, registers the attachment via API, and displays the image in the list below the zone

#### Scenario: Non-image file shows error
- **WHEN** a user drops a file that is not an image
- **THEN** the upload zone displays an error and no upload is initiated

#### Scenario: Image list shows thumbnail and delete control
- **WHEN** images exist for the playbook
- **THEN** each image is listed with its filename, a thumbnail that opens a lightbox on click, and a delete button

#### Scenario: Deleting image removes from list
- **WHEN** the user clicks delete on an image
- **THEN** the image is deleted via API and removed from the list

### Requirement: External link list in playbook editor
The system SHALL display a label + URL form for adding links and list existing links with their labels.

#### Scenario: User adds a labeled link
- **WHEN** the user enters a label (e.g., "Technical Study") and a URL, then presses Enter or the add button
- **THEN** the link is created via API and appears in the list as a labeled anchor

#### Scenario: Link list renders with label and delete control
- **WHEN** links exist for the playbook
- **THEN** each link is displayed as its label (as a clickable anchor, opens in new tab) and a remove button

#### Scenario: Deleting link removes from list
- **WHEN** the user clicks remove on a link
- **THEN** the link is deleted via API and removed from the list

### Requirement: Markdown preview resolves image refs
The system SHALL resolve `ref:<attachment_id>` placeholders in Markdown preview to the corresponding image's `storage_url`.

#### Scenario: Image ref rendered in preview
- **WHEN** the user switches to Preview tab and `content_markdown` contains `![alt](ref:<uuid>)`
- **THEN** the preview renders an `<img>` tag pointing to the image's `storage_url`

#### Scenario: Deleted image ref shows placeholder
- **WHEN** `content_markdown` references an attachment ID that no longer exists
- **THEN** the preview renders a placeholder indicating the image was deleted, not a broken img tag
