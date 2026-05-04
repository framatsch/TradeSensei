## 1. Database & Backend Models

- [x] 1.1 Create Alembic migration for `market_index_definitions` table and `checkin_market_indices` junction table.
- [x] 1.2 Implement the `MarketIndexDefinition` SQLAlchemy model.
- [x] 1.3 Update the `DailyCheckin` SQLAlchemy model to include a many-to-many `target_indices` relationship.
- [x] 1.4 Create Pydantic schemas (create, update, response) for Market Index Definitions.
- [x] 1.5 Update Check-in Pydantic payload schemas to accept `target_index_ids: list[UUID]`.

## 2. Backend Services & Repositories

- [x] 2.1 Implement `MarketIndexDefinitionRepository` with CRUD methods.
- [x] 2.2 Implement `MarketIndexDefinitionService` containing business logic and default seeding logic.
- [x] 2.3 Update `DailyCheckinRepository` and Service to synchronize the `checkin_market_indices` junction table on create/update.
- [x] 2.4 Ensure default indices are seeded automatically for users upon account creation or login.

## 3. Backend API Endpoints

- [x] 3.1 Create router and endpoints for `GET/POST/PUT/DELETE /api/v1/market-indexes`.
- [x] 3.2 Verify existing `POST/PUT /api/v1/checkins` endpoints correctly handle the new `target_index_ids` payload array.

## 4. Frontend API Client & State

- [x] 4.1 Run OpenApiSync to regenerate the frontend TypeScript API client based on the updated backend schema.
- [x] 4.2 Create React Query hooks for fetching and mutating market indices.
- [x] 4.3 Update React Query mutations for check-ins to pass `target_index_ids`.

## 5. Frontend UI: Settings

- [x] 5.1 Add a "Market Indexes" section to the Settings page.
- [x] 5.2 Implement a list view for active market indices.
- [x] 5.3 Implement a modal/form to create and edit market index definitions (Symbol, Name, TradingView URL).

## 6. Frontend UI: Check-in Form & View

- [x] 6.1 Update `CheckinForm.tsx` to replace the single dropdown with a Multi-Select component (or selectable chips) for `target_index_ids`.
- [x] 6.2 Update the Timeline View to render selected indices as neutral-colored badges next to the date heading.
- [x] 6.3 Update the check-in views to render the TradingView URLs purely as static external href links (e.g., an icon row: `[↗ SPX]`).
- [x] 6.4 Verify the UI enforces static S3 screenshot uploads for visual chart data (ensure existing upload mechanism works well with the new layout).

## 7. Testing & Review

- [x] 7.1 Write backend unit tests verifying the many-to-many junction table logic and CRUD operations.
- [ ] 7.2 Run full `safe-commit` checks (lint, format, typecheck).
