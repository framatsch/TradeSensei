# checkin-global-settings Specification

## Purpose
TBD - created by archiving change checkin-global-settings-tab. Update Purpose after archive.
## Requirements
### Requirement: Check-in Tab in Global Settings
The system SHALL provide a dedicated "Check-in" tab within the global settings module.

#### Scenario: User navigates to Global Settings
- **WHEN** the user opens the system settings
- **THEN** a "Check-in" tab is visible alongside Profile, Portfolios, Broker, and Security
- **AND WHEN** the user clicks on the "Check-in" tab
- **THEN** the configuration view for Market Phases and Custom Metrics is displayed

### Requirement: Market Phases Management (MarketPhaseDefinition)
The system SHALL allow users to create, read (list), and update the state of Market Phases. The `name` field MUST be immutable after creation. DELETE is intentionally excluded — deactivation via `is_active=false` preserves historical check-in references. PATCH is limited to `label`, `color_hex`, and `is_active`.

#### Scenario: Creating a new Market Phase
- **WHEN** the user clicks "+ Neue Phase" and enters a valid name, label, and hex color
- **THEN** a new Market Phase is created and added to the list

#### Scenario: Editing an existing Market Phase
- **WHEN** the user edits the label or color of an existing Market Phase
- **THEN** the changes are immediately validated and saved via the backend PATCH endpoint
- **AND** the `name` (Key) field remains read-only

#### Scenario: Mockup verification for Market Phases
- **WHEN** the Market Phases table is rendered
- **THEN** it MUST match the following structure and UI components:
  ```text
  MARKT-PHASEN (MarketPhaseDefinition)
  [ + Neue Phase ]
  Key (Immutable) | Label (Anzeige)  | Farbe     | Status
  ----------------+------------------+-----------+--------------
  bullish         | [ Bullish      ] | [#22c55e] | [ Aktiv  ▼ ]
  bearish         | [ Bearish      ] | [#ef4444] | [ Aktiv  ▼ ]
  sideways        | [ Sideways     ] | [#f59e0b] | [ Inaktiv▼ ]
  ```

### Requirement: Custom Metrics Management (CheckinFieldDefinition)
The system SHALL allow users to create, read (list), and update the is_active state of Custom Metrics. The `field_name` and `field_type` MUST be immutable after creation. DELETE is intentionally excluded — `field_name` references stored JSONB keys in `DailyCheckin.custom_metrics` and removing a definition would orphan historical data. Deactivation via `is_active=false` is the correct mechanism. PATCH is limited to `is_active`.

#### Scenario: Creating a new Custom Metric
- **WHEN** the user clicks "+ Neue Metrik" and specifies a key and type (Integer/Boolean)
- **THEN** a new metric is created and displayed in the list with its type shown as a Badge

#### Scenario: Deactivating a Custom Metric
- **WHEN** the user changes the status of a Custom Metric from Active to Inactive
- **THEN** a warning modal/dialog MUST appear stating that historical data will remain visible but no new entries will be possible
- **AND WHEN** the user confirms
- **THEN** the metric status is updated to Inactive via the backend PATCH endpoint

#### Scenario: Mockup verification for Custom Metrics
- **WHEN** the Custom Metrics table is rendered
- **THEN** it MUST match the following structure and UI components:
  ```text
  EIGENE METRIKEN (CheckinFieldDefinition)
  [ + Neue Metrik ]
  Key (Immutable) | Typ (Immutable)  | Status
  ----------------+------------------+--------------
  mood-level      | Integer          | [ Aktiv  ▼ ]
  focus           | Integer          | [ Aktiv  ▼ ]
  rule-followed   | Boolean          | [ Aktiv  ▼ ]
  ```

### Requirement: UI Standards and Testing
All components MUST adhere to the project's UI standards, utilizing Tailwind CSS and React components consistently. Automated tests MUST be provided to verify component rendering and state transitions.

**Backend API Dependencies**: This tab relies on the following backend endpoints (see Spec 5 — Daily Check-in System):
- `GET /api/v1/market-phases` — fetch market phase definitions (with optional `?is_active=` filter)
- `POST /api/v1/market-phases` — create a new market phase definition
- `PATCH /api/v1/market-phases/{id}` — update label, color_hex, or is_active (name immutable)
- `GET /api/v1/checkin-fields` — fetch check-in field definitions (with optional `?is_active=` filter)
- `POST /api/v1/checkin-fields` — create a new field definition
- `PATCH /api/v1/checkin-fields/{id}` — update is_active only (field_name and field_type immutable)
No DELETE endpoint exists for either entity — deactivation is the correct mechanism.

#### Scenario: UI component rendering test
- **WHEN** the Check-in settings tab is rendered in a test environment
- **THEN** it MUST successfully render all structural elements including the tabs, Market Phases table, and Custom Metrics table without errors
- **AND** it MUST trigger the warning dialog correctly when deactivating a metric

