## MODIFIED Requirements

### Requirement: Settings Check-in page shows only Market Indexes
The system SHALL render only the Market Indexes management section in Settings > Check-in. Market Phases and Custom Metrics sections SHALL NOT be visible.

#### Scenario: Check-in settings shows Market Indexes only
- **WHEN** the user navigates to Settings > Check-in
- **THEN** only the Market Indexes table and its controls are rendered
- **AND** no Market Phases section is present
- **AND** no Custom Metrics section is present

#### Scenario: CheckinSettings unit test mocks only market index hooks
- **WHEN** the `CheckinSettings` component is rendered in a unit test
- **THEN** only `useMarketIndexes`, `useCreateMarketIndex`, `useUpdateMarketIndex`, and `useDeleteMarketIndex` are mocked
- **AND** no mock for `useMarketPhases`, `useCreateMarketPhase`, `useUpdateMarketPhase`, `useCheckinFields`, `useCreateCheckinField`, or `useUpdateCheckinField` is present

#### Scenario: Market Index create form renders
- **WHEN** the user clicks the add market index button
- **THEN** inputs for symbol, name, and TradingView URL are shown

#### Scenario: Market Index delete works
- **WHEN** the user clicks delete on an existing market index
- **THEN** the index is removed from the list
