## Context

The Check-in configuration needs to be integrated into the central settings module of the frontend application. This includes CRUD operations for `MarketPhaseDefinition` and `CheckinFieldDefinition`. Separating these definitions from the daily capture ensures consistency and avoids psychological errors in trading.

## Goals / Non-Goals

**Goals:**
- Implement a dedicated "Check-in" tab in the global settings.
- Create CRUD interfaces for market phases (colors, labels) and custom metrics (booleans, integers).
- Support live state updates with validations (e.g. key/type immutability after creation).
- Integrate warning for metric deactivation regarding historical data.

**Non-Goals:**
- Changes to the Check-in Hub's standard views (Calendar, Model Book, Journal) are out of scope for this specific settings task.
- Backend implementation of the PATCH/CRU endpoints is handled by Spec 5 (Daily Check-in System) — see `daily-checkin-system/specs/checkin-field-definitions/spec.md`, `daily-checkin-system/specs/market-phase-definitions/spec.md`, and the routes `/api/v1/checkin-fields` and `/api/v1/market-phases`. This tab is a consumer of those existing API contracts.

## Decisions

- **State Management:** Use TanStack Query (React Query) for data fetching and optimistic updates, combined with controlled React components for the form inputs.
- **Validation:** Validation will happen on the client-side (e.g., making the `name` and `field_type` fields read-only after creation) before sending the PATCH request.
- **Color Picker:** Use a standard, lightweight color picker component compatible with Tailwind CSS to manage the `color_hex` for MarketPhaseDefinitions.
- **Warnings:** Use a modal/dialog component for the warning when deactivating a metric to ensure explicit user consent.

## Risks / Trade-offs

- **Data Inconsistency on PATCH failure:** Optimistic updates might lead to a brief mismatch if the backend rejects the PATCH request.
  - *Mitigation:* Handle mutations with `onSettled` or `onError` callbacks to revert the local cache to the previous state.
- **UX Complexity:** The settings module might become cluttered.
  - *Mitigation:* Keep the layout clean with tabular data representations as described in the mockups.