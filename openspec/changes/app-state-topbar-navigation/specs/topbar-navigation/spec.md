## ADDED Requirements

### Requirement: TopBar is always visible on all dashboard pages
The system SHALL render a `TopBar` component as a sticky full-width `<header>`
above the sidebar + main content area on all dashboard pages (desktop and
mobile). The TopBar SHALL have a height of 56 px (`h-14`). The TopBar layout
is: BentoMenu + wordmark (left) | PortfolioSwitcher (center, context-dependent)
| UserBadge (right).

#### Scenario: TopBar visible on desktop
- **WHEN** the user is on any `/dashboard/*` page on a viewport ≥ 1024 px
- **THEN** the TopBar is visible at the top of the viewport with BentoMenu + wordmark on the left, and UserBadge on the right

#### Scenario: TopBar visible on mobile
- **WHEN** the user is on any `/dashboard/*` page on a viewport < 1024 px
- **THEN** the TopBar is visible (the old mobile hamburger+logo bar is no longer present)

---

### Requirement: BentoMenu provides application context switching
The `BentoMenu` component SHALL render a nine-dot grid icon button at the
top-left of the TopBar. Clicking it SHALL open a popover listing the three
application contexts. Selecting a context SHALL update `activeContext` in
`appContextStore`, close the popover, and navigate to the context's root route.

#### Scenario: BentoMenu opens context list
- **WHEN** the user clicks the BentoMenu button
- **THEN** a popover appears listing three entries: "Portfolio Workspace", "Global Library", "Market Check-in" — each with a distinct icon and an active indicator on the currently selected context

#### Scenario: User switches to Global Library
- **WHEN** the user clicks "Global Library" in the BentoMenu
- **THEN** `appContextStore.setActiveContext('library')` is called, the popover closes, and the browser navigates to `/dashboard/library`; the sidebar updates to show Playbooks and Tags; the PortfolioSwitcher disappears from the TopBar center

#### Scenario: User switches to Portfolio Workspace
- **WHEN** the user clicks "Portfolio Workspace" in the BentoMenu
- **THEN** `appContextStore.setActiveContext('portfolio')` is called, navigation goes to `/dashboard`; the sidebar shows Dashboard/Journal/Reports/Import; the PortfolioSwitcher appears in the TopBar center

#### Scenario: Market Check-in shows placeholder
- **WHEN** the user clicks "Market Check-in" in the BentoMenu
- **THEN** the user is navigated to `/dashboard/checkin` which renders a "Coming Soon" placeholder; the sidebar shows a single disabled "Timeline" entry

#### Scenario: BentoMenu keyboard navigation
- **WHEN** the BentoMenu popover is open
- **THEN** the user can navigate entries with ArrowUp/ArrowDown, confirm with Enter, and close with Escape

---

### Requirement: PortfolioSwitcher is visible only in Portfolio Workspace context
The `PortfolioSwitcher` component SHALL render in the TopBar center slot only
when `activeContext === 'portfolio'`. It SHALL NOT render in `library` or
`checkin` contexts.

#### Scenario: PortfolioSwitcher visible in portfolio context
- **WHEN** `activeContext === 'portfolio'`
- **THEN** the PortfolioSwitcher is rendered in the TopBar center showing the active portfolio name and colour dot

#### Scenario: PortfolioSwitcher hidden in library context
- **WHEN** `activeContext === 'library'`
- **THEN** the TopBar center slot is empty (no PortfolioSwitcher rendered)

#### Scenario: PortfolioSwitcher hidden in checkin context
- **WHEN** `activeContext === 'checkin'`
- **THEN** the TopBar center slot is empty (no PortfolioSwitcher rendered)

#### Scenario: Loading state while portfolio resolves
- **WHEN** `activeContext === 'portfolio'` AND `isLoading` is `true` from `useActivePortfolio()`
- **THEN** the PortfolioSwitcher renders a skeleton placeholder (no name, no dot)

---

### Requirement: PortfolioSwitcher dropdown allows switching active portfolio
The PortfolioSwitcher SHALL open a dropdown listing all user portfolios when
activated. Selecting a portfolio SHALL set it as active.

#### Scenario: Dropdown opens
- **WHEN** the user clicks (or presses Enter/Space on) the PortfolioSwitcher trigger
- **THEN** a dropdown appears listing all portfolios, each showing: colour chip, name; the currently active portfolio has a checkmark

#### Scenario: User selects a different portfolio
- **WHEN** the user clicks a portfolio in the dropdown
- **THEN** `setActivePortfolio(id)` is called, the dropdown closes, and the TopBar immediately reflects the newly selected portfolio

#### Scenario: Keyboard navigation
- **WHEN** the dropdown is open
- **THEN** the user can navigate items with ArrowUp/ArrowDown, confirm with Enter, and close with Escape

---

### Requirement: Sidebar nav-items are context-specific
The sidebar SHALL render different navigation items depending on `activeContext`.
The sidebar shell (width, collapse behaviour, styling) is shared across all
contexts.

#### Scenario: Portfolio Workspace sidebar
- **WHEN** `activeContext === 'portfolio'`
- **THEN** the sidebar shows: Dashboard, Journal, Reports, Quick Import

#### Scenario: Global Library sidebar
- **WHEN** `activeContext === 'library'`
- **THEN** the sidebar shows: Playbooks, Tags

#### Scenario: Market Check-in sidebar
- **WHEN** `activeContext === 'checkin'`
- **THEN** the sidebar shows: Timeline (item rendered but disabled / greyed out as placeholder)

---

### Requirement: UserBadge displays user identity and provides account actions
The UserBadge component SHALL render the user's initials in a coloured circle.
Clicking it SHALL open a dropdown with links to Settings and a Sign Out action.

#### Scenario: Initials derived from user name
- **WHEN** the authenticated user has `first_name` and `last_name`
- **THEN** the badge shows the first character of each, uppercased (e.g. "JD")

#### Scenario: Initials fallback to email
- **WHEN** the authenticated user has no `first_name` or `last_name`
- **THEN** the badge shows the first two characters of the email address, uppercased

#### Scenario: Dropdown opens and provides navigation
- **WHEN** the user clicks the UserBadge
- **THEN** a dropdown appears with "Settings" linking to `/dashboard/settings` and "Sign Out" which triggers the logout mutation

#### Scenario: Sign out via UserBadge
- **WHEN** the user clicks "Sign Out" in the UserBadge dropdown
- **THEN** the `useLogout()` mutation is called, the token is cleared, and the user is redirected to `/login`

---

### Requirement: Sidebar no longer contains sign-out, account-management, or global library links
The sidebar SHALL be cleaned of: the sign-out link at the bottom, any
account-selection UI, Playbooks and Tags links (moved to Library context), and
the mobile-only hamburger top bar.

#### Scenario: Sign out not present in sidebar
- **WHEN** the user views the sidebar in any context
- **THEN** there is no "Sign Out" link in the sidebar

#### Scenario: Playbooks and Tags not in portfolio sidebar
- **WHEN** `activeContext === 'portfolio'`
- **THEN** there are no "Playbooks" or "Tags" items in the sidebar

#### Scenario: Account filter not present as sidebar link
- **WHEN** the user views the sidebar
- **THEN** there is no standalone "Accounts" nav item separate from Settings
