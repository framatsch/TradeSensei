## ADDED Requirements

### Requirement: User can edit a broker account display name via a modal dialog
The hub SHALL provide a broker account edit modal. The account's broker type SHALL be displayed as an immutable badge. The display name SHALL be editable. API credentials SHALL be masked with password-type inputs.

#### Scenario: Edit modal opens with pre-filled data
- **WHEN** the user clicks the Edit button on an account row in the hub
- **THEN** the modal opens with the display name pre-filled and the broker type shown as a read-only badge

#### Scenario: Broker type is immutable
- **WHEN** the edit modal is open
- **THEN** the broker type is rendered as a static badge (not a select/dropdown) and cannot be changed

#### Scenario: Credential fields are masked as password inputs
- **WHEN** the edit modal is open for an account with credentials stored
- **THEN** each credential field is rendered as `type="password"` with an empty value (not the real key)

#### Scenario: Empty credential fields preserve existing keys
- **WHEN** the user submits the edit form without entering values in credential fields
- **THEN** the system submits the payload without credential keys, and the backend retains the existing stored credentials; a hint text reads "Leave blank to keep existing credentials"

#### Scenario: Saving a name change succeeds
- **WHEN** the user changes the display name and clicks "Save Changes"
- **THEN** the system calls `PATCH /api/v1/portfolios/{portfolio_id}/accounts/{id}` with the updated name and the modal closes

### Requirement: Test Connection in edit modal provides non-blocking inline feedback
The edit modal SHALL include the same "Test Connection" button as the create modal. Failure SHALL not block Save.

#### Scenario: Test connection in edit context
- **WHEN** the user clicks "Test Connection" in the edit modal
- **THEN** the endpoint is called with the current account id context; result is shown inline without disabling Save

### Requirement: User can deactivate a broker account to stop future syncing
The edit modal SHALL include a Status section with a "Deactivate Account" button. Deactivation preserves all historical trade data but stops future sync activity. There SHALL be no hard-delete option for accounts.

#### Scenario: Deactivate Account button shown
- **WHEN** the edit modal is open and the account is currently active (`is_active: true`)
- **THEN** a "Deactivate Account" button is shown in the Status section with the notice "Stops data sync, but retains all historical trades"

#### Scenario: Deactivation confirmed
- **WHEN** the user clicks "Deactivate Account" and confirms the prompt
- **THEN** the system calls `PATCH /api/v1/portfolios/{portfolio_id}/accounts/{id}` with `{ is_active: false }` and the account shows an "Inactive" status badge in the hub

#### Scenario: Reactivate shown for inactive accounts
- **WHEN** the edit modal is open and the account is currently inactive (`is_active: false`)
- **THEN** the button reads "Reactivate Account" instead of "Deactivate Account"

#### Scenario: No delete option available
- **WHEN** the edit modal is open
- **THEN** there is no "Delete Account" button or destructive delete action of any kind
