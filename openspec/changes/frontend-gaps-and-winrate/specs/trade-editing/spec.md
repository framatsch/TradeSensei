## ADDED Requirements

### Requirement: User can create a trade manually
The system SHALL provide a trade creation form accessible from the trade list page,
allowing the user to enter all trade fields: symbol, direction, asset class,
quantity, entry price, exit price, stop loss, take profit, opened_at, closed_at,
PnL, commission, currency, account, playbook, tags, and notes.

#### Scenario: Successful trade creation
- **WHEN** user fills in required fields (symbol, direction, asset class, quantity,
  entry price, opened_at) and submits
- **THEN** the trade is created and appears in the trade list
- **AND** the user is navigated back to the trade list or to the new trade's detail page

#### Scenario: Validation error on create
- **WHEN** user submits the form with a missing required field
- **THEN** the form displays a validation error on the offending field
- **AND** the trade is not created

---

### Requirement: User can edit an existing trade
The system SHALL provide an edit form pre-populated with the trade's current values,
accessible via an "Edit" button on the trade detail page.

#### Scenario: Edit form pre-populated
- **WHEN** user clicks "Edit" on a trade detail page
- **THEN** the edit form opens with all current field values filled in

#### Scenario: Successful trade edit
- **WHEN** user modifies one or more fields and submits
- **THEN** the trade detail page reflects the updated values

#### Scenario: Clear nullable field (stop_loss / take_profit)
- **WHEN** user explicitly clears the stop_loss or take_profit field and saves
- **THEN** the field is set to null on the trade (not ignored)

---

### Requirement: Trade detail page shows playbook name
The system SHALL display the name of the assigned playbook (not the raw UUID) on
the trade detail page.

#### Scenario: Playbook name displayed
- **WHEN** a trade has an assigned playbook
- **THEN** the trade detail page shows the playbook's name as a readable label

#### Scenario: No playbook assigned
- **WHEN** a trade has no playbook
- **THEN** the playbook row shows "—" or is hidden

---

### Requirement: Trade detail page shows currency and EUR PnL
The system SHALL display the `currency` and `pnl_eur` fields on the trade detail
page when they are present.

#### Scenario: Currency and EUR PnL shown
- **WHEN** a trade has `currency` and `pnl_eur` set
- **THEN** the detail page displays both values in the trade details card

#### Scenario: Fields absent when null
- **WHEN** `currency` or `pnl_eur` is null
- **THEN** the corresponding row is not rendered (or shows "—")
