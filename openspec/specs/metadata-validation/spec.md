# metadata-validation Specification

## Purpose
Define validation rules for taxonomy and annotation definitions, including color format, type-to-column mapping, and scope enforcement.

## Requirements

### Requirement: Hex color validation for taxonomies
The system SHALL validate that `color_hex` on taxonomy create/update requests matches the pattern `^#[0-9A-Fa-f]{6}$`.

#### Scenario: Valid hex accepted
- **WHEN** a request includes `color_hex: "#A3F4B1"`
- **THEN** the system accepts the value

#### Scenario: Short hex rejected
- **WHEN** a request includes `color_hex: "#FFF"`
- **THEN** the system returns 422

#### Scenario: Missing hash rejected
- **WHEN** a request includes `color_hex: "A3F4B1"`
- **THEN** the system returns 422

### Requirement: Annotation type-to-column mapping
The system SHALL dynamically map the incoming annotation `value` to the correct typed column based on the annotation definition's `type` field.

#### Scenario: int value maps to value_int
- **WHEN** an annotation of type `int` is assigned with `value: 3`
- **THEN** `value_int = 3`, and `value_float`, `value_bool`, `value_string` are NULL

#### Scenario: float value maps to value_float
- **WHEN** an annotation of type `float` is assigned with `value: 1.5`
- **THEN** `value_float = 1.5` is stored

#### Scenario: bool value maps to value_bool
- **WHEN** an annotation of type `bool` is assigned with `value: false`
- **THEN** `value_bool = false` is stored

#### Scenario: string_enum value maps to value_string
- **WHEN** an annotation of type `string_enum` is assigned with a valid enum value
- **THEN** `value_string` is populated

#### Scenario: CHECK constraint triggered on multi-column population
- **WHEN** a code path (bypassing service) attempts to set two value columns simultaneously
- **THEN** the database raises a constraint violation

### Requirement: Scope enforcement at assignment time
The system SHALL reject any assignment of a definition to an entity type not covered by the definition's scope.

#### Scenario: trades-only definition rejected for check-in
- **WHEN** an annotation or taxonomy with `scope = trades` is assigned to a check-in
- **THEN** the system returns 422

#### Scenario: checkins-only definition rejected for trade
- **WHEN** an annotation or taxonomy with `scope = checkins` is assigned to a trade
- **THEN** the system returns 422

#### Scenario: both scope accepted for either entity
- **WHEN** a definition with `scope = both` is assigned to either a trade or a check-in
- **THEN** the assignment is accepted

### Requirement: string_enum option validation
The system SHALL validate that the submitted value for a `string_enum` annotation exists in `scale_labels.options`.

#### Scenario: Valid option accepted
- **WHEN** `scale_labels.options = ["Low", "Medium", "High"]` and `value = "Medium"`
- **THEN** the assignment is created successfully

#### Scenario: Invalid option rejected
- **WHEN** `value = "Critical"` is not in `scale_labels.options`
- **THEN** the system returns 422

### Requirement: Numeric range validation
The system SHALL validate that int and float annotation values fall within `scale_labels.min` and `scale_labels.max` when those fields are defined.

#### Scenario: In-range value accepted
- **WHEN** `scale_labels.min = 1`, `scale_labels.max = 10`, and `value = 7`
- **THEN** the assignment is accepted

#### Scenario: Below-range value rejected
- **WHEN** `value = 0` and `scale_labels.min = 1`
- **THEN** the system returns 422

#### Scenario: Above-range value rejected
- **WHEN** `value = 11` and `scale_labels.max = 10`
- **THEN** the system returns 422

### Requirement: Archived definition assignment prevention
The system SHALL reject attempts to assign archived definitions to any entity.

#### Scenario: Archived taxonomy assignment rejected
- **WHEN** a taxonomy with `is_archived = true` is referenced in an assignment request
- **THEN** the system returns 422

#### Scenario: Archived annotation definition assignment rejected
- **WHEN** an annotation definition with `is_archived = true` is referenced in an assignment request
- **THEN** the system returns 422
