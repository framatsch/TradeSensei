# topbar-responsive-navigation Specification

## Purpose
Responsive TopBar navigation across phone (`< sm`), tablet (`sm`–`lg`), and desktop (`lg+`), ensuring the Home button, Sidebar toggle, BentoMenu, PortfolioSwitcher, and UserBadge are always accessible without horizontal overflow.

## Requirements

### Requirement: Home button is visible across all viewports
The `TopBar` component SHALL render the `Home` navigation link (`aria-label="Home"`) visibly on phone (`< sm`), tablet (`sm`–`lg`), and desktop (`lg+`) viewports, navigating to the user's configured `home_route` (or `/dashboard` by default).

#### Scenario: Home button is visible and tappable on a mobile phone viewport
- **WHEN** an authenticated user views any `/dashboard/*` page on a mobile phone viewport (`375×812`)
- **THEN** the `Home` link is visible in the left section of the `TopBar` next to the sidebar toggle and `BentoMenu` button
- **AND** tapping the `Home` link navigates to the user's configured `home_route`

#### Scenario: Home button remains visible on tablet and desktop viewports
- **WHEN** an authenticated user views any `/dashboard/*` page on a tablet (`768×1024`) or desktop (`1280×800`) viewport
- **THEN** the `Home` link is visible in the left section of the `TopBar`

### Requirement: TopBar layout prevents horizontal overflow and control collision on narrow viewports
The `TopBar` component SHALL use a flexible layout (`shrink-0` left and right action groups, `min-w-0 flex-1` center slot) rather than rigid equal-width columns, ensuring that the sidebar toggle, `Home` button, `BentoMenu`, `PortfolioSwitcher`, and `UserBadge` fit within a `375px` viewport without horizontal page overflow or overlapping controls. The `contextLabel` text in the `TopBar` SHALL be hidden on narrow screens (`hidden md:block`) so it does not crowd the `PortfolioSwitcher` on phones or narrow tablets.

#### Scenario: PortfolioSwitcher truncates cleanly alongside Home button on 375px phone
- **WHEN** an authenticated user is in the `portfolio` context with a long portfolio name on a `375×812` viewport
- **THEN** the sidebar toggle, `Home` link, `BentoMenu`, `PortfolioSwitcher`, and `UserBadge` are all visible on a single row
- **AND** the portfolio name truncates with an ellipsis without pushing `UserBadge` off-screen or causing horizontal overflow
