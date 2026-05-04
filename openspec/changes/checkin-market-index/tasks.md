## 1. Database & Backend Models

- [ ] 1.1 Create Alembic migration for `market_index_definitions` table and `checkin_market_indices` junction table.
- [ ] 1.2 Implement the `MarketIndexDefinition` SQLAlchemy model.
- [ ] 1.3 Update the `DailyCheckin` SQLAlchemy model to include a many-to-many `target_indices` relationship.
- [ ] 1.4 Create Pydantic schemas (create, update, response) for Market Index Definitions.
- [ ] 1.5 Update Check-in Pydantic payload schemas to accept `target_index_ids: list[UUID]`.

## 2. Backend Services & Repositories

- [ ] 2.1 Implement `MarketIndexDefinitionRepository` with CRUD methods.
- [ ] 2.2 Implement `MarketIndexDefinitionService` containing business logic and default seeding logic.
- [ ] 2.3 Update `DailyCheckinRepository` and Service to synchronize the `checkin_market_indices` junction table on create/update.
- [ ] 2.4 Ensure default indices are seeded automatically for users upon account creation or login.

## 3. Backend API Endpoints

- [ ] 3.1 Create router and endpoints for `GET/POST/PUT/DELETE /api/v1/market-indexes`.
- [ ] 3.2 Verify existing `POST/PUT /api/v1/checkins` endpoints correctly handle the new `target_index_ids` payload array.

## 4. Frontend API Client & State

- [ ] 4.1 Run OpenApiSync to regenerate the frontend TypeScript API client based on the updated backend schema.
- [ ] 4.2 Create React Query hooks for fetching and mutating market indices.
- [ ] 4.3 Update React Query mutations for check-ins to pass `target_index_ids`.

## 5. Frontend UI: Settings

- [ ] 5.1 Add a "Market Indexes" section to the Settings page.
- [ ] 5.2 Implement a list view for active market indices.
- [ ] 5.3 Implement a modal/form to create and edit market index definitions (Symbol, Name, TradingView URL).

## 6. Frontend UI: Check-in Form & View

- [ ] 6.1 Update `CheckinForm.tsx` to replace the single dropdown with a Multi-Select component (or selectable chips) for `target_index_ids`.
- [ ] 6.2 Update the Timeline View to render selected indices as neutral-colored badges next to the date heading.
- [ ] 6.3 Update the check-in views to render the TradingView URLs purely as static external href links (e.g., an icon row: `[↗ SPX]`).
- [ ] 6.4 Verify the UI enforces static S3 screenshot uploads for visual chart data (ensure existing upload mechanism works well with the new layout).

## 7. Testing & Review

- [ ] 7.1 Write backend unit tests verifying the many-to-many junction table logic and CRUD operations.
- [ ] 7.2 Run E2E Playwright tests to verify index multi-selection and badge rendering.
- [ ] 7.3 Run full `safe-commit` checks (lint, format, typecheck).
