## MODIFIED Requirements

### Requirement: Execution timestamp is editable in the inline editor
The system SHALL allow users to edit the `executed_at` field of an execution leg via a datetime picker in the inline edit form. The stored value SHALL be UTC ISO-8601; the picker SHALL display local time but convert to UTC before sending to the API.

#### Scenario: Datetime picker pre-fills with current executed_at
- **WHEN** the user enters edit mode on an execution leg
- **THEN** the datetime input is pre-filled with the execution's `executed_at` converted to the browser's local time

#### Scenario: Timestamp change is sent as UTC ISO-8601
- **WHEN** the user modifies the datetime input and saves
- **THEN** the API receives `PATCH /executions/{id}` with `executed_at` as a UTC ISO-8601 string (ending in `Z` or with `+00:00` offset)

#### Scenario: Empty timestamp input blocks save
- **WHEN** the user clears the datetime input and attempts to save
- **THEN** the save button is disabled (or the field is highlighted as required) and no API call is made

---

## ADDED Requirements

### Requirement: Opened At and Closed At auto-sync from execution leg timestamps in Advanced Mode
When the New Trade form is in Advanced Mode, the `opened_at` and `closed_at` fields SHALL be derived automatically from the min and max `executed_at` values of the execution legs array respectively. Manual editing of these fields SHALL be disabled when Advanced Mode is active.

#### Scenario: opened_at derived from earliest leg timestamp
- **WHEN** the user is in Advanced Mode and has added execution legs
- **THEN** the `Opened At` field is automatically set to the `executed_at` of the earliest leg
- **THEN** the `Opened At` field input is disabled (non-editable)

#### Scenario: closed_at derived from latest leg timestamp (when more than one leg)
- **WHEN** the user is in Advanced Mode and has added two or more execution legs with different timestamps
- **THEN** the `Closed At` field is automatically set to the `executed_at` of the latest leg
- **THEN** the `Closed At` field input is disabled (non-editable)

#### Scenario: closed_at cleared when only one leg exists
- **WHEN** the user is in Advanced Mode and exactly one execution leg is present
- **THEN** the `Closed At` field is set to empty (null)

#### Scenario: Timestamps restored to manual editing when Advanced Mode is turned off
- **WHEN** the user disables Advanced Mode
- **THEN** the `Opened At` and `Closed At` fields become editable again
- **THEN** their values are NOT automatically reset

#### Scenario: Empty leg array leaves timestamps unchanged
- **WHEN** the user is in Advanced Mode but no execution legs have been added
- **THEN** the `Opened At` and `Closed At` fields show their last manually-entered values

### Requirement: New Trade form requires at least one execution leg in Advanced Mode
When the New Trade form is submitted with Advanced Mode active, the form SHALL require at least one execution leg to be present. Submission with zero legs in Advanced Mode SHALL be blocked with a validation error.

#### Scenario: Submission blocked with zero legs in Advanced Mode
- **WHEN** the user enables Advanced Mode and attempts to submit the form without adding any legs
- **THEN** the form displays a validation error: "At least one execution leg is required in Advanced Mode"
- **THEN** no API call is made
