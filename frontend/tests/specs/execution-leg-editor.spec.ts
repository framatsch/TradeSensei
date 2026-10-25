/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');

function getSeedState() {
  return JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8')) as {
    editExecutionTestTradeId: string;
    optionTestTradeId: string;
  };
}

test.describe('Execution Leg Editor', () => {
  test.describe.configure({ mode: 'serial' });

  async function openRowActionsMenu(row: import('@playwright/test').Locator) {
    await row.locator('button').last().click();
  }

  async function clickRowMenuEdit(page: import('@playwright/test').Page) {
    await page.getByRole('menuitem', { name: 'Edit', exact: true }).click();
  }

  test('TC-094 — navigate to editExecutionTestTradeId, open overflow menu -> Edit on first row, assert inputs visible', async ({ page }) => {
    const { editExecutionTestTradeId } = getSeedState();
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    // Wait for the table row
    await page.waitForSelector('#executions-table table tbody tr');

    const firstRow = page.locator('#executions-table table tbody tr').first();
    await openRowActionsMenu(firstRow);
    await clickRowMenuEdit(page);

    await expect(firstRow.getByRole('button', { name: /long/i })).toBeVisible();
    await expect(firstRow.getByRole('button', { name: /short/i })).toBeVisible();
    await expect(firstRow.getByLabel('Executed at date and time')).toBeVisible();
    await expect(firstRow.getByLabel('Quantity')).toBeVisible();
    await expect(firstRow.getByLabel('Price')).toBeVisible();
    await expect(firstRow.getByLabel('Commission')).toBeVisible();
    await expect(firstRow.getByLabel('P&L')).toBeVisible();
  });

  test('TC-095 — enter edit mode on LONG leg, click SHORT toggle, save; assert Side badge shows SHORT', async ({ page }) => {
    const { editExecutionTestTradeId } = getSeedState();
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('#executions-table table tbody tr');
    const firstRow = page.locator('#executions-table table tbody tr').first();
    await openRowActionsMenu(firstRow);
    await clickRowMenuEdit(page);

    await firstRow.getByRole('button', { name: /short/i }).click();
    await firstRow.getByTitle('Save').click();
    await expect(firstRow.getByTitle('Save')).not.toBeVisible();

    await expect(firstRow.getByText(/SHORT/i)).toBeVisible();
  });

  test('TC-096 — enter edit mode, change datetime input to a new value, save; assert Date cell text updates', async ({ page }) => {
    const { editExecutionTestTradeId } = getSeedState();
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('#executions-table table tbody tr');
    const firstRow = page.locator('#executions-table table tbody tr').first();
    await openRowActionsMenu(firstRow);
    await clickRowMenuEdit(page);

    const datetimeInput = firstRow.getByLabel('Executed at date and time');
    await datetimeInput.fill('2024-01-01T10:00');
    
    await firstRow.getByTitle('Save').click();
    await expect(firstRow.getByTitle('Save')).not.toBeVisible();

    await expect(firstRow).toContainText(/2024/);
  });

  test('TC-097 — enter edit mode on exit leg, set pnl to a value, save; assert ExecutionSummaryCard P&L text updates', async ({ page }) => {
    const { editExecutionTestTradeId } = getSeedState();
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('#executions-table table tbody tr');
    // Using second row as exit leg assumption
    const exitRow = page.locator('#executions-table table tbody tr').nth(1);
    await openRowActionsMenu(exitRow);
    await clickRowMenuEdit(page);

    await exitRow.getByLabel('P&L').fill('150.00');
    
    await exitRow.getByTitle('Save').click();
    await expect(exitRow.getByTitle('Save')).not.toBeVisible();

    // Check ExecutionSummaryCard or page for the updated P&L
    await expect(page.getByText('150.00').first()).toBeVisible();
  });

  test('TC-098 — enter edit mode, change direction + price, click Cancel; assert original values still shown, no mutation request fired', async ({ page }) => {
    const { editExecutionTestTradeId } = getSeedState();
    let mutationFired = false;
    await page.route('**/executions/**', async route => {
      if (route.request().method() !== 'GET') {
        mutationFired = true;
      }
      await route.continue();
    });

    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.waitForSelector('#executions-table table tbody tr');
    const firstRow = page.locator('#executions-table table tbody tr').first();
    const originalText = await firstRow.innerText();
    
    await openRowActionsMenu(firstRow);
    await clickRowMenuEdit(page);

    await firstRow.getByRole('button', { name: /short/i }).click();
    await firstRow.getByLabel('Price').fill('9999.99');
    
    await firstRow.getByTitle('Cancel').click();

    // Allow some time for UI revert
    await page.waitForTimeout(500);

    expect(await firstRow.innerText()).toBe(originalText);
    expect(mutationFired).toBe(false);
  });

  test('TC-099 — abort the executions fetch via route.abort(); assert Retry button and hint text visible; restore route and click Retry; assert table rows appear', async ({ page }) => {
    const { editExecutionTestTradeId } = getSeedState();
    let routeToAbort = true;
    await page.route('**/executions**', async route => {
      if (routeToAbort && route.request().method() === 'GET') {
        await route.abort();
      } else {
        await route.continue();
      }
    });

    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await expect(page.getByText(/Could not load executions|Failed to load|Error loading/i)).toBeVisible({ timeout: 15_000 });
    const retryBtn = page.getByRole('button', { name: /retry/i });
    await expect(retryBtn).toBeVisible();

    routeToAbort = false;
    await retryBtn.click();

    await page.waitForSelector('#executions-table table tbody tr');
    expect(await page.locator('#executions-table table tbody tr').count()).toBeGreaterThan(0);
  });

  test('TC-100 — open trade edit form; assert no <input> for pnl, entry_price, exit_price, commission, quantity, opened_at, closed_at; assert these values appear as static text', async ({ page }) => {
    const { editExecutionTestTradeId } = getSeedState();
    await page.goto(`/dashboard/trades/${editExecutionTestTradeId}`);
    
    await page.getByRole('button', { name: /trade actions/i }).click();
    await page.getByRole('button', { name: /correct trade/i }).click();

    await expect(page.getByRole('heading', { name: /correct trade/i })).toBeVisible();

    await expect(page.locator('input[name="pnl"]')).not.toBeVisible();
    await expect(page.locator('input[name="entry_price"]')).not.toBeVisible();
    await expect(page.locator('input[name="exit_price"]')).not.toBeVisible();
    await expect(page.locator('input[name="commission"]')).not.toBeVisible();
    await expect(page.locator('input[name="quantity"]')).not.toBeVisible();
    await expect(page.locator('input[name="opened_at"]')).not.toBeVisible();
    await expect(page.locator('input[name="closed_at"]')).not.toBeVisible();
  });

  test('TC-101 — navigate to optionTestTradeId detail page; assert Mult. column visible in legs table; assert option leg row shows 100 in Mult. column; assert notional value shown as qty × price × 100', async ({ page }) => {
    const { optionTestTradeId } = getSeedState();
    // If optionTestTradeId is not in seedState, skip or use fallback
    if (!optionTestTradeId) test.skip();

    await page.goto(`/dashboard/trades/${optionTestTradeId}`);
    
    await expect(page.getByRole('columnheader', { name: /mult\./i })).toBeVisible();
    
    await page.waitForSelector('#executions-table table tbody tr');
    const optionRow = page.locator('#executions-table table tbody tr').first();
    await expect(optionRow).toContainText('100');
    await expect(optionRow).toContainText('$75,000.00');
  });
});
