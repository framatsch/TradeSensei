## 1. Backend Core & Database

- [x] 1.1 Create `SavedCheckinFilter` SQLAlchemy model
- [x] 1.2 Generate and apply Alembic migration for the new model
- [x] 1.3 Create Pydantic schemas for `SavedCheckinFilter` (Create, Read, Update)
- [x] 1.4 Update `list_checkins` in `CheckinsApi` to accept `target_indices` and `has_media` params
- [x] 1.5 Implement filtering logic for `target_indices` and `has_media` in `DailyCheckinService.list_checkins`

## 2. Backend API Endpoints

- [x] 2.1 Add GET `/api/v1/checkins/filters` to list saved checkin filters
- [x] 2.2 Add POST `/api/v1/checkins/filters` to create a new saved checkin filter
- [x] 2.3 Add PUT `/api/v1/checkins/filters/{id}` to update a saved checkin filter
- [x] 2.4 Add DELETE `/api/v1/checkins/filters/{id}` to delete a saved checkin filter

## 3. Frontend Data Layer & Hooks

- [x] 3.1 Regenerate OpenAPI client in frontend (`npm run openapi-ts` or similar)
- [x] 3.2 Update `useCheckinParams` hook to support `target_indices` and `has_media`
- [x] 3.3 Create `useCheckinFilters` hook (fetching, creating, updating, deleting saved views)
- [x] 3.4 Create `CheckinFilterContext` to manage active view and temporary filter state

## 4. Frontend UI Components

- [x] 4.1 Create `CheckinFilterBar` component with Dropdowns and DatePickers
- [x] 4.2 Add "Save View" dialog to the `CheckinFilterBar`
- [x] 4.3 Integrate `CheckinFilterBar` into `CheckinsPageClient`
- [x] 4.4 Verify filtering works correctly on Timeline and Gallery views
