# library-responsive-ui Specification

## Purpose
Responsive layouts for the Global Library (`PlaybookList`, `PlaybookFilterBar`, `TaxonomyManager`, `AnnotationManager`) across phone (card list + sort select), tablet (`overflow-x-auto` table + touch-visible actions), and desktop.

## Requirements

### Requirement: Playbooks overview renders as a card list on mobile and a scrollable table on tablet/desktop
On viewports below `md` (`< 768px`), `PlaybookList` SHALL render each playbook as a tappable card (`data-testid="playbook-card-list"`) instead of a multi-column table row. On viewports `md` and wider (`>= 768px`), `PlaybookList` SHALL render the 5-column sortable table inside an `overflow-x-auto` container so columns are never clipped on tablet portrait (`768px`) or desktop viewports.

Each mobile playbook card SHALL display:
1. Header row: Playbook name (`font-semibold`) and the interactive `Active` / `Inactive` status toggle button.
2. Metadata row: Formatted creation date (`Created <Mon D, YYYY>`) and an explicit `Edit` action button (`aria-label="Edit <name>"`) that navigates to `/dashboard/library/playbooks/<id>?edit=true` without triggering card navigation.
3. Tags row (when taxonomy tags are assigned): Taxonomy tag pills with their configured colors.

Tapping the card body (outside the status toggle and `Edit` button) SHALL navigate to `/dashboard/library/playbooks/<id>`.

#### Scenario: Playbooks render as cards without horizontal clipping on a 375px phone
- **WHEN** a user opens `/dashboard/library/playbooks` on a `375×812` viewport
- **THEN** playbooks are rendered as stacked cards inside `data-testid="playbook-card-list"`
- **AND** each card shows the playbook name, interactive `Active`/`Inactive` badge, creation date, `Edit` button, and assigned tags without horizontal overflow

#### Scenario: Playbooks table is scrollable and unclipped on tablet and desktop
- **WHEN** a user opens `/dashboard/library/playbooks` on a `768×1024` tablet or `1280×800` desktop viewport
- **THEN** the 5-column sortable table (`Name`, `Tags`, `Status`, `Created`, `Actions`) is visible inside an `overflow-x-auto` container and the mobile card list is hidden

#### Scenario: Single unified page header without description clutter and with compact New Playbook button
- **WHEN** a user opens `/dashboard/library/playbooks` on any viewport (`375×812`, `768×1024`, or `1280×800`)
- **THEN** a single header row displaying only the title `Playbooks` (`text-2xl font-bold`) on the left and the compact single-line `New Playbook` button (`shrink-0 whitespace-nowrap h-9`) on the right is rendered
- **AND** neither a duplicate `Playbooks` heading nor redundant description subtitles are rendered above the filter bar

### Requirement: Touch-accessible actions and responsive detail headers in Global Library Tags and Metrics
In `TaxonomyManager` (`/dashboard/library/tags`) and `AnnotationManager` (`/dashboard/library/metrics`), the system SHALL ensure touch accessibility and responsive wrapping:
1. Card-level `Edit` and `Delete` icon buttons SHALL be visible by default on viewports below `lg` (`opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus-within:opacity-100`) so touch users on phones and tablets can trigger them directly.
2. Read-only detail view headers SHALL wrap (`flex-wrap gap-3`) so long tag or metric titles do not push `Edit`, `Archive`/`Unarchive`, and `Delete` action buttons outside the card on narrow viewports.

#### Scenario: Tag and Metric card actions are visible on touch viewports
- **WHEN** a user views `/dashboard/library/tags` or `/dashboard/library/metrics` on a `375×812` or `768×1024` viewport
- **THEN** the `Edit` and `Delete` buttons on each card are visible without hovering

#### Scenario: Detail header wraps cleanly on narrow screens
- **WHEN** a user opens the detail view of a Tag or Metric on a `375×812` viewport
- **THEN** the back button, title, and `Edit` / `Archive` / `Delete` action buttons wrap within the card boundaries without horizontal overflow
