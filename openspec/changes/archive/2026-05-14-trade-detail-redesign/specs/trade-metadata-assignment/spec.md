## MODIFIED Requirements

### Requirement: Assign taxonomy to trade
The system SHALL allow assigning an existing taxonomy to a trade, subject to scope and archive validation. **The Trade Detail UI SHALL provide a multi-select component that triggers this assignment when the user saves the Qualitative Analysis panel.**

#### Scenario: Successful assignment
- **WHEN** a POST request assigns a non-archived taxonomy with `scope = trades` or `scope = both` to a trade
- **THEN** the assignment is created and the system returns 201

#### Scenario: Scope mismatch rejected
- **WHEN** a POST request attempts to assign a taxonomy with `scope = checkins` to a trade
- **THEN** the system returns 422 with a scope violation message

#### Scenario: Archived taxonomy assignment rejected
- **WHEN** a POST request attempts to assign an archived taxonomy to a trade
- **THEN** the system returns 422

#### Scenario: Duplicate assignment rejected
- **WHEN** a POST request assigns a taxonomy that is already assigned to the same trade
- **THEN** the system returns 409 Conflict

#### Scenario: Assignment removed on trade delete
- **WHEN** a trade is deleted
- **THEN** all `trade_taxonomies` rows for that trade are also deleted (CASCADE)

#### Scenario: UI shows scope-filtered taxonomy options
- **WHEN** the Qualitative Analysis panel loads its taxonomy multi-select
- **THEN** only taxonomies with `scope = trades` or `scope = both` are offered as options

### Requirement: Assign annotation to trade
The system SHALL allow assigning an annotation definition to a trade with a typed value that is mapped to the correct typed column. **The Trade Detail UI SHALL render a dynamic input per annotation definition, with input type determined by `data_type`.**

#### Scenario: Successful int annotation
- **WHEN** a POST request assigns an annotation of type `int` with `value: 5` to a trade
- **THEN** `value_int = 5` is stored, all other value columns are NULL, and the system returns 201

#### Scenario: Successful float annotation
- **WHEN** a POST request assigns an annotation of type `float` with `value: 2.75` to a trade
- **THEN** `value_float = 2.75` is stored and the system returns 201

#### Scenario: Successful bool annotation
- **WHEN** a POST request assigns an annotation of type `bool` with `value: true` to a trade
- **THEN** `value_bool = true` is stored and the system returns 201

#### Scenario: Successful string_enum annotation
- **WHEN** a POST request assigns an annotation of type `string_enum` with a value that exists in `scale_labels.options`
- **THEN** `value_string` is stored and the system returns 201

#### Scenario: Wrong type value rejected
- **WHEN** a POST request submits a string for an `int`-typed annotation
- **THEN** the system returns 422

#### Scenario: Out-of-range value rejected
- **WHEN** a POST request submits a value outside `scale_labels.min`/`scale_labels.max` for an int/float annotation
- **THEN** the system returns 422

#### Scenario: Invalid enum value rejected
- **WHEN** a POST request submits a value not in `scale_labels.options` for a `string_enum` annotation
- **THEN** the system returns 422

#### Scenario: Scope mismatch rejected
- **WHEN** a POST request assigns an annotation with `scope = checkins` to a trade
- **THEN** the system returns 422

#### Scenario: Assignment removed on trade delete
- **WHEN** a trade is deleted
- **THEN** all `trade_annotations` rows for that trade are also deleted (CASCADE)

#### Scenario: UI renders int/float as number input with bounds
- **WHEN** the Qualitative Analysis panel renders an annotation with `data_type = int` or `float`
- **THEN** a number input is shown, and if `scale_labels.min`/`max` are set, the input enforces those bounds client-side
