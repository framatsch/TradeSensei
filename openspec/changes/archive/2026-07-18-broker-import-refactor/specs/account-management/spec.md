## ADDED Requirements

### Requirement: Danger Zone Clear-Trades Action
The account Danger Zone SHALL offer a "Clear all trades" destructive action that removes all trades for the account without deleting the account. The action SHALL be visually distinct as destructive and SHALL require an explicit confirmation affordance consistent with the account-deletion confirmation.

#### Scenario: Danger Zone exposes clear-trades
- **WHEN** a user opens the Danger Zone for an account they own
- **THEN** a "Clear all trades" action SHALL be presented alongside "Delete account"
- **THEN** the action SHALL clearly indicate it is destructive and cannot be undone

#### Scenario: Confirmation gate before clearing
- **WHEN** the user triggers "Clear all trades"
- **THEN** the user SHALL be required to confirm (acknowledgement or type-to-confirm) before the trades are deleted

#### Scenario: Account survives clear-trades
- **WHEN** the clear-trades action completes successfully
- **THEN** the account SHALL still exist and remain selectable
- **THEN** only its trades, executions, and raw transactions SHALL have been removed
