# playwright-e2e Specification

## Purpose
Define end-to-end test coverage for tag/annotation assignment and filtering flows in check-ins and trades.

## Requirements

### Requirement: E2E — Assign Tags and Annotations in Check-in Form
The system SHALL have automated end-to-end test coverage verifying that a user can assign, remove, set, and clear taxonomy tags and annotation values (string_enum and bool) on a check-in via the check-in form.

#### Scenario: User assigns a taxonomy tag to a check-in
- **GIVEN** the user navigates to a check-in date page
- **WHEN** the user clicks Edit and selects a tag from the Tags multi-select
- **THEN** the tag appears as assigned on the check-in in view mode

#### Scenario: User removes a taxonomy tag from a check-in
- **GIVEN** a check-in with an assigned tag
- **WHEN** the user clicks Edit and deselects the tag
- **THEN** the tag is no longer shown on the check-in in view mode

#### Scenario: User sets a string_enum annotation (Market Regime)
- **GIVEN** the user is on a check-in in edit mode
- **WHEN** the user selects "Bull" from the "Market Regime" annotation dropdown
- **THEN** the value is shown as "Bull" in view mode under Annotations

#### Scenario: User sets a bool annotation
- **GIVEN** a bool-type annotation definition exists for checkins
- **WHEN** the user toggles it on
- **THEN** it shows as checked/active in view mode

#### Scenario: User clears an annotation value
- **GIVEN** an annotation value is set
- **WHEN** the user clicks the clear button next to that annotation
- **THEN** the annotation row shows as unset in view mode

---

### Requirement: E2E — Filter Check-ins by Tag and Annotation
The system SHALL have automated end-to-end test coverage verifying that a user can filter check-ins by taxonomy tag and by annotation value, including combining multiple annotation filters with AND logic.

#### Scenario: User filters check-ins by taxonomy tag
- **GIVEN** some check-ins have tag "Bullish" assigned and some do not
- **WHEN** the user selects "Bullish" in the Tags filter of CheckinFilterBar
- **THEN** only check-ins with that tag appear in the list

#### Scenario: User filters check-ins by annotation value
- **GIVEN** some check-ins have "Market Regime" = "Bull" and others = "Bear"
- **WHEN** the user adds an annotation filter: Market Regime eq Bull
- **THEN** only Bear check-ins disappear from the list

#### Scenario: User combines annotation filter with AND logic
- **GIVEN** the user adds two annotation filters with logic=AND
- **THEN** only check-ins satisfying both conditions are shown

---

### Requirement: E2E — Filter Trades by Annotation Value
The system SHALL have automated end-to-end test coverage verifying that a user can filter trades by an annotation value using the TradeFilterBar.

#### Scenario: User adds an annotation filter row in TradeFilterBar
- **GIVEN** trades with annotation "Setup Quality" = "A+" and others = "B"
- **WHEN** the user adds annotation filter: Setup Quality eq A+ in the Trade filter
- **THEN** only A+ trades are shown in the trade list
