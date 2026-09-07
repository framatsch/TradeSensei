## Context

The current unified import dialog (`ImportDateRange.tsx` and `ImportForm.tsx`, used for both Schwab and IBKR) uses a standard date picker and manual account selection. To speed up selection, we want to add predefined quick-select options for dates and automatically pre-fill the account if only one exists.

## Goals / Non-Goals

**Goals:**
- Provide a simple UI (dropdown or button group) to select predefined date ranges.
- Update the date picker's state automatically when a preset is chosen.
- Ensure statefulness so selected presets persist.

**Non-Goals:**
- Do not redesign the entire import dialog layout significantly (though we will remove obsolete visual elements).

## Decisions

- **UI Component**: We implemented a "Stateful Dropdown" (`<select>`) that acts as the primary driver for the date preset. 
- **Date Picker Visibility**: The `<input type="date">` is always visible next to the dropdown to give immediate visual feedback. Modifying the date picker manually automatically switches the dropdown to "Custom date...".
- **Visual Clutter Removal**: We removed the large visual timeline progress bar, replacing it with a minimal text string indicating the number of selected days and the broker API limit.
- **Backend Persistence**: We expanded the `FlexFromDatePreset` Literal in the backend (`backend/app/schemas/account.py`) to explicitly support `"7d"`, `"30d"`, `"mtd"`, etc. This allows the user's quick-select choice to be saved as an account default dynamically, rather than just resolving to a static custom date.
- **Account Auto-Selection Logic**: Inside `ImportForm.tsx`, a `useEffect` hook checks if exactly one active account exists (`activeAccounts.length === 1`), automatically selecting it if no account is currently selected.

## Risks / Trade-offs

- **Timezones**: Date calculation uses the local timezone of the user to match expectations for "today".
- **Backend Schema Evolution**: Expanding the Literal in Pydantic required frontend types to be updated, but since the database uses JSONB for settings, no Alembic migration was required.
