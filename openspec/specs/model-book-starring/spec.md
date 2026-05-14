# model-book-starring Specification

## Purpose
TBD - created by archiving change model-book-cross-entity. Update Purpose after archive.
## Requirements
### Requirement: Trades can be starred into the Model Book
The system SHALL allow any trade to be marked as a Model Book entry via a boolean flag `is_modelbook`. A PATCH endpoint SHALL accept `{"is_modelbook": true/false}` and persist the change. The flag SHALL default to `false` for all trades.

#### Scenario: User stars a trade
- **WHEN** the user clicks the star toggle on a trade with `is_modelbook: false`
- **THEN** the system sends `PATCH /trades/{id}/modelbook` with `{"is_modelbook": true}`
- **AND** the response returns the updated trade with `is_modelbook: true`
- **AND** the star toggle updates immediately in the UI (optimistic update)

#### Scenario: User unstars a trade
- **WHEN** the user clicks the star toggle on a trade with `is_modelbook: true`
- **THEN** the system sends `PATCH /trades/{id}/modelbook` with `{"is_modelbook": false}`
- **AND** the trade is removed from the Model Book gallery on next load

#### Scenario: Starring is idempotent
- **WHEN** the user sends `PATCH /trades/{id}/modelbook` with `{"is_modelbook": true}` on an already-starred trade
- **THEN** the system returns 200 with `is_modelbook: true` (no error)

### Requirement: Check-ins can be starred into the Model Book
The system SHALL allow any daily check-in to be marked as a Model Book entry via a boolean flag `is_modelbook`. A PATCH endpoint SHALL accept `{"is_modelbook": true/false}` and persist the change. The flag SHALL default to `false` for all check-ins.

#### Scenario: User stars a check-in
- **WHEN** the user clicks the star toggle on a check-in detail view
- **THEN** the system sends `PATCH /checkins/{date}/modelbook` with `{"is_modelbook": true}`
- **AND** the response returns the updated check-in with `is_modelbook: true`

#### Scenario: User unstars a check-in
- **WHEN** the user clicks the star toggle on a check-in with `is_modelbook: true`
- **THEN** the check-in is removed from the Model Book gallery on next load

### Requirement: Star toggle is visible in Trade Detail and Check-in Detail toolbars
The Trade Detail page toolbar and the Check-in form toolbar SHALL each display a star icon button. The button SHALL reflect the current `is_modelbook` state (filled star = starred, outline star = not starred). Clicking it SHALL toggle the state.

#### Scenario: Trade Detail shows correct star state
- **WHEN** the user opens a trade with `is_modelbook: true`
- **THEN** the star button in the toolbar appears filled/highlighted

#### Scenario: Check-in form shows correct star state
- **WHEN** the user opens a check-in with `is_modelbook: false`
- **THEN** the star button in the form toolbar appears as an outline star

