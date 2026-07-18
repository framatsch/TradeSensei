# checkin-form-tags-annotations Specification

## Purpose
Define expected behavior for assigning tags and annotation values to check-ins via the check-in form.

## Requirements

### Requirement: Assign Tags to a Check-in

The system SHALL allow users to assign one or more Tags (Taxonomy with scope="checkins") to a daily check-in from within the Check-in Form.

#### Scenario: User assigns a tag to an existing check-in
- **WHEN** the user opens an existing check-in in edit mode and selects a tag from the Tags field
- **THEN** the system immediately calls `POST /{checkin_id}/taxonomies` and the tag appears as assigned

#### Scenario: User removes a tag from an existing check-in
- **WHEN** the user deselects an assigned tag in the Tags field
- **THEN** the system calls `DELETE /{checkin_id}/taxonomies/{taxonomy_id}` and the tag is removed

#### Scenario: User assigns tags while creating a new check-in
- **WHEN** the user selects tags before saving a new check-in
- **THEN** the tags are buffered locally and assigned via `POST /{checkin_id}/taxonomies` after the initial create call

---

### Requirement: Set Annotation Values on a Check-in

The system SHALL allow users to set typed annotation values on a daily check-in for all AnnotationDefinitions with scope="checkins" or scope="both".

#### Scenario: User sets a bool annotation
- **WHEN** a bool-type annotation definition is available and the user toggles it
- **THEN** the system calls `POST /{checkin_id}/annotations/{annotation_definition_id}` with `value_bool`

#### Scenario: User sets a string_enum annotation
- **WHEN** a string_enum-type annotation definition is available and the user selects a value from the dropdown
- **THEN** the system calls POST/PUT with `value_string`

#### Scenario: User sets an int or float annotation
- **WHEN** an int- or float-type annotation definition is available and the user enters a number
- **THEN** the system calls POST/PUT with the appropriate `value_int` or `value_float`

#### Scenario: User clears an annotation value
- **WHEN** the user clicks the clear/remove button on a set annotation
- **THEN** the system calls `DELETE /{checkin_id}/annotations/{annotation_definition_id}`

---

### Requirement: View Annotations in Read Mode

The system SHALL display currently set annotation values in the check-in view (non-edit mode).

#### Scenario: Read mode shows annotation values
- **WHEN** the user views a check-in that has annotations set
- **THEN** each annotation is shown with its definition name and current value (no edit controls)
