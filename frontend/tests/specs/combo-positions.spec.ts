import { expect, test } from '@playwright/test';
import seedState from '../.auth/seed-state.json';

test.describe('Combo Positions', () => {
  test('TC-101 — combo badge visible on trade detail', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.comboTestTradeId}`);
    await expect(page.getByRole('heading', { name: 'AAPL' })).toBeVisible();

    const header = page.locator('h1').first().locator('..');
    await expect(header.getByText('COMBO').first()).toBeVisible();
    await expect(header.getByText('LONG')).toHaveCount(0);
    await expect(header.getByText('SHORT')).toHaveCount(0);
  });

  test('TC-102 — execution summary shows grouped rows for combo', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.comboTestTradeId}`);
    await expect(page.getByRole('heading', { name: 'Execution Summary' })).toBeVisible();

    await expect(page.getByText('AAPL EQUITY')).toBeVisible();
    await expect(page.getByText('AAPL OPTION')).toBeVisible();
    await expect(page.getByText('Combined P&L: $600.00')).toBeVisible();

    await expect(page.getByText('VWAP Entry')).not.toBeVisible();
    await expect(page.getByText('VWAP Exit')).not.toBeVisible();
  });

  test('TC-103 — execution legs table shows symbol and asset class columns', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.comboTestTradeId}`);
    await expect(page.getByRole('button', { name: /Execution Legs/ })).toBeVisible();

    await expect(page.getByRole('columnheader', { name: 'Symbol' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Asset Class' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'AAPL' }).first()).toBeVisible();
    await expect(page.getByRole('cell', { name: 'EQUITY' }).first()).toBeVisible();
    await expect(page.getByRole('cell', { name: 'OPTION' }).first()).toBeVisible();
  });

  test('TC-104 — standard trade detail stays unchanged', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await expect(page.getByRole('heading', { name: 'Execution Summary' })).toBeVisible();

    await expect(page.getByRole('columnheader', { name: 'Symbol' })).toHaveCount(0);
    await expect(page.getByRole('columnheader', { name: 'Asset Class' })).toHaveCount(0);
    await expect(page.getByText('VWAP Entry')).toBeVisible();
  });

  test('TC-105 — trades list shows combo indicator', async ({ page }) => {
    // Narrow list and widen date range so seeded combo row is guaranteed to be on-page
    await page.goto('/dashboard/trades?symbol=AAPL&opened_at_from=2000-01-01&limit=100');
    await expect(page.getByRole('link', { name: 'New Trade' }).first()).toBeVisible();

    const comboRow = page.locator(`tr:has(a[href="/dashboard/trades/${seedState.comboTestTradeId}"])`);
    await expect(comboRow).toBeVisible({ timeout: 20000 });
    await expect(comboRow).toContainText('COMBO');
  });

  test('TC-106 — create combo trade from form', async ({ page }) => {
    await page.goto('/dashboard/trades/new');
    await expect(page.getByRole('heading', { name: 'New Trade' })).toBeVisible();

    await page.getByLabel('COMBO position').check();
    await expect(page.getByLabel('Asset Class *')).toHaveCount(0);

    await page.locator('input[name="symbol"]').fill('MSFT');
    await page.locator('select[name="direction"]').selectOption('LONG');
    await page.locator('input[name="opened_at"]').fill('2026-04-19T10:00');

    await page.getByRole('button', { name: 'Create Trade' }).click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i);
    await expect(page.getByText('COMBO').first()).toBeVisible();
  });
});
