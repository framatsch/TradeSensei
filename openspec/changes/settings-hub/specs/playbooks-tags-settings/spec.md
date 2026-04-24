## ADDED Requirements

### Requirement: Playbooks and Tags managed from Settings Hub
The Settings Hub SHALL provide a **Playbooks & Tags** tab that hosts the existing Playbook and
Tag management UI. The standalone routes `/dashboard/playbooks` and `/dashboard/tags` SHALL be
replaced with permanent redirects to `/dashboard/settings?tab=playbooks-tags`.

#### Scenario: User navigates to Playbooks & Tags tab
- **WHEN** the user opens Settings and selects the "Playbooks & Tags" tab
- **THEN** the existing `PlaybookList` and `TagList` components are rendered inside the tab

#### Scenario: Playbook CRUD works in Settings context
- **WHEN** the user creates, edits, or deletes a playbook from the Settings tab
- **THEN** the operations call the same API endpoints as before (`POST/PATCH/DELETE /api/v1/playbooks`) and the list updates

#### Scenario: Tag CRUD works in Settings context
- **WHEN** the user creates or deletes a tag from the Settings tab
- **THEN** the operations call the same API endpoints as before (`POST/DELETE /api/v1/tags`) and the list updates

#### Scenario: Old playbooks URL redirects
- **WHEN** a user navigates to `/dashboard/playbooks`
- **THEN** they are permanently redirected to `/dashboard/settings?tab=playbooks-tags`

#### Scenario: Old tags URL redirects
- **WHEN** a user navigates to `/dashboard/tags`
- **THEN** they are permanently redirected to `/dashboard/settings?tab=playbooks-tags`

#### Scenario: Sidebar no longer shows Playbooks and Tags links
- **WHEN** the dashboard sidebar is rendered
- **THEN** no "Playbooks" or "Tags" navigation items appear in the sidebar nav
