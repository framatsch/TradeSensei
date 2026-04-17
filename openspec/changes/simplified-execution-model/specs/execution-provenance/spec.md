## Requirements

### Requirement: Execution provenance is tracked via `origin` field

The system SHALL record the provenance of every execution using an immutable `origin` field set at creation time. Valid values are `imported`, `manual`, `merged`, `split`.

#### Scenario: Broker-imported execution has origin=imported
- **WHEN** an import file is processed and a new execution is created from a `BrokerRawTransaction`
- **THEN** `logical_executions.origin` is set to `'imported'`
- **AND** `origin` is not modifiable via the PATCH endpoint

#### Scenario: User-created execution has origin=manual
- **WHEN** a user creates an execution via `POST /executions` without a BRT link
- **THEN** `logical_executions.origin` is set to `'manual'`

#### Scenario: Split children have origin=split with parent linkage
- **WHEN** a user splits an execution
- **THEN** the original execution is marked `deleted=true`
- **AND** two new child executions are created with `origin='split'` and `parent_id=original.id`

#### Scenario: Merged execution has origin=merged with parent linkage
- **WHEN** a user merges two or more executions
- **THEN** all source executions are marked `deleted=true`
- **AND** a new merged execution is created with `origin='merged'` and `parent_id=primary_source.id`

---

### Requirement: User edits to imported executions are tracked via `user_modified`

The system SHALL set `user_modified=true` automatically when a user patches an execution whose `origin` is `imported`. This flag is not set for `manual`, `merged`, or `split` executions (those are always user-controlled).

#### Scenario: Patching price of imported execution sets user_modified=true
- **WHEN** `PATCH /executions/{id}` is called on an execution with `origin='imported'`
- **THEN** `user_modified` is set to `true`
- **AND** the import service still treats the execution as protected (`deleted` flag governs resurrection, not `user_modified`)

#### Scenario: user_modified is not set for manual executions
- **WHEN** `PATCH /executions/{id}` is called on an execution with `origin='manual'`
- **THEN** `user_modified` remains `false`

#### Scenario: user_modified flag is visible in API response
- **WHEN** `GET /executions/{id}` is called
- **THEN** the response includes `user_modified: true | false`

---

### Requirement: Execution status badge derives from origin + flags

The UI SHALL display a status badge derived from the combination of `origin`, `user_modified`, and `deleted`. No server-side status enum is exposed.

| Condition | Badge label | Color |
|---|---|---|
| `origin=imported`, `user_modified=false`, `deleted=false` | imported | blue |
| `origin=imported`, `user_modified=true`, `deleted=false` | edited | amber |
| `origin=manual` | manual | violet |
| `origin=merged` | merged | orange |
| `origin=split` | split | cyan |
| `deleted=true` (any origin) | deleted | gray, 50% opacity row |

#### Scenario: Imported execution shows imported badge
- **WHEN** an execution has `origin='imported'`, `user_modified=false`, `deleted=false`
- **THEN** the badge displays "imported" in blue

#### Scenario: Edited execution shows edited badge
- **WHEN** an execution has `origin='imported'`, `user_modified=true`, `deleted=false`
- **THEN** the badge displays "edited" in amber

#### Scenario: Deleted execution is hidden by default with restore option
- **WHEN** `deleted=true` for any execution
- **THEN** the row is hidden in `ExecutionLegsTable` unless the "Show deleted" toggle is active
- **AND** when shown, the row renders at 50% opacity with a `[Restore]` button
- **AND** the badge displays "deleted" in gray
