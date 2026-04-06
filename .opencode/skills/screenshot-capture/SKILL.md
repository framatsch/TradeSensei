# ---
# name: screenshot-capture
# description: Capture screenshots of frontend pages with Playwright (handles auth and saving)
# license: MIT
# compatibility: opencode
# metadata:
#   toolchain: playwright, python
# ---

# Skill: Screenshot Capture

This skill allows you to capture screenshots of specific dashboard pages or all pages. It handles authentication and saves screenshots to a designated directory.

## Workflow

1. **Information Gathering**: Ask the user for the base URL (defaults to `http://localhost:3000`), credentials (username/password), and which pages to capture.
2. **Setup**: Ensure the target directory exists.
3. **Execution**:
    - Launch Playwright.
    - Navigate to the login page and perform login.
    - Wait for the dashboard to load.
    - Iterate through the selected pages:
        - Navigate to the page.
        - Wait for content/network idle.
        - Take a screenshot.
        - Save with a descriptive name.
4. **Cleanup**: Close the browser.
5. **Report**: Show the user where the screenshots are saved.

## Usage

Run the tool script:
```bash
python3 tools/screenshot_capture.py
```

## Available Pages

- Dashboard Overview
- Trades
- Playbooks
- Reports (Overview, Monthly, Yearly, Calendar, etc.)
- Import
- Settings
- Accounts
- Connections
- Tags
- Tax
- Help
- Login Page (unauthenticated)
