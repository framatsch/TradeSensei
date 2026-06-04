## ADDED Requirements

### Requirement: Filter Check-ins by Taxonomy Tags

The system SHALL allow users to filter the check-in list by one or more assigned Taxonomy Tags.

#### Scenario: User selects taxonomy tags in the filter
- **WHEN** the user selects one or more tags in the "Tags" filter in the CheckinFilterBar
- **THEN** the system returns only check-ins that have at least one of the selected tags assigned (OR logic across selected tags)

---

### Requirement: Filter Check-ins by Annotation Values

The system SHALL allow users to filter the check-in list by annotation values, including specifying the operator and AND/OR chaining between multiple annotation filters.

#### Scenario: User adds a single annotation filter
- **WHEN** the user selects an annotation definition, an operator, and a value in the annotation filter section
- **THEN** the system returns only check-ins where that annotation matches the given condition

#### Scenario: User adds multiple annotation filters with AND logic
- **WHEN** the user adds two annotation filters both with logic=AND
- **THEN** the system returns only check-ins satisfying both conditions simultaneously

#### Scenario: User adds multiple annotation filters with OR logic
- **WHEN** the user sets the second annotation filter to logic=OR
- **THEN** the system returns check-ins satisfying either the first or second condition

#### Scenario: Operator options are type-appropriate
- **WHEN** the user selects an annotation definition of type bool
- **THEN** only the `eq` operator is offered
- **WHEN** the user selects type int or float
- **THEN** operators `eq`, `neq`, `gt`, `gte`, `lt`, `lte` are offered
- **WHEN** the user selects type string_enum
- **THEN** operators `eq` and `neq` are offered

---

### Requirement: Annotation Filters Persist in Saved Views

The system SHALL include annotation_filters and taxonomy_ids when saving or loading a saved check-in filter view.

#### Scenario: Save a view with annotation filters
- **WHEN** the user configures annotation filters and clicks "Save View"
- **THEN** the annotation_filters array is persisted in the saved view's filter_config
