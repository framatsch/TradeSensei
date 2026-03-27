## ADDED Requirements

### Requirement: Persisted saved trade filters
The system SHALL persist saved trade filters as named views with a stable UUID identifier, a scope flag, and a structured filter definition.

Saved trade filters SHALL include:
- `id` (UUID)
- `name` (string)
- `scope` (enum: `user`, `system`)
- `definition` (JSON object matching supported trade query fields)
- `owner_id` (UUID, nullable for system)
- `needs_review` (boolean, default false)
- `created_at` / `updated_at` (timestamp)

The `definition` SHALL be limited to the same fields already supported by trade query parameters.

#### Scenario: Create a user-owned saved filter
- **WHEN** an authenticated user creates a saved filter with a name and definition
- **THEN** the system stores it with `scope = user`, `owner_id = <user_id>`, and a generated UUID

#### Scenario: Global filter is read-only
- **WHEN** a user attempts to update or delete a filter with `scope = system`
- **THEN** the API rejects the request with a permission error

### Requirement: List saved trade filters
The system SHALL provide a list endpoint returning all saved trade filters visible to the user, including system filters and user-owned filters.

#### Scenario: List returns system and user filters
- **WHEN** an authenticated user requests their saved filters
- **THEN** the response includes all `scope = system` filters and all filters where `owner_id = <user_id>`

### Requirement: Apply saved filter definitions
The system SHALL apply a saved filter's `definition` to the trades query using the same semantics as existing trade query parameters.

#### Scenario: Apply saved filter definition
- **WHEN** a user selects a saved filter and requests trades
- **THEN** the returned trades match the saved definition's criteria using AND logic

### Requirement: Allow name collisions
The system SHALL allow multiple saved filters with the same `name`, using UUIDs as the primary identifier.

#### Scenario: Duplicate names are permitted
- **WHEN** a user creates a filter named "Winners" that already exists
- **THEN** the request succeeds and a new UUID is assigned

### Requirement: Handle field changes with review flag
The system SHALL mark saved filters as `needs_review = true` when a filter definition contains fields that can no longer be mapped to supported trade query fields.

#### Scenario: Field change sets needs_review
- **WHEN** a filter definition references a deprecated or renamed field without a mapping
- **THEN** the saved filter is flagged `needs_review = true` and returned as such in list responses

### Requirement: UI indicator for read-only filters
The UI SHALL display a lock icon for filters where `scope = system`.

#### Scenario: System filter shows lock
- **WHEN** a system filter is listed in the Trades navigation
- **THEN** it is labeled with a lock icon and treated as read-only
