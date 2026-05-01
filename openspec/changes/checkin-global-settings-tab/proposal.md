## Why

Integration of the Check-in configuration into the central settings module of the application. Separating definition (settings) from daily capture (Hub) ensures the necessary systematic approach to avoid psychological errors. Static typing of metrics also prevents inconsistencies in subsequent performance analysis.

## What Changes

- Dedicated "Check-in" tab within the global settings.
- Section "Marktphasen" (Market Phases): CRU interface for `MarketPhaseDefinition` (Create, Read, Update — no Delete; deactivation via `is_active`).
- Section "Metriken" (Metrics): CRU interface for `CheckinFieldDefinition` (Create, Read, Update — no Delete; deactivation via `is_active`).
- Live state management: Changes are immediately validated and saved via the backend's PATCH endpoints.
- UX additions: Warning when deactivating fields that historical data will remain but no new entries will be possible.

## Capabilities

### New Capabilities
- `checkin-global-settings`: Configuration of market phases and metrics in a global settings tab.

### Modified Capabilities
- 

## Impact

- Frontend: Global settings module (UI components, state management, API integration for PATCH endpoints).
- Backend: Expects corresponding CRUD/PATCH endpoints for `MarketPhaseDefinition` and `CheckinFieldDefinition`.