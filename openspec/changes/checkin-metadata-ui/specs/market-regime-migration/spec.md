## MODIFIED Requirements

### Requirement: Market Regime as Default Annotation

The system SHALL replace the `market_phase` string field in the Check-in UI with a default `string_enum` AnnotationDefinition named "Market Regime".

#### Scenario: New user sees Market Regime annotation pre-seeded
- **GIVEN** a new user registers
- **WHEN** the user opens the Check-in form
- **THEN** a "Market Regime" annotation with options ["Bull", "Bear", "Chop", "Sideways"] is available under the Annotations section

#### Scenario: Existing user — manual re-entry required
- **GIVEN** an existing user who previously used the Market Phase field
- **WHEN** they open the Check-in form after the update
- **THEN** the old Market Phase pill UI is gone; they can re-enter their regime via the new "Market Regime" annotation dropdown
- **NOTE** No automated migration of old `market_phase` string values occurs; a brief in-app note or docs entry informs existing users

#### Scenario: market_phase field preserved in DB
- **GIVEN** the updated system
- **THEN** the `market_phase` column on `daily_checkins` still exists in the DB and old values are intact
- **AND** the field is simply no longer written or read by the UI

#### Scenario: regime filter replaced
- **GIVEN** the updated CheckinFilterBar
- **THEN** there is no dedicated "Market Phase" select filter
- **AND** filtering by market condition is done via the Annotation filter with the "Market Regime" definition
