## MODIFIED Requirements

### Requirement: Execute API Sync per Account
The system MUST support initiating trade synchronization targeting a specific `account_id` utilizing the account's specific decrypted properties.

#### Scenario: Syncing an IBKR Account imports open positions
- **WHEN** the user initiates an API sync for an account of type `IBKR`
- **THEN** the system SHALL look up the account's decrypted Flex Token and Query ID
- **THEN** the system SHALL execute the IBKR sync logic
- **THEN** any `<OpenPosition>` elements in the Flex report SHALL be imported as open-lot execution legs in addition to `<Trade>` elements

#### Scenario: Syncing an IBKR Account — open positions are not duplicated on re-sync
- **WHEN** the user initiates a second API sync for the same IBKR account
- **WHEN** the Flex report contains the same `<OpenPosition>` records as the previous sync
- **THEN** no duplicate `LogicalExecution` or `Trade` records SHALL be created

#### Scenario: Syncing without valid credentials
- **WHEN** the user initiates an API sync for an account missing required `AccountProperty` records
- **THEN** the system SHALL return an HTTP 400 Bad Request indicating missing configuration
