## 1. Backend Updates

- [x] 1.1 Add `chart_intervals` field to `UserSettingsRead` and `UserSettingsUpdate` schemas in `backend/app/schemas/user.py`. It should be `list[Literal["1h", "4h", "1d"]]` with default `["1h", "4h", "1d"]`.
- [x] 1.2 Validate that the user provides at least one interval in `UserSettingsUpdate`.
- [x] 1.3 Ensure `chart_intervals` is handled properly when updating and returning user settings in the API route.

## 2. Frontend Settings API & Types

- [ ] 2.1 Run `npm run openapi-ts` in the frontend directory (if needed) or simply update `UserSettings` interface in `frontend/lib/types.ts` manually to include `chart_intervals: Array<"1h" | "4h" | "1d">`.
- [ ] 2.2 Update `DEFAULT_SETTINGS` in `frontend/hooks/useSettings.ts` to include `chart_intervals: ["1h", "4h", "1d"]`.

## 3. Settings UI

- [ ] 3.1 In `frontend/components/settings/GeneralSettings.tsx` (or `FeaturesSettings`), add a UI section for "Chart Timeframes".
- [ ] 3.2 Add multi-select checkboxes for "1h", "4h", and "1d".
- [ ] 3.3 Hook up the checkboxes to `useUpdateSettings` mutation. Ensure at least one interval (e.g., "1d") is always selected.

## 4. Chart Component Updates

- [ ] 4.1 Update `smartDefaultInterval` in `frontend/components/charts/TradeChart.tsx` to accept the allowed `Interval[]` array. It should fallback to the next available interval if "1h" or "4h" is excluded.
- [ ] 4.2 Update `TradeChart.tsx` to read `chart_intervals` from `useSettings()` (or pass it via props if needed, but since it's a client component, `useSettings` works).
- [ ] 4.3 Replace the hardcoded `["1h", "4h", "1d"]` array in `TradeChart.tsx` with the user's `chart_intervals` array when rendering the interval selection buttons.
