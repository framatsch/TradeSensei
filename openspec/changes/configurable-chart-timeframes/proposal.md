## Why

Users who use market data providers that only supply End of Day (EOD) data (daily or higher resolution) currently see chart interval options like "1h" and "4h" in the Trade Detail view. Clicking these unsupported intervals results in empty charts or errors. Making the available chart intervals configurable allows users to tailor the UI to their specific market data provider's capabilities, improving usability and avoiding confusion.

## What Changes

- Add a new user setting `chart_intervals` to store the user's preferred or provider-supported timeframes for charts.
- Update the Settings UI to allow users to select which intervals should be visible in the chart component.
- Update `TradeChart.tsx` to read the available intervals from user settings rather than hardcoding `["1h", "4h", "1d"]`.
- Update the default interval selection logic in `TradeChart.tsx` (`smartDefaultInterval`) to respect the user's configured intervals (e.g. fallback to "1d" if "1h" is not available).

## Capabilities

### New Capabilities
- `chart-intervals-setting`: Add configuration for chart intervals (timeframes) in the user settings UI, backend models, and schemas.

### Modified Capabilities

## Impact

- **Backend**: Adds `chart_intervals` to `UserSettingsRead` and `UserSettingsUpdate` Pydantic schemas in `user.py`, with default `["1h", "4h", "1d"]`.
- **Frontend Types/Hooks**: Updates `UserSettings` in `types.ts` and `DEFAULT_SETTINGS` in `useSettings.ts`. 
- **Frontend Settings UI**: Adds a new section or multi-select toggle in the Settings page (under General or Features) to configure chart intervals.
- **Frontend Components**: `TradeChart.tsx` dynamically renders interval buttons based on the user setting instead of the hardcoded array.
