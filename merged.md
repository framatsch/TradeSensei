#########################
# openspec/changes/checkin-market-index/design.md
#########################

## Context

The daily check-in feature currently captures user sentiment, playbook adherence, and trading metrics, but lacks an explicit connection to broader market conditions. Traders often need to correlate their performance with market indices (e.g., S&P 500, NASDAQ) to understand if their results are alpha or beta. 

We need to associate a market index with a check-in, store configurable index definitions per user, and display an embedded OHLC chart using cached data from our market data provider. The backend already has an `OhlcPrice` model used for caching external provider data, which is suitable for this feature.

## Goals / Non-Goals

**Goals:**
- Allow users to define and manage custom market indices (Symbol, Name, TradingView URL).
- Seed default market indices (e.g., SPX, NDX, DAX) for new and existing users.
- Link a specific market index to a daily check-in.
- Fetch and display cached daily/weekly OHLC candles for the associated index within the check-in view.
- Utilize the existing `OhlcPrice` caching infrastructure to minimize external API calls.

**Non-Goals:**
- Intraday (minute-level) caching or real-time streaming for the index chart.
- Complex technical analysis tools on the embedded chart (basic OHLC/volume is sufficient).
- Automated correlation analysis between the user's trades and the index.

## Decisions

### 1. Data Model: Market Index Definitions
We will create a new `market_index_definitions` table to store index configurations per user.

*Rationale:* Hardcoding indices limits flexibility for users who trade niche markets (e.g., specific commodities or crypto). Scoping to the user allows personalization while still enabling us to seed defaults.
*Alternatives Considered:* A global, non-configurable list of indices. Rejected because it limits user flexibility and requires code deployments to add new indices.

### 2. Check-in Association
We will add a nullable `market_index_id` (UUID) foreign key to the `daily_checkins` table.

*Rationale:* A direct foreign key is the standard relational approach. It's nullable to ensure backward compatibility and because linking an index is optional.
*Alternatives Considered:* Storing the symbol string directly on the check-in. Rejected because it breaks referential integrity and makes updating index metadata (like the TradingView link) harder.

### 3. Caching Index Data
We will reuse the existing `OhlcPrice` table and `MarketDataService` to cache and serve the index OHLC data.

*Rationale:* The `OhlcPrice` table is specifically designed to cache interval-based OHLC data from external providers (e.g., LSEG). Reusing it avoids duplicating caching logic and schema definitions. The frontend will request data via the existing proxy endpoint (`/api/v1/market-data/prices/{symbol}/history`), which automatically checks the database cache before querying the upstream Hub.
*Alternatives Considered:* Creating a separate caching table for indices. Rejected as redundant and contrary to the DRY principle.

### 4. API Design
- **CRUD Endpoints:** `GET /api/v1/market-indexes`, `POST /api/v1/market-indexes`, `PUT /api/v1/market-indexes/{id}`, `DELETE /api/v1/market-indexes/{id}`.
- **Check-in Endpoints:** Update `POST /api/v1/checkins` and `PUT /api/v1/checkins/{id}` payloads to accept `market_index_id`. Update response models to include the nested `market_index` object.
- **Market Data:** No new endpoints needed. We will use the existing `GET /api/v1/market-data/prices/{symbol}/history` endpoint, ensuring the frontend requests `interval="1d"` or `"1w"`.

## Risks / Trade-offs

- **Risk:** Upstream Market Data Hub rate limits or unavailability.
  - *Mitigation:* The existing proxy endpoint already falls back to cached data if the upstream request fails. We will ensure the UI gracefully handles scenarios where no data is available (e.g., showing a placeholder or just the TradingView link).
- **Risk:** Unbounded growth of the `OhlcPrice` table due to caching many indices.
  - *Mitigation:* Daily and weekly candles consume very little storage compared to minute data. The storage impact will be negligible.
- **Risk:** Seeding defaults for existing users.
  - *Mitigation:* We will implement a data migration or an application-level seeding mechanism (similar to how playbooks/tags are seeded) to populate defaults for existing users upon login or application startup.

## Migration Plan

1. **Database Migration:** Create the Alembic revision for the `market_index_definitions` table and the `market_index_id` column on `daily_checkins`.
2. **Backend API:** Implement the CRUD endpoints and update the check-in schemas. Add the seeding logic.
3. **Frontend UI:** 
    - Implement the Market Indexes settings page.
    - Update the Check-in Form to include the index selector.
    - Implement the embedded chart in the Check-in details view, connecting it to the market data proxy endpoint.
4. **Testing:** Update E2E tests to verify index selection and chart rendering.

## Open Questions

- Should we seed default indices via an Alembic data migration, or via application logic when a user is created/logs in (similar to `MarketPhaseDefinition`)? *Recommendation:* Application logic is preferred for per-user data to ensure newly registered users automatically get the defaults.

---

#########################
# openspec/changes/checkin-market-index/proposal.md
#########################

## Why

The daily check-in currently lacks an explicit association with a broader market index (e.g., S&P 500, NASDAQ, DAX). Adding an index reference, its TradingView link, and an embedded OHLC chart helps provide crucial macro market context for the trading day directly within the check-in view, allowing traders to better correlate their performance and mood with overall market movements.

## What Changes

- Add a new settings section to manage a list of Market Indexes (e.g., Symbol, Name, TradingView link), seeded with standard US and EU indexes.
- Update the daily check-in form to include a dropdown field for selecting an associated Market Index.
- Display a TradingView link for the selected index in the check-in details.
- Embed a chart (daily or weekly candles) of the selected index within the check-in view, similar to the trade details view.
- Implement caching for the index's candlestick data to prevent redundant API calls and optimize page load times.

## Capabilities

### New Capabilities
- `market-indexes`: Management of configurable market indexes (symbol, name, TradingView link) scoped to the user, including a default seed of standard indexes.
- `checkin-market-context`: Fetching, caching, and displaying embedded OHLC charts (daily/weekly) and TradingView links for a selected market index within a check-in.

### Modified Capabilities
- `daily-checkins`: Update the daily check-in data model, API, and UI to support associating a check-in with a specific market index.

## Impact

- **Database**: New table for `market_index_definitions` and a new foreign key column on `daily_checkins` linking to the index.
- **Backend API**: New CRUD endpoints for market indexes and updates to the check-ins payload/responses. New endpoint for fetching cached index OHLC data.
- **Frontend UI**: Updates to the Settings page (new Market Indexes section), Check-in Form (new dropdown), and Check-in View/Timeline (embedded chart and TradingView link).
- **External APIs**: Calls to the market data provider for the index OHLC data, requiring caching logic to minimize external requests.

---

#########################
# openspec/changes/checkin-market-index/specs/checkin-market-context/spec.md
#########################

## ADDED Requirements

### Requirement: Display OHLC chart for selected index
The system MUST display an OHLC candlestick chart for the market index associated with a check-in, using the existing market data proxy endpoint.

#### Scenario: Viewing a check-in with an associated index
- **WHEN** the user views a check-in that has a `market_index_id`
- **THEN** the system fetches the cached daily/weekly OHLC data for that index's symbol and renders a candlestick chart

#### Scenario: Fallback when market data is unavailable
- **WHEN** the system attempts to fetch OHLC data but the upstream hub and local cache both fail
- **THEN** the UI displays a graceful fallback message indicating chart data is unavailable, while still showing the TradingView link

### Requirement: Display TradingView link
The system MUST provide a clickable TradingView link for the associated market index within the check-in view.

#### Scenario: User clicks the TradingView link
- **WHEN** the user views a check-in with an associated index and clicks the "View on TradingView" link
- **THEN** the TradingView URL defined for that index opens in a new browser tab

---

#########################
# openspec/changes/checkin-market-index/specs/daily-checkins/spec.md
#########################

## MODIFIED Requirements

### Requirement: User can create a daily check-in
The system MUST allow users to create a daily check-in that captures pre/post-market sentiment, playbook adherence, custom metrics, and optionally an associated market index.

#### Scenario: User creates a check-in with a market index
- **WHEN** the user submits a check-in form with a selected `market_index_id`
- **THEN** the system validates that the ID belongs to one of the user's active market index definitions and saves the check-in

#### Scenario: User creates a check-in without a market index
- **WHEN** the user submits a check-in form with no market index selected (`market_index_id` is null)
- **THEN** the system saves the check-in successfully without any index association

### Requirement: User can update a daily check-in
The system MUST allow users to update an existing daily check-in, including changing or removing the associated market index.

#### Scenario: User associates a market index to an existing check-in
- **WHEN** the user edits a check-in and selects a `market_index_id`
- **THEN** the system updates the check-in and returns the updated record including the nested `market_index` object

#### Scenario: User removes the market index from a check-in
- **WHEN** the user edits a check-in and deselects the market index (setting `market_index_id` to null)
- **THEN** the system removes the association and updates the record

---

#########################
# openspec/changes/checkin-market-index/specs/market-indexes/spec.md
#########################

## ADDED Requirements

### Requirement: User can manage market index definitions
The system MUST allow users to create, read, update, and delete market index definitions scoped to their account. A market index consists of a unique symbol, a display name, and a TradingView URL.

#### Scenario: User creates a new market index
- **WHEN** the user submits a valid market index payload (symbol, name, tv_url)
- **THEN** the system saves the index and returns it with a generated UUID

#### Scenario: User views their market indexes
- **WHEN** the user requests their market indexes
- **THEN** the system returns a list of all active market index definitions belonging to the user

#### Scenario: User updates an existing market index
- **WHEN** the user submits updated fields for an existing index they own
- **THEN** the system updates the record and returns the modified index

#### Scenario: User deletes a market index
- **WHEN** the user requests to delete an index they own
- **THEN** the system marks it as inactive or deletes it and returns a success response

### Requirement: System seeds default market indexes
The system MUST automatically seed a set of default market indexes (e.g., SPX, NDX, DAX) for a user if none exist.

#### Scenario: Seeding defaults for a new user
- **WHEN** a user logs in and has no market indexes defined
- **THEN** the system inserts the default US and EU index definitions for that user

---

#########################
# openspec/changes/checkin-market-index/tasks.md
#########################

## 1. Database & Backend Models

- [ ] 1.1 Create Alembic migration for `market_index_definitions` table and `daily_checkins.market_index_id` column.
- [ ] 1.2 Implement the `MarketIndexDefinition` SQLAlchemy model.
- [ ] 1.3 Update the `DailyCheckin` SQLAlchemy model to include the `market_index` relationship.
- [ ] 1.4 Create Pydantic schemas (create, update, response) for Market Index Definitions.
- [ ] 1.5 Update existing Check-in Pydantic schemas to include `market_index_id` and the nested `market_index` object.

## 2. Backend Services & Repositories

- [ ] 2.1 Implement `MarketIndexDefinitionRepository` with CRUD methods.
- [ ] 2.2 Implement `MarketIndexDefinitionService` containing business logic and default seeding logic.
- [ ] 2.3 Ensure default indices are seeded automatically for users (e.g., during login/creation).
- [ ] 2.4 Update `DailyCheckinRepository` and Service to handle the new relationship (e.g., `joinedload` on queries).

## 3. Backend API Endpoints

- [ ] 3.1 Create router and endpoints for `GET/POST/PUT/DELETE /api/v1/market-indexes`.
- [ ] 3.2 Verify existing `POST/PUT /api/v1/checkins` endpoints correctly handle the new `market_index_id` field.
- [ ] 3.3 Ensure the existing market data proxy `/api/v1/market-data/prices/{symbol}/history` handles interval `"1w"` properly (if any specific adjustments are needed).

## 4. Frontend API Client & State

- [ ] 4.1 Run OpenApiSync to regenerate the frontend TypeScript API client based on the updated backend schema.
- [ ] 4.2 Create React Query hooks for fetching, creating, updating, and deleting market indices.
- [ ] 4.3 Update the React Query mutations and invalidations for check-ins to handle the market index data.

## 5. Frontend UI: Settings

- [ ] 5.1 Add a "Market Indexes" section to the Settings page.
- [ ] 5.2 Implement a list view for active market indexes.
- [ ] 5.3 Implement a modal/form to create and edit market index definitions (Symbol, Name, TradingView URL).
- [ ] 5.4 Add delete/deactivate functionality.

## 6. Frontend UI: Check-in Form & View

- [ ] 6.1 Update `CheckinForm.tsx` to include a dropdown/selector for the `market_index_id`.
- [ ] 6.2 Update `CheckinDetail.tsx` (or equivalent view component) to display the TradingView link.
- [ ] 6.3 Implement a new component (e.g., `MarketIndexChart.tsx`) to fetch OHLC data via the proxy and render the candlestick chart using Recharts.
- [ ] 6.4 Integrate `MarketIndexChart.tsx` into the check-in view, ensuring graceful fallbacks if data fails to load.

## 7. Testing & Review

- [ ] 7.1 Write backend unit tests for the Market Index repository, service, and API endpoints.
- [ ] 7.2 Run E2E Playwright tests to verify index selection and chart rendering.
- [ ] 7.3 Run full `safe-commit` checks (lint, format, typecheck).

---

