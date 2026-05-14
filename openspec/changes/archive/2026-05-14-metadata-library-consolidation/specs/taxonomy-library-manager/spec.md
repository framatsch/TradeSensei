## ADDED Requirements

### Requirement: Library Tags tab manages taxonomies
The system SHALL render a Taxonomy Manager at `/dashboard/library/tags` that displays all non-archived taxonomies and allows creating, editing, and archiving them. This replaces the legacy `TagList` component.

#### Scenario: List non-archived taxonomies
- **WHEN** the user navigates to Library > Tags
- **THEN** a list of all non-archived taxonomies is shown, each displaying name, color swatch, scope badge, and optional icon identifier

#### Scenario: Create taxonomy from Library
- **WHEN** the user fills in name, scope, and hex color and submits the "New Tag" form
- **THEN** a new taxonomy is created and immediately appears in the list

#### Scenario: Scope selector shows three options
- **WHEN** the create or edit form is open
- **THEN** a scope selector is visible with options: "Trades", "Check-ins", "Both"

#### Scenario: Edit taxonomy inline
- **WHEN** the user clicks an edit action on an existing taxonomy
- **THEN** an inline or modal form allows updating name, color, scope, description, and icon_identifier

#### Scenario: Archive taxonomy
- **WHEN** the user clicks the archive/delete action on a taxonomy with existing assignments
- **THEN** the taxonomy is soft-deleted (archived) and disappears from the active list

#### Scenario: Hard-delete taxonomy when unused
- **WHEN** the user deletes a taxonomy with no assignments
- **THEN** the taxonomy is permanently removed and disappears from the list

### Requirement: Library navigation includes three tabs
The system SHALL render a tab bar on the Library page with exactly three tabs: "Playbooks", "Tags", "Metrics". The active tab is highlighted. Navigating to `/dashboard/library` SHALL redirect to `/dashboard/library/playbooks`.

#### Scenario: Tab bar visible on all Library sub-pages
- **WHEN** the user is on any Library sub-page (playbooks, tags, metrics)
- **THEN** the three-tab bar is visible and the current tab is in the active state

#### Scenario: Metrics tab navigates to metrics page
- **WHEN** the user clicks the "Metrics" tab
- **THEN** the browser navigates to `/dashboard/library/metrics`
