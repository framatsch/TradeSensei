## ADDED Requirements

### Requirement: Inline Editing of SL/TP in Performance Card
The Performance Card in the right sidebar SHALL allow inline editing of Stop Loss and Take Profit values.

#### Scenario: Click-to-edit SL/TP
- **WHEN** a user clicks on the Stop Loss or Take Profit value in the Performance Card
- **THEN** the value MUST transform into an editable number input field
- **AND** Save (✓) and Cancel (✕) action buttons MUST appear
- **AND** pressing Enter MUST save, pressing Escape MUST cancel

#### Scenario: Saving SL/TP inline
- **WHEN** a user modifies the Stop Loss value and clicks Save
- **THEN** the system MUST call `PATCH /api/v1/trades/{id}` with `{ "stop_loss": "148.00" }`
- **AND** the Performance Card MUST refresh with the updated value
- **AND** dependent metrics (Initial Risk, Planned RRR, Realized R) MUST recalculate immediately

#### Scenario: Clearing SL/TP
- **WHEN** a user clears the input field and saves
- **THEN** the system MUST send `{ "stop_loss": null }` to clear the value
- **AND** the display MUST show "—"

### Requirement: Inline Editing of Playbook in Playbook & Psychology Card
The Playbook & Psychology Card SHALL allow inline editing of the Playbook assignment.

#### Scenario: Click-to-edit Playbook
- **WHEN** a user clicks on the current playbook name (or "No playbook assigned" placeholder)
- **THEN** a dropdown selector MUST appear with all available playbooks
- **AND** selecting a playbook MUST immediately call `PATCH /api/v1/trades/{id}` with `{ "playbook_id": "uuid" }`
- **AND** selecting "None" MUST clear the playbook assignment

### Requirement: Inline Editing of Tags in Playbook & Psychology Card
The Playbook & Psychology Card SHALL allow inline editing of trade tags.

#### Scenario: Click-to-edit Tags
- **WHEN** a user clicks on the tags area (or "No tags" placeholder)
- **THEN** a multi-select tag picker MUST appear with all available tags
- **AND** adding or removing a tag MUST immediately call `PATCH /api/v1/trades/{id}` with the updated `tag_ids` array

#### Scenario: Tag badges display
- **WHEN** tags are not being edited
- **THEN** they MUST display as the existing `TagBadge` components
- **AND** clicking any badge area MUST enter edit mode

### Requirement: Correct Trade Modal for Rare Corrections
The system SHALL provide a "Correct Trade..." option for editing rarely-changed identity fields (Symbol, Asset Class) that opens a small correction modal.

#### Scenario: Accessing the correction modal
- **WHEN** a user clicks "Correct Trade..." in the header overflow menu (⋮)
- **THEN** a modal dialog MUST open with editable fields: Symbol, Asset Class
- **AND** Direction MUST be displayed as **read-only** (derived from execution directions)
- **AND** Currency MUST be displayed as **read-only** (inherited from account)

#### Scenario: Correction modal content
- **WHEN** the correction modal is open
- **THEN** it MUST show a warning: "These fields affect trade identity. Only change them to fix import errors."
- **AND** the modal MUST have Cancel and "Save Corrections" buttons

#### Scenario: Saving corrections
- **WHEN** a user modifies the symbol and clicks "Save Corrections"
- **THEN** the system MUST call `PATCH /api/v1/trades/{id}` with the updated fields
- **AND** the system MUST set `is_manually_edited: true` on the trade
- **AND** the modal MUST close and the trade header MUST refresh

### Requirement: Direction and Currency are Read-Only
Direction and Currency SHALL be derived values that cannot be manually edited on the Trade Detail page.

#### Scenario: Direction derived from executions
- **WHEN** the trade detail page renders
- **THEN** Direction MUST be displayed as a badge (LONG/SHORT) but MUST NOT be editable
- **AND** the direction is determined by the opening execution legs

#### Scenario: Currency inherited from account
- **WHEN** the trade detail page renders
- **THEN** Currency MUST NOT be editable
- **AND** it is inherited from the associated broker account

### Requirement: Notes and TradingView Link Remain Inline (Unchanged)
The existing inline editing for Notes (Journal & Notes section) and TradingView Link (Media & Charts Card) SHALL remain as-is.

#### Scenario: Notes inline editing unchanged
- **WHEN** a user interacts with the Journal & Notes section
- **THEN** the existing inline note editor (NoteList + "Add Note") MUST work as before

#### Scenario: TradingView link inline editing unchanged
- **WHEN** a user interacts with the TradingView link area in MediaChartsCard
- **THEN** the existing inline edit behavior (click to edit URL) MUST work as before

### Requirement: Remove Full-Page Edit Form
The existing `TradeEditForm` component that replaces the entire Trade Detail page SHALL be removed. All editing is now inline or via the correction modal.

#### Scenario: No page-replacing edit mode
- **WHEN** the Trade Detail page renders
- **THEN** there MUST NOT be an `{isEditing ? <TradeEditForm/> : <NormalView/>}` toggle
- **AND** the entire page MUST always show the normal view with inline editing capabilities

#### Scenario: Edit Trade button behavior change
- **WHEN** the user clicks "Edit Trade" (in header or overflow menu)
- **THEN** it MUST NOT replace the page with a form
- **AND** instead it MUST activate inline edit mode on the sidebar cards (Performance + Playbook cards enter their editable state simultaneously)

### Requirement: Auto-Create Execution on Manual Trade Creation
When a trade is created via the "New Trade" form, the backend SHALL automatically create a corresponding `LogicalExecution` with `status: manual`.

#### Scenario: New trade gets an execution
- **WHEN** a user creates a trade via `POST /api/v1/trades` with entry_price, quantity, and opened_at
- **THEN** the backend MUST create a `LogicalExecution` with the trade's entry values and `status: manual`
- **AND** the execution MUST be assigned to the newly created trade

## REMOVED Requirements

### Requirement: TradeEditForm Full Page Override
**Reason**: Replaced by inline editing in sidebar cards and a small correction modal for rare identity fixes. The full-page form was necessary when all fields were editable; with execution-driven computed values, the remaining editable fields are few enough for inline editing.
**Migration**: SL/TP → inline in Performance Card. Playbook/Tags → inline in Playbook Card. Notes/TradingView → already inline. Symbol/AssetClass → Correct Trade modal. Direction/Currency → read-only.
