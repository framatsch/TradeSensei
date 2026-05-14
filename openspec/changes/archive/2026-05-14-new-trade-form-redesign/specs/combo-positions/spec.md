## MODIFIED Requirements

### Requirement: User can create a COMBO position trade
The system SHALL allow an authenticated user to create a trade with `is_combo: true`. For a COMBO trade the top-level `asset_class` SHALL be null and `entry_price`, `exit_price`, `quantity` SHALL be null. The trade's combined `pnl`, `commission`, `opened_at`, and `closed_at` SHALL be computed from its execution legs.

In the New Trade form UI, checking "COMBO position" SHALL immediately force Advanced Mode (Manual Legs) to `true` and SHALL disable the Advanced Mode toggle so it cannot be turned off independently. This constraint is enforced client-side only; the backend `is_combo` immutability requirement is unchanged.

#### Scenario: Successful COMBO trade creation
- **WHEN** a user sends `POST /api/v1/trades` with `{"symbol": "AAPL", "is_combo": true, "direction": "LONG"}`
- **THEN** the API returns 201 with `is_combo: true`, `asset_class: null`, `entry_price: null`, `exit_price: null`, `quantity: null`

#### Scenario: Non-COMBO trade is unaffected
- **WHEN** a user sends `POST /api/v1/trades` without `is_combo` (or with `is_combo: false`)
- **THEN** `is_combo` is `false` in the response and all existing aggregation behavior applies

#### Scenario: COMBO checkbox locks Advanced Mode toggle in the form
- **WHEN** the user checks "COMBO position" in the New Trade form
- **THEN** the Advanced Mode toggle is set to `true`
- **THEN** the Advanced Mode toggle is rendered as disabled (cannot be unchecked)

#### Scenario: Unchecking COMBO unlocks Advanced Mode toggle
- **WHEN** the user unchecks "COMBO position"
- **THEN** the Advanced Mode toggle is re-enabled
- **THEN** Advanced Mode value is NOT automatically reset (user controls it independently)

#### Scenario: Asset Class field hidden for COMBO trades
- **WHEN** the "COMBO position" checkbox is checked
- **THEN** the Asset Class dropdown is hidden from the form

#### Scenario: Advanced Mode without COMBO is still possible
- **WHEN** the user does NOT check "COMBO position" but enables Advanced Mode
- **THEN** the Advanced Mode toggle is active and not disabled
- **THEN** Asset Class remains visible
