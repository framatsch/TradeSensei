## Context

The system currently allows filtering check-ins via query parameters in the URL (`regime`, `from_date`, `to_date`). However, there is no UI filter bar to easily adjust these, and no way to save them. The Reporting Hub already has a `WorkspaceFilterBar` and `SavedDashboardView`/`SavedTradeFilter` models. We need a similar but distinct solution for Check-ins, since Check-ins are global to the user, not tied to a specific portfolio.

## Goals / Non-Goals

**Goals:**
- Provide a `CheckinFilterBar` UI component.
- Extend `list_checkins` backend API to support filtering by `target_indices` (list of UUIDs) and `has_media` (boolean).
- Introduce a new database model `SavedCheckinFilter` to store these presets per user.
- Provide CRUD endpoints for `SavedCheckinFilter`.

**Non-Goals:**
- Unifying Check-ins into the Portfolio data model. Check-ins remain global/user-level.

## Decisions

1. **SavedCheckinFilter Model**
   - Rationale: Since check-ins don't belong to a portfolio, we cannot reuse `SavedDashboardView` which requires a `portfolio_id`. We need a new table `saved_checkin_filters` with columns: `id`, `user_id`, `name`, `is_default`, and `filter_config` (JSONB).
2. **Backend Filtering Extension**
   - Rationale: To filter by `target_indices`, the query needs to join or use `EXISTS` against the `checkin_target_index_link` table.
   - For `has_media`, we can check if `screenshot_keys` is not null and length > 0.
3. **Frontend Architecture**
   - Rationale: We will create a `CheckinFilterContext` (similar to `WorkspaceFilterContext`) to manage the filter state and the currently active saved view. The `CheckinsPageClient` will consume this context.

## Risks / Trade-offs

- **Risk:** Complexity of the API query increasing due to `target_indices` filtering.
  - **Mitigation:** Use `selectinload` for indices and an `EXISTS` subquery or `any()` array operations if possible, to keep the query performant.
- **Risk:** Filter state sync between URL query parameters and the `CheckinFilterContext`.
  - **Mitigation:** We can either drop the URL syncing and rely purely on the context + saved views, OR keep them synced. Given `useCheckinParams` already syncs to URL, we will continue syncing the active filter configuration to the URL so that the page remains deep-linkable.
