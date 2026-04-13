/**
 * Reports Navigation Spec — covers clicking bars/rows in performance reports
 * to navigate to the Trades page with the correct URL filters.
 *
 * Tests:
 *  - Hourly report: "View Report" navigates to trades?hour_of_day=N
 *  - Weekday report: "View Report" navigates to trades?day_of_week=N
 *  - Monthly report: "View Report" navigates to trades with opened_at range
 *  - Yearly report:  "View Report" navigates to trades with full-year range
 *  - Filter chip is visible after navigation (hour_of_day / day_of_week)
 *
 * All tests run as the seeded E2E user (10 trades seeded by global-setup).
 */

import { test, expect } from '@playwright/test';

test.describe('Performance Reports — Navigation', () => {
  test('TC-R001 Hourly report row click navigates to trades with hour_of_day filter', async ({
    page,
  }) => {
    await page.goto('/dashboard/analytics?tab=time');
    // Ensure the page has loaded and the layout is ready
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'Hourly' }).click();
    await page.waitForLoadState('networkidle');

    // Wait for the performance table to render (at least one row with data)
    // We look for a row that has a numeric value in one of its cells.
    const firstRow = page.locator('tbody tr').filter({ hasText: /[1-9]/ }).first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();


    // Should navigate to trades page with hour_of_day param
    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    await expect(page).toHaveURL(/hour_of_day=\d+/);
  });

  test('TC-R002 Weekday report row click navigates to trades with day_of_week filter', async ({
    page,
  }) => {
    await page.goto('/dashboard/analytics?tab=time');
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: 'Weekday' }).click();
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();

    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    await expect(page).toHaveURL(/day_of_week=\d+/);
  });

  test('TC-R003 Monthly report row click navigates to trades with date range', async ({
    page,
  }) => {
    await page.goto('/dashboard/analytics?tab=time');
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: 'Monthly' }).click();
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();

    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    // Monthly navigation sets a date range
    await expect(page).toHaveURL(/opened_at_from=/);
    await expect(page).toHaveURL(/opened_at_to=/);
  });

  test('TC-R004 Yearly report row click navigates to trades with full-year date range', async ({
    page,
  }) => {
    await page.goto('/dashboard/analytics?tab=time');
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: 'Yearly' }).click();
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();

    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    // Yearly navigation sets full-year date range
    await expect(page).toHaveURL(/opened_at_from=/);
    await expect(page).toHaveURL(/opened_at_to=/);
  });

  test('TC-R005 after Hourly navigation, one filter is active in Trades', async ({ page }) => {
    await page.goto('/dashboard/analytics?tab=time');
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: 'Hourly' }).click();
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();

    await expect(page).toHaveURL(/hour_of_day=\d+/, { timeout: 8_000 });

    // hour_of_day counts as 1 active filter
    await expect(page.getByRole('button', { name: 'Filters' })).toContainText(/[1-9]/);
  });

  test('TC-R006 after Weekday navigation, one filter is active in Trades', async ({ page }) => {
    await page.goto('/dashboard/analytics?tab=time');
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: 'Weekday' }).click();
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();

    await expect(page).toHaveURL(/day_of_week=\d+/, { timeout: 8_000 });

    await expect(page.getByRole('button', { name: 'Filters' })).toContainText(/[1-9]/);
  });

  test('TC-R007 Calendar report day click navigates to trades with closed_at filters', async ({ page }) => {
    await page.goto('/dashboard/reports/calendar');
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');

    // Wait for the calendar to render and find a day cell with trades
    // Looking for the specific text "trades" which is only rendered on days with activity
    const dayWithTrades = page.locator('div.cursor-pointer', { hasText: /trades/i }).first();
    await expect(dayWithTrades).toBeVisible({ timeout: 15_000 });

    await dayWithTrades.click();

    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    await expect(page).toHaveURL(/closed_at_from=/);
    await expect(page).toHaveURL(/closed_at_to=/);

    // Verify filter chip is visible
    await expect(page.getByRole('button', { name: 'Filters' })).toContainText('2');
  });
});
