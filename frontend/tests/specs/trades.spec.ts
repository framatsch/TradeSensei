/**
 * Trades Spec — covers the trade list page (table rendering, pagination,
 * column headers, empty state, and trade detail navigation).
 *
 * All tests run as the seeded E2E user. globalSetup has inserted 10 trades,
 * so the table should be populated.
 */

import { test, expect } from '@playwright/test';

test.describe('Trades List', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/trades');
    // Wait for table to finish loading
    await page.waitForLoadState('networkidle');
  });

  test('TC-050 renders page heading and subtitle', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Trades' })).toBeVisible();
    await expect(page.getByText('All recorded trading positions')).toBeVisible();
  });

  test('TC-051 table renders all column headers', async ({ page }) => {
    const expectedHeaders = [
      'Symbol',
      'Direction',
      'Asset Class',
      'Entry Price',
      'Exit Price',
      'PnL',
      'Opened At',
      'Closed At',
    ];
    for (const header of expectedHeaders) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible({
        timeout: 10_000,
      });
    }
  });

  test('TC-052 table shows seeded trades (at least 10 rows)', async ({ page }) => {
    // Wait for rows to appear
    const rows = page.locator('tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 15_000 });
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(10);
  });

  test('TC-053 trade rows contain expected symbols', async ({ page }) => {
    // AAPL was seeded twice — should appear in the table
    await expect(page.getByRole('cell', { name: 'AAPL' }).first()).toBeVisible({ timeout: 15_000 });
  });

  test('TC-054 direction badges LONG and SHORT are shown', async ({ page }) => {
    await expect(page.getByText('LONG').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('SHORT').first()).toBeVisible({ timeout: 10_000 });
  });

  test('TC-055 pagination Previous button is disabled on first page', async ({ page }) => {
    const prevBtn = page.getByRole('button', { name: 'Previous' });
    await expect(prevBtn).toBeVisible({ timeout: 10_000 });
    await expect(prevBtn).toBeDisabled();
  });

  test('TC-056 pagination Next button is disabled when all trades fit on one page', async ({
    page,
  }) => {
    // We have 10 trades and default page size is 20 — Next should be disabled
    const nextBtn = page.getByRole('button', { name: 'Next' });
    await expect(nextBtn).toBeVisible({ timeout: 10_000 });
    // With 10 seeded trades, all fit on one page
    await expect(nextBtn).toBeDisabled();
  });

  test('TC-057 clicking a trade row navigates to trade detail', async ({ page }) => {
    // The first row should be a link or clickable
    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();

    // Detail page URL should contain a UUID segment
    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });
  });
});

test.describe('Trade Detail', () => {
  test('TC-060 trade detail page shows trade fields', async ({ page }) => {
    // Navigate to trades list first to get a real trade ID
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Detail page should show some trade data
    // At minimum the page should render without a 404
    await expect(page.locator('main')).toBeVisible();
  });
});
