## ADDED Requirements

### Requirement: Execute API Sync per Account
The system MUST support initiating trade synchronization targeting a specific `account_id` utilizing the account's specific decrypted properties.

#### Scenario: Syncing an IBKR Account
- **WHEN** the user initiates an API sync for an account of type `IBKR`
- **THEN** the system SHALL look up the account's decrypted Flex Token and Query ID
- **THEN** the system SHALL execute the IBKR sync logic

#### Scenario: Syncing a Schwab Account
- **WHEN** the user initiates an API sync for an account of type `SCHWAB`
- **THEN** the system SHALL look up the account's decrypted App Key and App Secret
- **THEN** the system SHALL execute the Schwab sync logic

#### Scenario: Syncing without valid credentials
- **WHEN** the user initiates an API sync for an account missing required `AccountProperty` records
- **THEN** the system SHALL return an HTTP 400 Bad Request indicating missing configuration