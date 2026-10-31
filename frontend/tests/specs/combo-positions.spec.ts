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

import { expect, test } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');

function getSeedState() {
  return JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8')) as {
    comboTestTradeId: string;
    executionTradeId: string;
    comboImportedClosedTradeId: string;
  };
}

test.describe('Combo Positions', () => {
  test('TC-101 — combo badge visible on trade detail', async ({ page }) => {
    const seedState = getSeedState();
    await page.goto(`/dashboard/trades/${seedState.comboTestTradeId}`);
    await expect(page.getByRole('heading', { name: 'AAPL' })).toBeVisible();

    const header = page.getByRole('heading', { name: 'AAPL', level: 1, exact: true }).locator('../..');
    await expect(header.getByText('COMBO').first()).toBeVisible();
    await expect(header.getByText('LONG')).toHaveCount(0);
    await expect(header.getByText('SHORT')).toHaveCount(0);
  });

  test('TC-102 — execution summary shows grouped rows for combo', async ({ page }) => {
    const seedState = getSeedState();
    await page.goto(`/dashboard/trades/${seedState.comboTestTradeId}`);
    await expect(page.getByRole('heading', { name: 'Execution Summary' })).toBeVisible();

    await expect(page.getByText('AAPL EQUITY')).toBeVisible();
    await expect(page.getByText('AAPL OPTION')).toBeVisible();
    await expect(page.getByText('+$600.00').last()).toBeVisible();

    await expect(page.getByText('VWAP Entry')).not.toBeVisible();
    await expect(page.getByText('VWAP Exit')).not.toBeVisible();
  });

  test('TC-103 — execution legs table shows symbol and asset class columns', async ({ page }) => {
    const seedState = getSeedState();
    await page.goto(`/dashboard/trades/${seedState.comboTestTradeId}`);
    await expect(page.getByRole('button', { name: /Execution Legs/ })).toBeVisible();

    await expect(page.getByRole('columnheader', { name: 'Symbol' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Asset Class' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'AAPL' }).first()).toBeVisible();
    await expect(page.getByRole('cell', { name: 'EQUITY' }).first()).toBeVisible();
    await expect(page.getByRole('cell', { name: 'OPTION' }).first()).toBeVisible();
  });

  test('TC-104 — standard trade detail stays unchanged', async ({ page }) => {
    const seedState = getSeedState();
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await expect(page.getByRole('heading', { name: 'Execution Summary' })).toBeVisible();

    await expect(page.getByRole('columnheader', { name: 'Symbol' })).toHaveCount(0);
    await expect(page.getByRole('columnheader', { name: 'Asset Class' })).toHaveCount(0);
    await expect(page.getByText('VWAP Entry')).toBeVisible();
  });

  test('TC-105 — trades list shows combo indicator', async ({ page }) => {
    const seedState = getSeedState();
    // Narrow list and widen date range so seeded combo row is guaranteed to be on-page
    await page.goto('/dashboard/trades?symbol=AAPL&opened_at_from=2000-01-01&limit=100');
    await expect(page.getByRole('link', { name: 'New Trade' }).first()).toBeVisible({ timeout: 15_000 });

    const comboRow = page.locator(`tr:has(a[href="/dashboard/trades/${seedState.comboTestTradeId}"])`);
    await expect(comboRow).toBeVisible({ timeout: 20000 });
    await expect(comboRow).toContainText('COMBO');
  });

  test('TC-106 — create combo trade from form', async ({ page }) => {
    await page.goto('/dashboard/trades/new');
    await expect(page.getByRole('heading', { name: 'New Trade' })).toBeVisible({ timeout: 15_000 });

    await page.getByLabel('COMBO position').check();
    await expect(page.getByLabel('Asset Class *')).toHaveCount(0);

    await page.locator('input[name="symbol"]').fill('MSFT');
    await page.locator('select[name="direction"]').selectOption('LONG');

    // Advanced mode is forced for COMBOs, so we must add at least 1 leg
    await page.getByRole('button', { name: 'Add Leg' }).click();
    const legQuantities = page.locator('input[name^="executions."][name$=".quantity"]');
    const legPrices = page.locator('input[name^="executions."][name$=".price"]');
    const legSides = page.locator('select[name^="executions."][name$=".direction"]');
    const legDates = page.locator('input[name^="executions."][name$=".executed_at"]');
    
    await expect(legSides.nth(0)).toBeVisible({ timeout: 5000 });
    await legSides.nth(0).selectOption('LONG');
    await legDates.nth(0).fill('2026-04-19T10:00');
    await legQuantities.nth(0).fill('10');
    await legPrices.nth(0).fill('100');
    await legPrices.nth(0).blur();

    await page.getByRole('button', { name: 'Create Trade' }).click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 15000 });
    const header = page.getByRole('heading', { name: 'MSFT', level: 1, exact: true }).locator('../..');
    await expect(header.getByText('COMBO', { exact: true })).toBeVisible();
  });

  test('TC-107 — imported closed vertical shows open/close legs and two summary rows', async ({ page }) => {
    const seedState = getSeedState();
    test.skip(!seedState.comboImportedClosedTradeId, 'Imported combo seed not available in this environment.');

    await page.goto(`/dashboard/trades/${seedState.comboImportedClosedTradeId}`);
    await expect(page.getByRole('heading', { name: 'QQQ' })).toBeVisible();

    const header = page.getByRole('heading', { name: 'QQQ', level: 1, exact: true }).locator('../..');
    await expect(header.getByText('COMBO').first()).toBeVisible();

    await expect(page.getByRole('columnheader', { name: 'Open/Close' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Open' })).toHaveCount(2);
    await expect(page.getByRole('cell', { name: 'Close' })).toHaveCount(2);

    await expect(page.getByRole('row', { name: /QQQ OPTION \(878467678\)/ })).toBeVisible();
    await expect(page.getByRole('row', { name: /QQQ OPTION \(884162799\)/ })).toBeVisible();
  });
});
