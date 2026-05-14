## ADDED Requirements

### Requirement: Model Book gallery renders starred trades and check-ins in a unified grid
The Model Book view SHALL display a single grid containing both starred trades (with `is_modelbook: true`) and starred check-ins (with `is_modelbook: true`), sorted by date descending. Trade cards and check-in cards SHALL be visually distinguishable but rendered side-by-side in the same grid.

#### Scenario: Unified grid shows both entity types
- **WHEN** there are 2 starred trades and 1 starred check-in
- **THEN** the Model Book gallery shows 3 cards sorted by date descending
- **AND** each card displays a type label ("Trade" or "Check-in")

#### Scenario: Empty Model Book shows a call-to-action
- **WHEN** no trades or check-ins are starred
- **THEN** the Model Book shows an empty state with instructions on how to star items

#### Scenario: Trade card shows domain-specific metadata
- **WHEN** a starred trade card is rendered
- **THEN** the card SHALL display: trade symbol, result (R-multiple or P&L), associated tags, and image preview (if any)

#### Scenario: Check-in card shows domain-specific metadata
- **WHEN** a starred check-in card is rendered
- **THEN** the card SHALL display: date, market phase label (color-coded), screenshot preview (if any), and any custom field values

#### Scenario: Clicking a trade card navigates to trade detail
- **WHEN** the user clicks on a trade card in the Model Book
- **THEN** the user is navigated to `/dashboard/trades/{id}`

#### Scenario: Clicking a check-in card navigates to check-in detail
- **WHEN** the user clicks on a check-in card in the Model Book
- **THEN** the user is navigated to `/dashboard/checkins/{date}`

### Requirement: Model Book gallery supports pagination
The gallery SHALL support pagination with 12 items per page by default. A "Load more" or page navigation control SHALL be visible when there are more items than the current page size.

#### Scenario: Pagination shows next page
- **WHEN** there are more starred items than the per-page limit
- **THEN** a "Next" button or "Load more" control is visible
- **AND** clicking it loads the next page of results

### Requirement: Model Book aggregation endpoint returns merged sorted entries
The system SHALL provide a `GET /model-book/entries` endpoint that returns a paginated list of starred trades and check-ins merged and sorted by date descending. Each item SHALL include a `type` discriminator field (`"trade"` or `"checkin"`).

#### Scenario: Endpoint returns mixed entries sorted by date
- **WHEN** `GET /model-book/entries` is called
- **THEN** the response includes items with `type: "trade"` and `type: "checkin"` interleaved by date
- **AND** items are sorted by date descending (most recent first)

#### Scenario: Endpoint supports entity_type filter
- **WHEN** `GET /model-book/entries?entity_type=trade` is called
- **THEN** only starred trade entries are returned

#### Scenario: Endpoint supports date range filter
- **WHEN** `GET /model-book/entries?from_date=2026-01-01&to_date=2026-03-31` is called
- **THEN** only entries within that date range are returned
