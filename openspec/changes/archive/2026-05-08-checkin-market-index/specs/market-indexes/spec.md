## ADDED Requirements

### Requirement: User can manage market index definitions
The system MUST allow users to create, read, update, and delete market index definitions scoped to their account. A market index consists of a unique symbol, a display name, and a TradingView URL.

#### Scenario: User creates a new market index
- **WHEN** the user submits a valid market index payload (symbol, name, tv_url)
- **THEN** the system saves the index and returns it with a generated UUID

#### Scenario: User views their market indexes
- **WHEN** the user requests their market indexes
- **THEN** the system returns a list of all active market index definitions belonging to the user

#### Scenario: User updates an existing market index
- **WHEN** the user submits updated fields for an existing index they own
- **THEN** the system updates the record and returns the modified index

#### Scenario: User deletes a market index
- **WHEN** the user requests to delete an index they own
- **THEN** the system marks it as inactive or deletes it and returns a success response

### Requirement: System seeds default market indexes
The system MUST automatically seed a set of default market indexes (e.g., SPX, NDX, DAX) for a user if none exist.

#### Scenario: Seeding defaults for a new user
- **WHEN** a user logs in and has no market indexes defined
- **THEN** the system inserts the default US and EU index definitions for that user
