import re

with open('frontend/tests/specs/reports.spec.ts', 'r') as f:
    content = f.read()

# Replace View Report locating and clicking with row clicking
content = content.replace(
    "const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();\n    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });\n\n    // Click the first \"View Report\" button\n    await firstViewReport.click();",
    "const firstRow = page.locator('tbody tr').first();\n    await expect(firstRow).toBeVisible({ timeout: 15_000 });\n    await firstRow.click();"
)

content = content.replace(
    "const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();\n    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });\n\n    await firstViewReport.click();",
    "const firstRow = page.locator('tbody tr').first();\n    await expect(firstRow).toBeVisible({ timeout: 15_000 });\n    await firstRow.click();"
)

content = content.replace(
    "const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();\n    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });\n    await firstViewReport.click();",
    "const firstRow = page.locator('tbody tr').first();\n    await expect(firstRow).toBeVisible({ timeout: 15_000 });\n    await firstRow.click();"
)

# For Weekday:
content = content.replace(
    """  test('TC-R002 Weekday report "View Report" navigates to trades with day_of_week filter', async ({\n    page,\n  }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.waitForLoadState('networkidle');""",
    """  test('TC-R002 Weekday report row click navigates to trades with day_of_week filter', async ({\n    page,\n  }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.getByRole('button', { name: 'Weekday' }).click();\n    await page.waitForLoadState('networkidle');"""
)

# For Monthly:
content = content.replace(
    """  test('TC-R003 Monthly report "View Report" navigates to trades with date range', async ({\n    page,\n  }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.waitForLoadState('networkidle');""",
    """  test('TC-R003 Monthly report row click navigates to trades with date range', async ({\n    page,\n  }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.getByRole('button', { name: 'Monthly' }).click();\n    await page.waitForLoadState('networkidle');"""
)

# For Yearly:
content = content.replace(
    """  test('TC-R004 Yearly report "View Report" navigates to trades with full-year date range', async ({\n    page,\n  }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.waitForLoadState('networkidle');""",
    """  test('TC-R004 Yearly report row click navigates to trades with full-year date range', async ({\n    page,\n  }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.getByRole('button', { name: 'Yearly' }).click();\n    await page.waitForLoadState('networkidle');"""
)

# For TC-R006 (Weekday again)
content = content.replace(
    """  test('TC-R006 after Weekday navigation, one filter is active in Trades', async ({ page }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.waitForLoadState('networkidle');""",
    """  test('TC-R006 after Weekday navigation, one filter is active in Trades', async ({ page }) => {\n    await page.goto('/dashboard/analytics?tab=time');\n    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });\n    await page.getByRole('button', { name: 'Weekday' }).click();\n    await page.waitForLoadState('networkidle');"""
)

# Replace remaining 'Hourly report "View Report"' title
content = content.replace('Hourly report "View Report"', 'Hourly report row click')

with open('frontend/tests/specs/reports.spec.ts', 'w') as f:
    f.write(content)

