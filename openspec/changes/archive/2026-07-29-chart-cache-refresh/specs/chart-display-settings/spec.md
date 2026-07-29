## MODIFIED Requirements

### Requirement: Look & Feel tab in Settings
The Settings Hub SHALL provide a **Look & Feel** tab that lets a user read and update the chart
display defaults, and clear the chart candles cache for their account.
#### Scenario: Look & Feel tab renders current values
- **WHEN** the user opens the Look & Feel tab
- **THEN** the form shows the current `chart_candles_before`, `chart_candles_after`, and `chart_show_post_exit` values fetched from `GET /api/v1/users/me/settings`

#### Scenario: User updates candle counts
- **WHEN** the user changes the "Candles before entry" or "Candles after exit" input and saves
- **THEN** `PUT /api/v1/users/me/settings` is called with the updated values and a success toast is shown

#### Scenario: Candle count validation — positive integer required
- **WHEN** the user enters a value ≤ 0 or a non-integer in a candle count field
- **THEN** the form shows an inline error "Must be a positive whole number" and save is disabled

#### Scenario: User toggles post-exit candle visibility
- **WHEN** the user changes the "Show post-exit candles by default" toggle and saves
- **THEN** `PUT /api/v1/users/me/settings` is called with the updated boolean and the toggle reflects the saved state

#### Scenario: Save fails — network error
- **WHEN** the PUT request fails
- **THEN** an error toast is shown and the form values revert to the last saved state

#### Scenario: User clicks clear cache and confirms
- **WHEN** the user clicks the "Clear chart candles cache" button
- **THEN** a confirmation dialog ("Are you sure? - Yes/No" or similar) is shown
- **AND WHEN** the user selects "Yes"
- **THEN** `DELETE /api/v1/market-data/cache` is called, a success toast is shown, and the dialog is closed

#### Scenario: User clicks clear cache and cancels
- **WHEN** the user clicks the "Clear chart candles cache" button
- **THEN** a confirmation dialog is shown
- **AND WHEN** the user selects "No"
- **THEN** the dialog is closed and no API request is made

