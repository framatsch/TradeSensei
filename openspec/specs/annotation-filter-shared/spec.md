## ADDED Requirements

### Requirement: Shared Annotation Filter Logic (Backend)

The system SHALL implement annotation filter query logic as a shared backend utility reusable across Check-ins, Trades, and Workspace.

#### Scenario: Annotation filter applied to trades
- **WHEN** the trade list API receives annotation_filters in the query
- **THEN** the shared utility generates the correct EXISTS subquery against `trade_annotations`

#### Scenario: Annotation filter applied to check-ins
- **WHEN** the check-in list API receives annotation_filters
- **THEN** the shared utility generates the correct EXISTS subquery against `checkin_annotations`

---

### Requirement: Filter Trades by Annotation Values (UI)

The system SHALL expose annotation filtering in the Trade Filter Bar using the shared AnnotationFilterRows component.

#### Scenario: User adds annotation filter rows in the Trade filter
- **WHEN** the user adds annotation filter rows in TradeFilterBar
- **THEN** the trade list is filtered using AND/OR chaining of the annotation conditions

---

### Requirement: Filter Workspace by Annotation Values (UI)

The system SHALL expose annotation filtering in the Workspace Filter Bar using the shared AnnotationFilterRows component.

#### Scenario: User adds annotation filter rows in the Workspace filter
- **WHEN** the user adds annotation filter rows in WorkspaceFilterBar
- **THEN** the workspace trade list is filtered using the annotation conditions

---

### Requirement: Shared AnnotationFilterRows UI Component

The system SHALL provide a single reusable `AnnotationFilterRows` frontend component used by all three filter bars (Check-ins, Trades, Workspace).

#### Scenario: Component renders typed operator and value inputs
- **GIVEN** an annotation definition has been selected in a filter row
- **THEN** the operator dropdown shows only operators valid for that definition's type
- **AND** the value input renders as a toggle (bool), dropdown (string_enum), or number field (int/float)
