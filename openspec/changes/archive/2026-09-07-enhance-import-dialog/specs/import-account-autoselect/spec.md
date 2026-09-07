## ADDED Requirements

### Requirement: Account Auto-Selection
The system SHALL automatically select an account in the unified import dialog (used for both Schwab and IBKR) if the user has exactly one account in their portfolio.

#### Scenario: User has exactly one account
- **WHEN** the user opens the import dialog
- **AND** the user's portfolio contains exactly one account
- **THEN** the account dropdown is automatically pre-filled with that account
- **AND** the user is not required to manually select an account

#### Scenario: User has multiple accounts
- **WHEN** the user opens the import dialog
- **AND** the user's portfolio contains more than one account
- **THEN** the account dropdown remains empty (or in its default state)
- **AND** the user must manually select an account
