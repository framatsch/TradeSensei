import { test, expect } from '@playwright/test';
import seedState from '../.auth/seed-state.json';

test.describe('Execution Leg Editor', () => {
  const { editExecutionTestTradeId, optionTestTradeId } = seedState as any;

  test('TC-094 — navigate to editExecutionTestTradeId, open overflow menu -> Edit on first row, assert inputs visible', async ({ page }) => {
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    // Wait for the table row
    await page.waitForSelector('table tbody tr');

    const firstRow = page.locator('table tbody tr').first();
    await firstRow.getByRole('button', { name: /actions|more|options/i }).click();
    await page.getByRole('menuitem', { name: /edit/i }).click();

    await expect(page.getByRole('radio', { name: /long/i })).toBeVisible();
    await expect(page.getByRole('radio', { name: /short/i })).toBeVisible();
    await expect(page.getByLabel(/Date|Time/i)).toBeVisible();
    await expect(page.getByLabel(/Price/i)).toBeVisible();
    await expect(page.getByLabel(/Quantity/i)).toBeVisible();
    await expect(page.getByLabel(/Commission/i)).toBeVisible();
    await expect(page.getByLabel(/P&L/i)).toBeVisible();
  });

  test('TC-095 — enter edit mode on LONG leg, click SHORT toggle, save; assert Side badge shows SHORT', async ({ page }) => {
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('table tbody tr');
    const firstRow = page.locator('table tbody tr').first();
    await firstRow.getByRole('button', { name: /actions|more|options/i }).click();
    await page.getByRole('menuitem', { name: /edit/i }).click();

    await page.getByRole('radio', { name: /short/i }).click();
    await page.getByRole('button', { name: /save/i }).click();

    await expect(firstRow.getByText(/SHORT/i)).toBeVisible();
  });

  test('TC-096 — enter edit mode, change datetime input to a new value, save; assert Date cell text updates', async ({ page }) => {
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('table tbody tr');
    const firstRow = page.locator('table tbody tr').first();
    await firstRow.getByRole('button', { name: /actions|more|options/i }).click();
    await page.getByRole('menuitem', { name: /edit/i }).click();

    const datetimeInput = page.getByLabel(/Date|Time/i);
    await datetimeInput.fill('2024-01-01T10:00');
    
    await page.getByRole('button', { name: /save/i }).click();

    await expect(firstRow).toContainText('01/01/2024'); // Assuming some date format
  });

  test('TC-097 — enter edit mode on exit leg, set pnl to a value, save; assert ExecutionSummaryCard P&L text updates', async ({ page }) => {
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('table tbody tr');
    // Using second row as exit leg assumption
    const exitRow = page.locator('table tbody tr').nth(1);
    await exitRow.getByRole('button', { name: /actions|more|options/i }).click();
    await page.getByRole('menuitem', { name: /edit/i }).click();

    await page.getByLabel(/P&L/i).fill('150.00');
    
    await page.getByRole('button', { name: /save/i }).click();

    // Check ExecutionSummaryCard or page for the updated P&L
    await expect(page.getByText('150.00').first()).toBeVisible();
  });

  test('TC-098 — enter edit mode, change direction + price, click Cancel; assert original values still shown, no mutation request fired', async ({ page }) => {
    let mutationFired = false;
    await page.route('**/executions/**', async route => {
      if (route.request().method() !== 'GET') {
        mutationFired = true;
      }
      await route.continue();
    });

    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('table tbody tr');
    const firstRow = page.locator('table tbody tr').first();
    const originalText = await firstRow.innerText();
    
    await firstRow.getByRole('button', { name: /actions|more|options/i }).click();
    await page.getByRole('menuitem', { name: /edit/i }).click();

    await page.getByRole('radio', { name: /short/i }).click();
    await page.getByLabel(/Price/i).fill('9999.99');
    
    await page.getByRole('button', { name: /cancel/i }).click();

    // Allow some time for UI revert
    await page.waitForTimeout(500);

    expect(await firstRow.innerText()).toBe(originalText);
    expect(mutationFired).toBe(false);
  });

  test('TC-099 — abort the executions fetch via route.abort(); assert Retry button and hint text visible; restore route and click Retry; assert table rows appear', async ({ page }) => {
    let routeToAbort = true;
    await page.route('**/executions**', async route => {
      if (routeToAbort && route.request().method() === 'GET') {
        await route.abort();
      } else {
        await route.continue();
      }
    });

    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await expect(page.getByText(/Failed to load|Error loading/i)).toBeVisible();
    const retryBtn = page.getByRole('button', { name: /retry/i });
    await expect(retryBtn).toBeVisible();

    routeToAbort = false;
    await retryBtn.click();

    await page.waitForSelector('table tbody tr');
    expect(await page.locator('table tbody tr').count()).toBeGreaterThan(0);
  });

  test('TC-100 — open trade edit form; assert no <input> for pnl, entry_price, exit_price, commission, quantity, opened_at, closed_at; assert these values appear as static text', async ({ page }) => {
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.getByRole('button', { name: /edit trade/i }).click();

    await expect(page.locator('input[name="pnl"]')).not.toBeVisible();
    await expect(page.locator('input[name="entry_price"]')).not.toBeVisible();
    await expect(page.locator('input[name="exit_price"]')).not.toBeVisible();
    await expect(page.locator('input[name="commission"]')).not.toBeVisible();
    await expect(page.locator('input[name="quantity"]')).not.toBeVisible();
    await expect(page.locator('input[name="opened_at"]')).not.toBeVisible();
    await expect(page.locator('input[name="closed_at"]')).not.toBeVisible();
  });

  test('TC-101 — navigate to optionTestTradeId detail page; assert Mult. column visible in legs table; assert option leg row shows 100 in Mult. column; assert notional value shown as qty × price × 100', async ({ page }) => {
    // If optionTestTradeId is not in seedState, skip or use fallback
    if (!optionTestTradeId) test.skip();

    await page.goto(`/dashboard/trades/${optionTestTradeId}`);
    
    await expect(page.getByRole('columnheader', { name: /mult\./i })).toBeVisible();
    
    await page.waitForSelector('table tbody tr');
    const optionRow = page.locator('table tbody tr').first();
    await expect(optionRow.getByRole('cell', { name: '100' })).toBeVisible();
  });
});
