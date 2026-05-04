## ADDED Requirements

### Requirement: Display target indices as badges
The system MUST render the selected market indices as lightweight badges in the timeline and detail views.

#### Scenario: Viewing a check-in with multiple indices
- **WHEN** the user views a check-in associated with "SPX" and "NDX"
- **THEN** the system displays neutral-colored badges for both indices near the date heading or market regime pill

### Requirement: Display external TradingView links
The system MUST provide clickable external TradingView links for the associated market indices.

#### Scenario: User clicks an index TradingView link
- **WHEN** the user clicks the "↗ SPX" link icon on a check-in
- **THEN** the defined TradingView URL opens in a new browser tab

### Requirement: Static visual evidence constraint
The system MUST NOT embed dynamic or live-fetching chart widgets for market indices. All visual context MUST be captured via the standard static image upload feature (`screenshot_urls`) and markdown text.

#### Scenario: User wishes to save market chart context
- **WHEN** a user wants to record the chart state for an index alongside their check-in
- **THEN** they upload a static screenshot which captures their exact annotations, avoiding UI main-thread blocking and preserving exact historical context
