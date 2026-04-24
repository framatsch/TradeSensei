## ADDED Requirements

### Requirement: TopBar is always visible on all dashboard pages
The system SHALL render a `TopBar` component as a sticky full-width `<header>`
above the sidebar + main content area on all dashboard pages (desktop and
mobile). The TopBar SHALL have a height of 56 px (`h-14`).

#### Scenario: TopBar visible on desktop
- **WHEN** the user is on any `/dashboard/*` page on a viewport ≥ 1024 px
- **THEN** the TopBar is visible at the top of the viewport with logo on the left, PortfolioSwitcher in the center, and UserBadge on the right

#### Scenario: TopBar visible on mobile
- **WHEN** the user is on any `/dashboard/*` page on a viewport < 1024 px
- **THEN** the TopBar is visible (the old mobile hamburger+logo bar is no longer present)

---

### Requirement: PortfolioSwitcher shows active portfolio identity
The PortfolioSwitcher component SHALL display the active portfolio's name, a
colour indicator dot (derived from `color_hex`), and a status badge
(`LIVE` or `PAPER` based on `is_paper`).

#### Scenario: Active portfolio displayed
- **WHEN** the user has an active portfolio selected
- **THEN** the PortfolioSwitcher shows a coloured dot (12 px circle, `background-color: portfolio.color_hex`), the portfolio name, and a badge reading `LIVE` (green) or `PAPER` (amber)

#### Scenario: Loading state while portfolio resolves
- **WHEN** `isLoading` is `true` from `useActivePortfolio()`
- **THEN** the PortfolioSwitcher renders a skeleton placeholder (no name, no dot)

---

### Requirement: PortfolioSwitcher dropdown allows switching active portfolio
The PortfolioSwitcher SHALL open a dropdown listing all user portfolios when
activated. Selecting a portfolio SHALL set it as active.

#### Scenario: Dropdown opens
- **WHEN** the user clicks (or presses Enter/Space on) the PortfolioSwitcher trigger
- **THEN** a dropdown appears listing all portfolios, each showing: colour dot, name, LIVE/PAPER badge; the currently active portfolio has a checkmark

#### Scenario: User selects a different portfolio
- **WHEN** the user clicks a portfolio in the dropdown
- **THEN** `setActivePortfolio(id)` is called, the dropdown closes, and the TopBar immediately reflects the newly selected portfolio

#### Scenario: Keyboard navigation
- **WHEN** the dropdown is open
- **THEN** the user can navigate items with ArrowUp/ArrowDown, confirm with Enter, and close with Escape

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

### Requirement: Sidebar no longer contains sign-out or account-management links
The sidebar SHALL be cleaned of: the sign-out link at the bottom, any
account-selection UI, and the mobile-only hamburger top bar. These concerns
move to `TopBar` and `UserBadge`.

#### Scenario: Sign out not present in sidebar
- **WHEN** the user views the sidebar
- **THEN** there is no "Sign Out" link in the sidebar

#### Scenario: Account filter not present as sidebar link
- **WHEN** the user views the sidebar
- **THEN** there is no standalone "Accounts" nav item linking to account management separate from Settings
