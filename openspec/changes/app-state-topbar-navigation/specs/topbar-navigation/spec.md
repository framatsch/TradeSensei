## ADDED Requirements

### Requirement: TopBar is always visible on all dashboard pages
The system SHALL render a `TopBar` component as a sticky full-width `<header>`
above the sidebar + main content area on all dashboard pages (desktop and
mobile). The TopBar SHALL have a height of 56 px (`h-14`). The TopBar layout
is: `[☰ SidebarToggle] [⠿ BentoMenu] [wordmark]` (left) |
`[PortfolioSwitcher*]` (center, context-dependent) | `[UserBadge]` (right).
The old mobile-only hamburger header and the floating desktop `PanelLeftOpen`
button are both replaced by the SidebarToggle in the TopBar.

UI state reference:

```
Zustand 1 — Portfolio Workspace:
+---------------------------------------------------------------------------------+
| [☰] [⠿] Trade Sensei   [ ● Main Live Account (USD)  LIVE ▼ ]      [ JD ▼ ]    |
+------------------+--------------------------------------------------------------+
| -- WORKSPACE --  |  Performance Overview                                        |
|  Dashboard       |  Net P&L        Win Rate       Profit Factor                 |
|  Journal         |  $14,250.00     62.5%          1.85                          |
|  Reports         |                                                              |
|  Quick Import    |                                                              |
+------------------+--------------------------------------------------------------+

Zustand 2 — Global Library:
+---------------------------------------------------------------------------------+
| [☰] [⠿] Trade Sensei                                              [ JD ▼ ]    |
+------------------+--------------------------------------------------------------+
| -- LIBRARY --    |  Global Strategy Library                                     |
|  Playbooks       |  [ + Create New Playbook ]                                   |
|  Tags            |  | Trendfolge (Trend Following)                    |         |
+------------------+--------------------------------------------------------------+

Zustand 3 — Market Check-in:
+---------------------------------------------------------------------------------+
| [☰] [⠿] Trade Sensei                                              [ JD ▼ ]    |
+------------------+--------------------------------------------------------------+
| -- CHECK-IN --   |  Daily Market Context                                        |
|  Timeline (dim)  |  [ Date: 26. Apr 2026 ]                                      |
|                  |  [ Notes: CPI released. Volatility high... ]                 |
+------------------+--------------------------------------------------------------+

Zustand 4 — System Settings (via UserBadge → Settings):
+---------------------------------------------------------------------------------+
|  System Settings                                              [X] Close         |
+---------------------------------------------------------------------------------+
|  [ Portfolios ]  [ Accounts & Sync ]  [ Look & Feel ]  [ Features ]            |
|                                                                                 |
|  ★ Main Live Account          [Edit] [Delete]                                  |
|    Currency: USD | Type: LIVE | Linked: IBKR (API)                             |
+---------------------------------------------------------------------------------+
```

#### Scenario: TopBar visible on desktop
- **WHEN** the user is on any `/dashboard/*` page on a viewport ≥ 1024 px
- **THEN** the TopBar is visible at the top of the viewport with SidebarToggle + BentoMenu + wordmark on the left, and UserBadge on the right

#### Scenario: TopBar visible on mobile
- **WHEN** the user is on any `/dashboard/*` page on a viewport < 1024 px
- **THEN** the TopBar is visible with SidebarToggle as the first element; the old mobile hamburger+logo bar is no longer present

---

### Requirement: SidebarToggle controls sidebar visibility on all viewports
The TopBar SHALL contain a `SidebarToggle` button (`☰`) as the first element
in the left slot. Clicking it SHALL toggle the sidebar open/closed on all
viewport sizes. The existing floating `PanelLeftOpen` desktop button and the
mobile-only hamburger `<header>` SHALL be removed; the SidebarToggle is their
single replacement. The sidebar open/closed state SHALL continue to be persisted
in `localStorage` under `"desktopSidebarOpen"` and togglable via `Cmd/Ctrl+B`.

#### Scenario: SidebarToggle opens closed sidebar
- **WHEN** the sidebar is closed and the user clicks `[☰]` in the TopBar
- **THEN** the sidebar slides open on all viewport sizes

#### Scenario: SidebarToggle closes open sidebar
- **WHEN** the sidebar is open and the user clicks `[☰]` in the TopBar
- **THEN** the sidebar closes on all viewport sizes

#### Scenario: No floating open button on desktop
- **WHEN** the sidebar is closed on a desktop viewport
- **THEN** there is no floating `PanelLeftOpen` button in the top-left of the main content area; the TopBar SidebarToggle is the only way to reopen the sidebar (besides `Cmd/Ctrl+B`)

---

### Requirement: Wordmark navigates to the user's configured home route
The `"Trade Sensei"` wordmark in the TopBar left slot SHALL be rendered as a
`<Link>`. Its destination SHALL be the value of the `home_route` key from
`user_settings` (default: `"/dashboard"`). The three valid values are
`"/dashboard"` (Portfolio Overview), `"/dashboard/trades"` (Journal), and
`"/dashboard/library"` (Strategy & Tags). The wordmark SHALL NOT open the
`AboutModal` — that action is moved to the UserBadge dropdown.

#### Scenario: Logo navigates to configured home
- **WHEN** `home_route` is set to `"/dashboard/trades"` in user settings
- **THEN** clicking the wordmark navigates to `/dashboard/trades`

#### Scenario: Logo defaults to Portfolio Overview
- **WHEN** `home_route` is not set in user settings
- **THEN** clicking the wordmark navigates to `/dashboard`

---

### Requirement: BentoMenu provides application context switching
The `BentoMenu` component SHALL render a nine-dot grid icon button at the
top-left of the TopBar (immediately right of the SidebarToggle). Clicking it
SHALL open a popover listing the three application contexts. Selecting a context
SHALL update `activeContext` in `appContextStore`, close the popover, and
navigate to the context's root route.

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
- **THEN** the PortfolioSwitcher is rendered in the TopBar center showing the colour chip, portfolio name, currency code in parentheses, and a LIVE or PAPER badge

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
The PortfolioSwitcher trigger SHALL display the active portfolio as:
`[colour chip] [name] ([currency]) [LIVE|PAPER badge] [▼]`.
Clicking it SHALL open a dropdown listing all user portfolios.

#### Scenario: Dropdown opens
- **WHEN** the user clicks (or presses Enter/Space on) the PortfolioSwitcher trigger
- **THEN** a dropdown appears listing all portfolios, each showing: colour chip, name, currency code, LIVE/PAPER badge; the currently active portfolio has a checkmark

#### Scenario: User selects a different portfolio
- **WHEN** the user clicks a portfolio in the dropdown
- **THEN** `setActivePortfolio(id)` is called, the dropdown closes, and the TopBar trigger immediately reflects the newly selected portfolio's name, currency, and badge

#### Scenario: Keyboard navigation
- **WHEN** the dropdown is open
- **THEN** the user can navigate items with ArrowUp/ArrowDown, confirm with Enter, and close with Escape

---

### Requirement: Sidebar displays a context label header above nav items
The sidebar SHALL show a static text header above the navigation items that
reflects the active context: `"— WORKSPACE —"` for portfolio, `"— LIBRARY —"`
for library, `"— CHECK-IN —"` for checkin. The header is non-interactive and
styled as `text-xs text-muted-foreground uppercase tracking-widest`.

#### Scenario: Workspace context label shown
- **WHEN** `activeContext === 'portfolio'` and the sidebar is open
- **THEN** the sidebar shows `"— WORKSPACE —"` above Dashboard, Journal, Reports, Quick Import

#### Scenario: Library context label shown
- **WHEN** `activeContext === 'library'` and the sidebar is open
- **THEN** the sidebar shows `"— LIBRARY —"` above Playbooks, Tags

#### Scenario: Check-in context label shown
- **WHEN** `activeContext === 'checkin'` and the sidebar is open
- **THEN** the sidebar shows `"— CHECK-IN —"` above the disabled Timeline entry

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
Clicking it SHALL open a dropdown with: Settings, Help, About (with version),
a divider, and Sign Out.

```
UserBadge Dropdown:
+---------------------------+
|  Settings                 |
|  Help                     |
|  About  v0.25.0           |
|  ───────────────────      |
|  Sign Out                 |
+---------------------------+
```

#### Scenario: Initials derived from user name
- **WHEN** the authenticated user has `first_name` and `last_name`
- **THEN** the badge shows the first character of each, uppercased (e.g. "JD")

#### Scenario: Initials fallback to email
- **WHEN** the authenticated user has no `first_name` or `last_name`
- **THEN** the badge shows the first two characters of the email address, uppercased

#### Scenario: Dropdown contains all five items
- **WHEN** the user clicks the UserBadge
- **THEN** a dropdown appears with: "Settings" linking to `/dashboard/settings`, "Help" opening the help window, "About v{version}" showing the app version from `NEXT_PUBLIC_APP_VERSION`, a visual divider, and "Sign Out"

#### Scenario: Help opens help window
- **WHEN** the user clicks "Help" in the UserBadge dropdown
- **THEN** `window.open('/help', ...)` is called with the same parameters as the current sidebar Help button

#### Scenario: About shows version
- **WHEN** the user clicks "About v{version}" in the UserBadge dropdown
- **THEN** the `AboutModal` opens showing the app version

#### Scenario: Sign out via UserBadge
- **WHEN** the user clicks "Sign Out" in the UserBadge dropdown
- **THEN** the `useLogout()` mutation is called, the token is cleared, and the user is redirected to `/login`

---

### Requirement: Sidebar no longer contains sign-out, help, account-management, or global library links
The sidebar SHALL be cleaned of: the sign-out link, the help button, any
account-selection UI, Playbooks and Tags links (moved to Library context), and
the mobile-only hamburger top bar. These are all replaced by the TopBar.

#### Scenario: Sign out not present in sidebar
- **WHEN** the user views the sidebar in any context
- **THEN** there is no "Sign Out" link in the sidebar

#### Scenario: Help not present in sidebar
- **WHEN** the user views the sidebar in any context
- **THEN** there is no "Help" button in the sidebar

#### Scenario: Playbooks and Tags not in portfolio sidebar
- **WHEN** `activeContext === 'portfolio'`
- **THEN** there are no "Playbooks" or "Tags" items in the sidebar

#### Scenario: Account filter not present as sidebar link
- **WHEN** the user views the sidebar
- **THEN** there is no standalone "Accounts" nav item separate from Settings
