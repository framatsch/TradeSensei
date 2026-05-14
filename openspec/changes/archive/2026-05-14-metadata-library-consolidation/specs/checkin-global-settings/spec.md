## REMOVED Requirements

### Requirement: Check-in Tab in Global Settings
**Reason**: The Market Phases and Custom Metrics management sections are being consolidated into the Metadata Library (Library > Tags for taxonomies, Library > Metrics for annotation definitions). The Settings > Check-in page is reduced to technical configuration only.
**Migration**: Users manage qualitative labels via Library > Tags (taxonomies) and quantitative metrics via Library > Metrics (annotation definitions). Existing `market_phase_definitions` and `checkin_field_definitions` backend endpoints remain intact; only the UI management sections are removed from Settings.

### Requirement: Market Phases Management (MarketPhaseDefinition)
**Reason**: Market Phases (qualitative labels for check-ins) are superseded by scoped taxonomies (`scope=checkins` or `scope=both`). The Market Phases UI section is removed from Settings.
**Migration**: No data migration in this change. The Check-in form continues to read `market_phase_definitions` until a dedicated migration change copies data to `taxonomies` and updates the Check-in form. Backend endpoints are preserved.

### Requirement: Custom Metrics Management (CheckinFieldDefinition)
**Reason**: Custom Metrics (quantitative variables for check-ins) are superseded by scoped annotation definitions (`scope=checkins` or `scope=both`). The Custom Metrics UI section is removed from Settings.
**Migration**: Same as Market Phases above — backend endpoints preserved, UI removed.

## ADDED Requirements

### Requirement: Settings Check-in page shows only Market Indexes
The system SHALL render only the Market Indexes management section in Settings > Check-in. Market Phases and Custom Metrics sections SHALL NOT be visible.

#### Scenario: Check-in settings shows Market Indexes only
- **WHEN** the user navigates to Settings > Check-in
- **THEN** only the Market Indexes table and its controls are rendered
- **AND** no Market Phases section is present
- **AND** no Custom Metrics section is present
