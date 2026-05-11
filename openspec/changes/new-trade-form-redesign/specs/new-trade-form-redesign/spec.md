## ADDED Requirements

### Requirement: Currency displayed as read-only account label
The New Trade form SHALL display the linked account's currency as a read-only label in the form header area. The currency input field SHALL be removed from the form. When no account is selected, no currency label is shown.

#### Scenario: Account with currency selected
- **WHEN** the user selects an account that has an associated currency (e.g., "Live Portfolio — USD")
- **THEN** the currency is shown as a non-editable text label adjacent to the account name
- **THEN** no currency input field is visible

#### Scenario: No account selected
- **WHEN** no account is selected in the account dropdown
- **THEN** no currency label is shown

---

### Requirement: Full-width form layout
The New Trade form SHALL use a full-width container layout to accommodate the execution legs table without horizontal compression. The form SHALL span the full available content width.

#### Scenario: Form renders at full width
- **WHEN** the New Trade page is loaded
- **THEN** the form container does not have a max-width constraint that forces it below the page content width

---

### Requirement: Drag-and-drop screenshot uploader in New Trade form
The New Trade form SHALL replace the `<input type="file">` with a drag-and-drop upload zone for screenshots. The zone SHALL support click-to-browse, drag-and-drop, and clipboard paste. Accepted types: PNG, JPG, GIF, WebP. Maximum file size: 20 MB per file.

#### Scenario: User drags an image onto the drop zone
- **WHEN** the user drags a valid image file onto the drop zone
- **THEN** the drop zone displays an active/highlighted state
- **THEN** on drop the file is uploaded and a thumbnail preview is added

#### Scenario: User clicks the drop zone to browse
- **WHEN** the user clicks the drop zone
- **THEN** a file picker dialog opens
- **THEN** selecting a valid image file triggers the upload

#### Scenario: Invalid file type dropped
- **WHEN** the user drops a non-image file onto the drop zone
- **THEN** no upload is triggered and an error message is displayed

#### Scenario: Thumbnail removal
- **WHEN** the user clicks "Remove" on a thumbnail
- **THEN** the image URL is removed from the form state and the thumbnail disappears

---

### Requirement: 2x2 Metadata Matrix panel in New Trade form
The New Trade form SHALL include a "Qualitative Data" section with two sub-panels:
1. **Trade Taxonomies** — multi-select panel showing all non-archived taxonomies scoped to `trades` or `both`.
2. **Trade Annotations** — one input per non-archived annotation definition scoped to `trades` or `both`, rendered according to its `input_type` (slider for int/float, toggle for bool, select for string_enum).

Selected taxonomy IDs and annotation values SHALL be held in local component state and assigned via separate API calls after the trade is created.

#### Scenario: Taxonomy panel loads scoped taxonomies
- **WHEN** the New Trade form is opened
- **THEN** the Trade Taxonomies panel shows only taxonomies with scope `trades` or `both`
- **THEN** checkins-only taxonomies are not visible

#### Scenario: User selects a taxonomy
- **WHEN** the user clicks a taxonomy chip in the panel
- **THEN** the chip appears selected (highlighted)
- **THEN** the taxonomy ID is stored in local form state

#### Scenario: Annotation panel renders correct input type
- **WHEN** an annotation definition of type `bool` is present
- **THEN** a toggle control is rendered for it
- **WHEN** an annotation definition of type `int` or `float` is present
- **THEN** a slider (or numeric input) is rendered for it
- **WHEN** an annotation definition of type `string_enum` is present
- **THEN** a select/dropdown is rendered for it

#### Scenario: No taxonomies defined
- **WHEN** there are no taxonomies scoped to `trades` or `both`
- **THEN** the Trade Taxonomies panel shows an empty state message

#### Scenario: No annotation definitions defined
- **WHEN** there are no annotation definitions scoped to `trades` or `both`
- **THEN** the Trade Annotations panel shows an empty state message

---

### Requirement: Taxonomy and annotation assignment after trade creation
After a trade is successfully created, the system SHALL assign all selected taxonomies and annotation values in parallel before navigating away. If any assignment fails, a non-blocking error message SHALL be displayed and the user SHALL be navigated to the new trade's detail page regardless.

#### Scenario: Successful creation with taxonomies
- **WHEN** the user creates a trade with 2 taxonomies selected
- **THEN** after trade creation succeeds, 2 POST calls to `/api/v1/trades/{id}/taxonomies` are made
- **THEN** the user is navigated to the trade detail page

#### Scenario: Taxonomy assignment fails after trade creation
- **WHEN** a taxonomy assignment API call returns an error after trade creation succeeds
- **THEN** a non-blocking warning is shown (e.g. toast or inline notice)
- **THEN** the user is still navigated to the trade detail page

#### Scenario: Successful creation with annotation values
- **WHEN** the user creates a trade with annotation values filled in
- **THEN** after trade creation succeeds, POST/PUT calls to `/api/v1/trades/{id}/annotations/{definition_id}` are made for each filled annotation
- **THEN** the user is navigated to the trade detail page
