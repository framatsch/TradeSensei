## 1. Setup and Scaffolding

- [x] 1.1 Create the basic component structure for the "Check-in" tab within the global settings module.
- [x] 1.2 Define the TypeScript interfaces/types for `MarketPhaseDefinition` and `CheckinFieldDefinition` matching the backend schema.
- [x] 1.3 Setup the React Query hooks (queries and mutations) for fetching and updating these entities.

## 2. Market Phases Component

- [x] 2.1 Implement the data table for `MarketPhaseDefinition` including the "Key", "Label", "Farbe", and "Status" columns.
- [x] 2.2 Add the "+ Neue Phase" button and implement the creation logic.
- [x] 2.3 Implement the inline editing for "Label" and "Farbe" (using a color picker component) with optimistic updates via PATCH.
- [x] 2.4 Ensure the "Key" column is rendered as immutable (read-only text) for existing entries.
- [x] 2.5 Implement the "Status" toggle (Aktiv/Inaktiv).

## 3. Custom Metrics Component

- [x] 3.1 Implement the data table for `CheckinFieldDefinition` including the "Key", "Typ", and "Status" columns.
- [x] 3.2 Render the "Typ" field using appropriate Badge components (e.g., Integer, Boolean).
- [x] 3.3 Add the "+ Neue Metrik" button and implement the creation logic.
- [x] 3.4 Ensure the "Key" and "Typ" columns are rendered as immutable for existing entries.
- [x] 3.5 Implement the warning modal component that appears when attempting to change a metric's status to Inaktiv.
- [x] 3.6 Wire the "Status" toggle to the warning modal, and upon confirmation, execute the PATCH request.

## 4. UI Polish and Testing

- [x] 4.1 Review the component styling against the mockups and project UI standards (Tailwind classes).
- [x] 4.2 Write component tests (e.g., using React Testing Library) to verify rendering of both tables and the tabs.
- [x] 4.3 Write tests to verify the read-only behavior of the immutable fields (`name`, `field_name`, `field_type`).
- [x] 4.4 Write tests to ensure the warning modal is triggered correctly when deactivating a custom metric.