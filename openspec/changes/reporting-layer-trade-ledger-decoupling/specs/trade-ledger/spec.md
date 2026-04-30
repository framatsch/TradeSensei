## MODIFIED Requirements

### Requirement: Trade list endpoint returns raw trade records only
The `GET /portfolios/{portfolio_id}/trades` endpoint SHALL return paginated `TradeRead` objects. It SHALL NOT compute any aggregate metrics, win rates, equity curves, or any other derived statistical value.

#### Scenario: Trade list response shape
- **WHEN** a user requests the trade list
- **THEN** the response contains only paginated `TradeRead` objects and cursor metadata — no metric fields are present in the response envelope

#### Scenario: Filtering for display purposes
- **WHEN** a user provides filter parameters (date range, playbook, tags, direction) to the trade list endpoint
- **THEN** the system returns the filtered raw trade records without computing any aggregates over them

#### Scenario: Attempt to add aggregation to trade list endpoint is rejected
- **WHEN** a code change attempts to add a `win_rate`, `pnl_sum`, or any computed metric field to the trade list response
- **THEN** the change SHALL be rejected in code review as a violation of ledger API contract
