# symbol-filter Specification

## Purpose
TBD - created by archiving change symbol-filter-extended. Update Purpose after archive.
## Requirements
### Requirement: Symbol include/exclude filter on Trades list
The Trades list filter SHALL accept a list of symbols to include and a list of symbols to exclude. Prefix-match (case-insensitive) SHALL be applied: a filter value of `AAPL` matches trades where the symbol starts with `AAPL` (e.g. `AAPL`, `AAPL240119C00150000`). The `TradeFilters` interface SHALL replace the singular `symbol` field with `symbols: list[str] | None` and add `excluded_symbols: list[str] | None`.

#### Scenario: Single symbol include filter
- **WHEN** the user adds `AAPL` as an include symbol on the Trades filter bar
- **THEN** only trades whose symbol starts with `AAPL` (case-insensitive) are shown

#### Scenario: Multiple symbol include filter
- **WHEN** the user adds `AAPL` and `MSFT` as include symbols
- **THEN** only trades whose symbol starts with `AAPL` or starts with `MSFT` are shown

#### Scenario: Symbol exclude filter
- **WHEN** the user adds `TSLA` as an exclude symbol
- **THEN** trades whose symbol starts with `TSLA` are hidden; all other trades are shown

#### Scenario: Include and exclude combined
- **WHEN** the user includes `AAPL` and excludes `AAPL240119C` (an option root)
- **THEN** only `AAPL` equity trades are shown (option trades starting with `AAPL240119C` are excluded)

#### Scenario: No symbol filter active
- **WHEN** both include and exclude lists are empty
- **THEN** all trades are shown regardless of symbol

#### Scenario: Typing !-prefix adds to exclude list
- **WHEN** the user types `!TSLA` in the symbol tag input and presses Enter
- **THEN** `TSLA` is added as an exclude tag (rendered in red/destructive style)
- **AND** the input field is cleared

#### Scenario: Tags are uppercased on entry
- **WHEN** the user types `aapl` and presses Enter
- **THEN** the tag is stored and displayed as `AAPL`

#### Scenario: Tag can be removed individually
- **WHEN** the user clicks the × button on a symbol tag
- **THEN** that symbol is removed from the include or exclude list

---

### Requirement: Symbol include/exclude filter on Dashboard analytics
The `DashboardFilterConfig` schema SHALL include `symbols: list[str] | None` and `excluded_symbols: list[str] | None`. All analytics endpoints that accept `DashboardFilterConfig` SHALL apply these filters to the underlying trade set before aggregation, using the same prefix-match (case-insensitive) semantics.

#### Scenario: Dashboard metrics scoped to included symbols
- **WHEN** `symbols: ["AAPL"]` is set in the dashboard filter
- **THEN** all dashboard metrics (win rate, PnL, drawdown, etc.) reflect only trades whose symbol starts with `AAPL`

#### Scenario: Dashboard metrics exclude symbols
- **WHEN** `excluded_symbols: ["TSLA"]` is set in the dashboard filter
- **THEN** all dashboard metrics exclude trades whose symbol starts with `TSLA`

#### Scenario: Extended filter section on Dashboard filter bar
- **WHEN** the user opens the Dashboard
- **THEN** a collapsible "Extended Filters" section is visible below the standard filter bar
- **AND** the section is collapsed by default

#### Scenario: Extended filter badge count when active
- **WHEN** the user has one or more symbol or asset-class filters active in the extended section
- **AND** the extended section is collapsed
- **THEN** the toggle button shows a badge with the count of active extended filters (e.g. "Extended (2)")

---

### Requirement: Asset class filter on Dashboard analytics
The `DashboardFilterConfig` schema SHALL include `asset_classes: list[AssetClass] | None` using the same `AssetClass` enum already used in `TradeFilters`. All analytics endpoints SHALL apply this filter before aggregation.

#### Scenario: Dashboard filtered to equities only
- **WHEN** `asset_classes: ["EQUITY"]` is set in the dashboard filter
- **THEN** all dashboard metrics reflect only equity trades

#### Scenario: Multiple asset classes selected
- **WHEN** `asset_classes: ["EQUITY", "OPTION"]` is set
- **THEN** metrics include trades of both asset classes

#### Scenario: No asset class filter active
- **WHEN** `asset_classes` is null or empty
- **THEN** all asset classes are included in metrics

---

### Requirement: Reusable SymbolTagInput component
A `SymbolTagInput` React component SHALL be available at `frontend/components/ui/SymbolTagInput.tsx`. It SHALL accept separate `included` and `excluded` arrays and corresponding change callbacks. It SHALL render include tags in neutral style and exclude tags in destructive (red) style. It SHALL support the `!`-prefix typing shortcut for adding exclude tags.

#### Scenario: Component renders include and exclude tags
- **WHEN** `included=["AAPL", "MSFT"]` and `excluded=["TSLA"]` are passed
- **THEN** `AAPL` and `MSFT` render as neutral chips
- **AND** `TSLA` renders as a red/destructive chip

#### Scenario: Comma-separated entry adds multiple tags at once
- **WHEN** the user types `AAPL, MSFT` and presses Enter
- **THEN** both `AAPL` and `MSFT` are added to the included list

#### Scenario: Duplicate tag is silently ignored
- **WHEN** the user adds a symbol that already exists in the included list
- **THEN** the tag is not duplicated

### Requirement: UI Help text for Symbol Filtering
The `SymbolTagInput` component SHALL include a help icon (e.g., `Info` or `HelpCircle` from `lucide-react`) next to its label or input field. The icon SHALL display a tooltip or popover when hovered or clicked, explaining the syntax for symbol filtering.

#### Scenario: User views the help tooltip
- **WHEN** the user hovers over or clicks the help icon
- **THEN** a tooltip/popover appears explaining:
  - Prefix matching (e.g., "AAPL matches AAPL and AAPL240119C")
  - Multiple symbols using comma separation (e.g., "AAPL, MSFT")
  - Exclusion syntax using the `!` prefix (e.g., "!TSLA to exclude TSLA")

