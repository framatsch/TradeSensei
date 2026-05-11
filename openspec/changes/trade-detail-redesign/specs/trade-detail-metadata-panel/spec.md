## ADDED Requirements

### Requirement: Qualitative metadata panel renders trade taxonomies
The Trade Detail page SHALL display a "Qualitative Analysis & Metadata" full-width section below the chart+performance row. This section SHALL render the trade's currently assigned taxonomies as selected options in a multi-select component, loading available definitions from `GET /api/v1/taxonomies?scope=trades`.

#### Scenario: Assigned taxonomies shown as selected
- **WHEN** a trade has taxonomies assigned
- **THEN** the panel displays those taxonomy names as selected tags in the multi-select component

#### Scenario: No taxonomies shows empty state
- **WHEN** a trade has no assigned taxonomies
- **THEN** the multi-select displays a placeholder "Select tags…" with no selected items

#### Scenario: Available taxonomy options exclude archived
- **WHEN** the taxonomy list is fetched
- **THEN** only non-archived taxonomy definitions with scope `trades` or `both` are shown as options

### Requirement: Qualitative metadata panel renders trade annotations with dynamic inputs
The panel SHALL render a list of annotation inputs, one per annotation definition returned by `GET /api/v1/annotation-definitions?scope=trades`. Each input SHALL reflect the annotation's `data_type`:
- `int` or `float` → numeric input with `min`/`max` from `scale_labels` (if present)
- `bool` → toggle switch
- `string_enum` → dropdown with options from `scale_labels.options`

Pre-populated with the trade's current annotation values.

#### Scenario: Integer annotation renders number input
- **WHEN** an annotation definition has `data_type = int`
- **THEN** the panel renders a number input; if `scale_labels.min`/`max` are set, the input enforces those bounds

#### Scenario: Float annotation renders number input
- **WHEN** an annotation definition has `data_type = float`
- **THEN** the panel renders a number input with decimal support

#### Scenario: Bool annotation renders toggle
- **WHEN** an annotation definition has `data_type = bool`
- **THEN** the panel renders a toggle switch; checked state reflects the current `value_bool`

#### Scenario: String enum annotation renders dropdown
- **WHEN** an annotation definition has `data_type = string_enum` and `scale_labels.options` is non-empty
- **THEN** the panel renders a dropdown with the defined options

#### Scenario: String enum with empty options renders disabled input
- **WHEN** an annotation definition has `data_type = string_enum` and `scale_labels.options` is null or empty
- **THEN** the panel renders a disabled input with placeholder "No options defined"

#### Scenario: Existing annotation value pre-fills input
- **WHEN** the trade has a value stored for an annotation definition
- **THEN** the corresponding input is pre-filled with that value in view mode

### Requirement: Qualitative metadata panel edit mode
The panel SHALL have a header with an `[✎ Edit]` button. Clicking it enters edit mode for the entire panel. In edit mode, taxonomy multi-select, annotation inputs, and the journal textarea become interactive. A `[Save]` button commits all changes; a `[Cancel]` button discards drafts and returns to view mode.

#### Scenario: Clicking Edit enters edit mode
- **WHEN** the user clicks `[✎ Edit]` on the panel header
- **THEN** all inputs in the panel become interactive and the `[Save]` and `[Cancel]` buttons appear

#### Scenario: Save commits taxonomy changes
- **WHEN** the user adds or removes taxonomies and clicks `[Save]`
- **THEN** the appropriate `POST /api/v1/trades/{id}/taxonomies` or `DELETE /api/v1/trades/{id}/taxonomies/{taxonomy_id}` calls are made

#### Scenario: Save commits annotation changes
- **WHEN** the user changes an annotation value and clicks `[Save]`
- **THEN** the appropriate `POST` (new) or `PUT` (existing) call is made to `/api/v1/trades/{id}/annotations/{definition_id}`

#### Scenario: Save commits journal notes
- **WHEN** the user edits the journal textarea and clicks `[Save]`
- **THEN** `PATCH /api/v1/portfolios/{portfolio_id}/trades/{trade_id}` is called with the updated `notes` field

#### Scenario: Cancel discards unsaved changes
- **WHEN** the user modifies inputs and clicks `[Cancel]`
- **THEN** all inputs revert to the last saved values and edit mode is exited

### Requirement: Execution legs table is full-width at bottom of page
The `ExecutionLegsTable` SHALL be rendered in a standalone full-width container at the absolute bottom of the Trade Detail page, outside of the two-column grid, so that it does not cause horizontal scrolling within the grid.

#### Scenario: Execution legs table spans full width
- **WHEN** the Trade Detail page is rendered
- **THEN** the execution legs table is not inside the two-column grid and spans the full page width

### Requirement: Trade Images block is removed from Trade Detail page
The `TradeImageGallery` component SHALL NOT be rendered on the Trade Detail page. Screenshot management is available via the Screenshots tab in `MediaChartsCard`.

#### Scenario: Trade Detail page does not render TradeImageGallery
- **WHEN** the Trade Detail page is rendered
- **THEN** no `TradeImageGallery` component is present in the DOM

### Requirement: Stop Loss and Take Profit appear at top of Performance card
The Stop Loss and Take Profit editable fields SHALL be rendered at the top of the Performance card, above all computed metrics.

#### Scenario: SL/TP fields appear before computed metrics
- **WHEN** the Performance card is rendered
- **THEN** the Stop Loss and Take Profit fields are the first rows in the card, before Realized R and other computed metrics
