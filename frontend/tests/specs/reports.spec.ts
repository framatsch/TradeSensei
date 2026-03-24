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
  test('TC-R001 Hourly report "View Report" navigates to trades with hour_of_day filter', async ({
    page,
  }) => {
    await page.goto('/dashboard/reports/hourly');
    await page.waitForLoadState('networkidle');

    // Wait for the performance table to render (at least one "View Report" button)
    const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();
    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });

    // Click the first "View Report" button
    await firstViewReport.click();

    // Should navigate to trades page with hour_of_day param
    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    await expect(page).toHaveURL(/hour_of_day=\d+/);
  });

  test('TC-R002 Weekday report "View Report" navigates to trades with day_of_week filter', async ({
    page,
  }) => {
    await page.goto('/dashboard/reports/weekday');
    await page.waitForLoadState('networkidle');

    const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();
    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });

    await firstViewReport.click();

    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    await expect(page).toHaveURL(/day_of_week=\d+/);
  });

  test('TC-R003 Monthly report "View Report" navigates to trades with date range', async ({
    page,
  }) => {
    await page.goto('/dashboard/reports/monthly');
    await page.waitForLoadState('networkidle');

    const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();
    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });

    await firstViewReport.click();

    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    // Monthly navigation sets a date range
    await expect(page).toHaveURL(/opened_at_from=/);
    await expect(page).toHaveURL(/opened_at_to=/);
  });

  test('TC-R004 Yearly report "View Report" navigates to trades with full-year date range', async ({
    page,
  }) => {
    await page.goto('/dashboard/reports/yearly');
    await page.waitForLoadState('networkidle');

    const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();
    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });

    await firstViewReport.click();

    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    // Yearly navigation sets full-year date range
    await expect(page).toHaveURL(/opened_at_from=/);
    await expect(page).toHaveURL(/opened_at_to=/);
  });

  test('TC-R005 after Hourly navigation, one filter is active in Trades', async ({ page }) => {
    await page.goto('/dashboard/reports/hourly');
    await page.waitForLoadState('networkidle');

    const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();
    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });
    await firstViewReport.click();

    await expect(page).toHaveURL(/hour_of_day=\d+/, { timeout: 8_000 });

    await expect(page.getByRole('button', { name: 'Filters' })).toContainText('1');
  });

  test('TC-R006 after Weekday navigation, one filter is active in Trades', async ({ page }) => {
    await page.goto('/dashboard/reports/weekday');
    await page.waitForLoadState('networkidle');

    const firstViewReport = page.getByRole('button', { name: 'View Report' }).first();
    await expect(firstViewReport).toBeVisible({ timeout: 15_000 });
    await firstViewReport.click();

    await expect(page).toHaveURL(/day_of_week=\d+/, { timeout: 8_000 });

    await expect(page.getByRole('button', { name: 'Filters' })).toContainText('1');
  });
});
