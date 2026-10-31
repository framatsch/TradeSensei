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

/**
 * Trades Spec — covers the trade list page (table rendering, pagination,
 * column headers, empty state, and trade detail navigation).
 *
 * All tests run as the seeded E2E user. globalSetup has inserted 10 trades,
 * plus special seeded trades for execution and merge workflow tests.
 */

import { test, expect, chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { z } from 'zod';
import { tradeMobileTest, expectNoTradeOverflow } from '../fixtures/trade-mobile-layout';

const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');
const seedState = new Proxy(
  {} as {
    executionTradeId: string;
    addExecutionTestTradeId: string;
    detachTestTradeId: string;
    mergeTradeIds: [string, string];
  },
  {
    get(_target, prop: string) {
      const data = JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8'));
      return data[prop];
    },
  }
);

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';

const EMPTY_USER = {
  username: 'e2e_emptyuser',
  email: 'e2e_emptyuser@example.com',
  password: 'E2eEmptyPass123!',
};

test.describe('Trades List', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/trades');
    // Wait for table to finish loading
  });

  test('TC-050 renders page heading and subtitle', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Trades' })).toBeVisible();
    await expect(page.getByText('Manage, filter, and review your trading history.')).toBeVisible();
  });

  test('TC-051 table renders all column headers', async ({ page }) => {
    // Increase timeout and ensure large viewport
    test.slow();
    await page.setViewportSize({ width: 1600, height: 1000 });

    const expectedHeaders = [
      'Symbol',
      'Direction',
      'Asset Class',
      'Qty',
      'Broker',
      'Entry Price',
      'Exit Price',
      'PnL',
      'Opened At',
      'Closed At',
      'Tags',
    ];
    // Wait for table to be fully loaded
    await page.waitForSelector('thead th', { timeout: 15_000 });
    
    // Check for each header in the table to ensure they are present.
    // Some headers might be hidden on small screens, so we ensure the viewport is large.
    await page.setViewportSize({ width: 1440, height: 900 });

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

  test('TC-055 pagination Previous button is not shown when there is only one page', async ({ page }) => {
    const prevBtn = page.getByRole('button', { name: 'Previous' });
    await expect(prevBtn).toBeHidden({ timeout: 10_000 });
  });

  test('TC-056 pagination Next button is not shown when there are no more pages', async ({ page }) => {
    const nextBtn = page.getByRole('button', { name: 'Next', exact: true });
    await expect(nextBtn).toBeHidden({ timeout: 10_000 });

    const rows = page.locator('tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });
    const count = await rows.count();
    expect(count).toBeLessThanOrEqual(20);
  });

  test('TC-057 clicking the symbol link in a trade row navigates to trade detail', async ({ page }) => {
    // Rows have a <Link> on the symbol text in the first column — click that
    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    // Detail page URL should contain a UUID segment
    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });
  });
});

test.describe('Trade Detail', () => {
  // ── TC-060: Trade detail page renders trade header ──
  test('TC-060 trade detail page renders trade header', async ({ page }) => {
    // Navigate to trades list first to get a real trade ID
    await page.goto('/dashboard/trades');

    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Assert main is visible
    await expect(page.locator('main')).toBeVisible();
    // Assert at least one direction badge (LONG or SHORT) is visible
    await expect(
      page.getByText('LONG').or(page.getByText('SHORT')).filter({ visible: true }).first()
    ).toBeVisible();
  });

  // ── TC-061: Execution Summary Card content ──
  test('TC-061 execution summary card shows VWAP entry, quantity, total commission', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Assert Execution Summary heading visible
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });
    // Assert VWAP Entry label visible
    await expect(page.getByText('VWAP Entry')).toBeVisible();
    // Assert the entry price ($400.00) appears in the card
    await expect(page.getByRole('definition').filter({ hasText: '$400.00' }).first()).toBeVisible();
    // Assert Total Quantity label visible
    await expect(page.getByText('Total Quantity')).toBeVisible();
    // Assert total commission ($3.00) visible in the execution summary card
    // We use a broader search if the exact $3.00 isn't unique or easily found
    await expect(page.locator('dt:has-text("Total Commission") + dd')).toContainText('3.00');
  });

  // ── TC-062: Execution table renders with correct direction badges ──
  test('TC-062 execution table has correct number of rows with LONG and SHORT badges', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 25_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    // Assert execution table has at least 2 rows (account for parallel TC-071)
    const tbodyRows = page.locator('table tbody tr');
    const count = await tbodyRows.count();
    expect(count).toBeGreaterThanOrEqual(2);

    // The seeded executions include both directions (order may vary with parallel tests)
    const sideCells = page.locator('table tbody tr td:nth-child(2)');
    await expect(sideCells.filter({ hasText: 'LONG' }).first()).toBeVisible();
    await expect(sideCells.filter({ hasText: 'SHORT' }).first()).toBeVisible();
  });

  // ── TC-063: Execution dates are in chronological order ──
  test('TC-063 execution dates are in chronological order', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 25_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    const tbodyRows = page.locator('table tbody tr');
    // Ensure we have at least 2 rows from seeding
    const rowCount = await tbodyRows.count();
    expect(rowCount).toBeGreaterThanOrEqual(2);

    const rows = await tbodyRows.all();
    const dates: number[] = [];

    for (const row of rows) {
      const dateCell = row.locator('td').first();
      const text = await dateCell.textContent();
      if (text) dates.push(new Date(text).getTime());
    }

    // Verify dates are non-decreasing (oldest first in list)
    for (let i = 0; i < dates.length - 1; i++) {
      expect(dates[i]).toBeLessThanOrEqual(dates[i + 1]);
    }
  });

  // ── TC-064: Add Execution button is visible ──
  test('TC-064 add execution button is visible', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    await expect(page.getByRole('button', { name: 'Add Execution' })).toBeVisible();
  });

  // ── TC-065: Sidebar performance labels are visible ──
  test('TC-065 sidebar labels gross p&l, net p&l, return %, holding period are visible', async ({ page }) => {
    // Navigate via list
    await page.goto('/dashboard/trades');

    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Assert all four labels visible
    await expect(page.getByText('Gross P&L')).toBeVisible();
    await expect(page.getByText('Net P&L')).toBeVisible();
    await expect(page.locator('#trade-overview-pane').getByText('Return %', { exact: true })).toBeVisible();
    await expect(page.getByText('Holding Period')).toBeVisible();
  });

  // ── TC-066: Trade actions menu ──
  test('TC-066 trade actions dropdown shows correct menu items', async ({ page }) => {
    // Navigate via list
    await page.goto('/dashboard/trades');

    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Click the trade actions button
    await page.getByRole('button', { name: 'Trade actions' }).click();

    // Assert dropdown menu items
    await expect(page.getByText('Correct Trade…')).toBeVisible();
    await expect(page.getByText('Merge with…')).toBeVisible();
  });

  // ── TC-067: Position Conflict banner is not visible on normal trade ──
  test('TC-067 position conflict banner is not visible on normal trade', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Assert Position Conflict is NOT visible
    await expect(page.getByText('Position Conflict')).not.toBeVisible();
  });
});

test.describe('Add Execution Modal', () => {
  async function openAddExecutionModal(page: import('@playwright/test').Page) {
    const addExecutionButton = page.getByRole('button', { name: 'Add Execution' }).first();
    await expect(addExecutionButton).toBeVisible({ timeout: 15_000 });
    await addExecutionButton.click();
    await expect(page.locator('#add-execution-form')).toBeVisible({ timeout: 10_000 });
  }

  // ── TC-070: Add Execution modal opens with BUY/SELL toggles ──
  test('TC-070 add execution modal opens with toggle and datetime input', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    await openAddExecutionModal(page);

    // Assert modal heading visible
    await expect(page.locator('#add-execution-form').getByRole('button', { name: 'BUY' })).toBeVisible();
    // Assert BUY toggle visible
    await expect(page.locator('#add-execution-form').getByRole('button', { name: 'BUY' })).toBeVisible();
    // Assert SELL toggle visible
    await expect(page.locator('#add-execution-form').getByRole('button', { name: 'SELL' })).toBeVisible();
    // Assert datetime-local input visible
    await expect(page.locator('#add-execution-form input[type="datetime-local"]')).toBeVisible();
  });

  // ── TC-071: Successfully add execution increases table row count ──
  test('TC-071 adding execution with quantity and price increases table rows', async ({ page }) => {
    // Use dedicated add-execution-test trade to avoid race conditions with other tests
    await page.goto(`/dashboard/trades/${seedState.addExecutionTestTradeId}`);

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 25_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    const tbodyRows = page.locator('table tbody tr');
    // Assert we have exactly 3 rows: 1 auto-created + 2 manual from seeding
    await expect(tbodyRows).toHaveCount(3, { timeout: 15_000 });
    const initialCount = 3;

    await openAddExecutionModal(page);

    // Fill in quantity and price using positional index within the form
    const form = page.locator('#add-execution-form');
    const numberInputs = form.locator('input[type="number"]');
    await numberInputs.nth(0).fill('10');  // Quantity
    await numberInputs.nth(1).fill('410.00');  // Price

    // Click submit button in modal
    await form.getByRole('button', { name: 'Add Execution' }).click();

    // Wait for modal to close
    await expect(page.locator('#add-execution-form')).not.toBeVisible({ timeout: 10_000 });

    // Assert row count increased by 1
    await expect(page.locator('table tbody tr')).toHaveCount(initialCount + 1, { timeout: 15_000 });
  });

  // ── TC-072: Validation error on quantity 0 ──
  test('TC-072 validation error shown when quantity is 0', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 25_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    await openAddExecutionModal(page);

    // Set quantity to 0 — scoped to the modal form
    const quantityInput = page.locator('#add-execution-form input[type="number"]').first();
    await quantityInput.clear();
    await quantityInput.fill('0');

    await expect(page.locator('table tbody tr')).toHaveCount(2, { timeout: 15_000 });

    // Click submit button
    await page.locator('#add-execution-form').getByRole('button', { name: 'Add Execution' }).click();

    // For invalid quantity, modal stays open and no new execution is added
    await expect(page.locator('#add-execution-form')).toBeVisible();
    await expect(page.locator('table tbody tr')).toHaveCount(2);
  });
});

test.describe('Inline Sidebar Editing', () => {
  // ── TC-075: Inline edit Stop Loss ──
  test('TC-075 inline edit stop loss value', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 25_000 });

    // Find Stop Loss section — scoped to the sidebar card that contains it
    // InlineNumberField renders a button with title "Click to edit Stop Loss" in view mode
    const stopLossEditBtn = page.getByTitle('Click to edit Stop Loss');
    await expect(stopLossEditBtn).toBeVisible({ timeout: 10_000 });

    // Click on the value button to enter edit mode
    await stopLossEditBtn.click();

    // Wait for the number input to appear (InlineNumberField switches to edit mode)
    const numberInput = page.locator('input[type="number"]').filter({ has: page.locator(':scope') }).last();
    // More specific: the input near the Stop Loss label
    const stopLossRow = page.locator('div').filter({ has: page.locator('span', { hasText: 'Stop Loss' }) }).last();
    const editInput = stopLossRow.locator('input[type="number"]');
    await expect(editInput).toBeVisible({ timeout: 10_000 });

    // Type the new value and press Enter to save
    await editInput.fill('150.00');
    await editInput.press('Enter');

    // Wait for input to disappear (edit mode exited)
    await expect(editInput).not.toBeVisible({ timeout: 15_000 });

    // Assert Stop Loss display button reflects the updated value
    await expect(page.getByTitle('Click to edit Stop Loss')).toContainText('$150.00');
  });

  // ── TC-076: Edit Playbook ──
  test('TC-076 inline edit playbook field', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Select Playbook (QualitativeMetadataPanel is directly editable; changing it reveals Save)
    const playbookSelect = page.locator('select').filter({ hasText: 'Select a playbook' });
    await expect(playbookSelect).toBeVisible({ timeout: 15_000 });
    await playbookSelect.selectOption({ label: 'Breakout' });

    // Save
    const saveBtn = page.getByRole('button', { name: 'Save', exact: true });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();
    await expect(saveBtn).not.toBeVisible({ timeout: 10_000 });

    // Assert the field now shows Breakout
    await expect(page.locator('select').filter({ hasText: 'Breakout' })).toHaveValue(/^[a-zA-Z0-9-]{36}$/); // uuid
    await expect(page.locator('select').filter({ hasText: 'Breakout' }).locator('option:checked')).toHaveText('Breakout');
  });

  // ── TC-077: Edit Taxonomies ──
  test('TC-077 inline edit taxonomies in playbook psychology card', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Click on taxonomy badge to toggle it (QualitativeMetadataPanel is directly editable)
    const tagBtn = page.getByRole('button', { name: /high-conviction/i });
    await expect(tagBtn).toBeVisible({ timeout: 15_000 });
    await tagBtn.click();

    // Save
    const saveBtn = page.getByRole('button', { name: 'Save', exact: true });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // Verify save completes and Unsaved changes banner disappears
    await expect(saveBtn).not.toBeVisible({ timeout: 10_000 });
  });
});

test.describe.serial('Merge Workflow', () => {
  // Helper: locate a trade row by the trade ID stored in the link's title attribute
  function tradeRow(page: import('@playwright/test').Page, tradeId: string) {
    return page.locator(`tr:has(a[title="${tradeId}"])`);
  }

  // ── TC-080: Select two trades and Merge button appears ──
  test('TC-080 selecting two trades shows merge button in toolbar', async ({ page }) => {
    // Show all rows and narrow to AAPL so seeded merge trades are visible
    await page.goto('/dashboard/trades?symbol=AAPL&opened_at_from=2000-01-01&limit=100');

    // Wait for table rows to load
    await page.waitForSelector('tbody tr', { timeout: 25_000 });

    const [tradeId1, tradeId2] = seedState.mergeTradeIds;
    
    // Skip if no merge trade IDs were seeded
    test.skip(!tradeId1 || !tradeId2, `Merge trade IDs not found: [${tradeId1}, ${tradeId2}]`);

    // Wait for the specific rows to be present via the link title attribute
    await expect(tradeRow(page, tradeId1)).toBeVisible({ timeout: 15_000 });
    await expect(tradeRow(page, tradeId2)).toBeVisible({ timeout: 15_000 });

    // Check checkbox for first merge trade
    const checkbox1 = tradeRow(page, tradeId1).locator('input[type="checkbox"]');
    await expect(checkbox1).toBeVisible({ timeout: 15_000 });
    await checkbox1.check();

    // Check checkbox for second merge trade
    const checkbox2 = tradeRow(page, tradeId2).locator('input[type="checkbox"]');
    await expect(checkbox2).toBeVisible({ timeout: 15_000 });
    await checkbox2.check();

    // Assert Merge button appears in toolbar
    await expect(page.getByRole('button', { name: 'Merge' })).toBeVisible({ timeout: 10_000 });
  });

  // ── TC-081: Merge button opens preview modal ──
  test('TC-081 merge button opens preview modal with combined info', async ({ page }) => {
    // Show all rows and narrow to AAPL so seeded merge trades are visible
    await page.goto('/dashboard/trades?symbol=AAPL&opened_at_from=2000-01-01&limit=100');

    // Wait for table rows to load
    await page.waitForSelector('tbody tr', { timeout: 15_000 });

    const [tradeId1, tradeId2] = seedState.mergeTradeIds;
    
    // Skip if no merge trade IDs were seeded
    test.skip(!tradeId1 || !tradeId2, `Merge trade IDs not found: [${tradeId1}, ${tradeId2}]`);

    // Check both trade checkboxes using the link title attribute
    const checkbox1 = tradeRow(page, tradeId1).locator('input[type="checkbox"]');
    await expect(checkbox1).toBeVisible({ timeout: 15_000 });
    await checkbox1.check();

    const checkbox2 = tradeRow(page, tradeId2).locator('input[type="checkbox"]');
    await expect(checkbox2).toBeVisible({ timeout: 15_000 });
    await checkbox2.check();

    // Click Merge button
    await page.getByRole('button', { name: 'Merge' }).click();

    // Assert merge preview modal appears
    await expect(page.getByRole('heading', { name: 'Merge Trades' })).toBeVisible({ timeout: 10_000 });
    // Assert warning text visible
    await expect(
      page.getByText('All execution legs will be moved to the oldest trade.')
    ).toBeVisible({ timeout: 10_000 });
    // Assert Combined Qty section visible
    await expect(page.getByText('Combined Qty')).toBeVisible({ timeout: 10_000 });
  });

  // ── TC-082: Confirm merge navigates to survivor trade ──
  test('TC-082 confirming merge navigates to survivor trade detail', async ({ page }) => {
    // Show all rows and narrow to AAPL so seeded merge trades are visible
    await page.goto('/dashboard/trades?symbol=AAPL&opened_at_from=2000-01-01&limit=100');

    // Wait for table rows to load
    await page.waitForSelector('tbody tr', { timeout: 15_000 });

    const [tradeId1, tradeId2] = seedState.mergeTradeIds;
    
    // Skip if no merge trade IDs were seeded
    test.skip(!tradeId1 || !tradeId2, `Merge trade IDs not found: [${tradeId1}, ${tradeId2}]`);

    // Check both trade checkboxes using the link title attribute
    const checkbox1 = tradeRow(page, tradeId1).locator('input[type="checkbox"]');
    await expect(checkbox1).toBeVisible({ timeout: 15_000 });
    await checkbox1.check();

    const checkbox2 = tradeRow(page, tradeId2).locator('input[type="checkbox"]');
    await expect(checkbox2).toBeVisible({ timeout: 15_000 });
    await checkbox2.check();

    // Click Merge button
    await page.getByRole('button', { name: 'Merge' }).click();

    // Wait for modal to appear
    await expect(page.getByRole('heading', { name: 'Merge Trades' })).toBeVisible({ timeout: 10_000 });

    // Click Merge Trades button to confirm
    await page.getByRole('button', { name: 'Merge Trades' }).click();

    // Wait for modal to close
    await expect(page.getByRole('heading', { name: 'Merge Trades' })).not.toBeVisible({ timeout: 10_000 });

    // Assert URL navigates to survivor trade (the older one, which is mergeTradeIds[0])
    await expect(page).toHaveURL(`/dashboard/trades/${tradeId1}`, { timeout: 8_000 });
  });
});

test.describe('Execution Context Menu', () => {
  // ── TC-085: Execution overflow menu shows correct actions ──
  test('TC-085 execution overflow menu shows edit, move, detach, delete options', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 25_000 });

    // Wait for execution table rows
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });
    const tbodyRows = page.locator('table tbody tr');
    await expect(tbodyRows.first()).toBeVisible({ timeout: 10_000 });

    // Click overflow menu button in first execution row (usually the rightmost button)
    const overflowButton = tbodyRows.first().locator('button').last();
    await overflowButton.click();

    // Wait for dropdown menu to appear (it's not in the table, it's a popover)
    await page.waitForTimeout(300); // Allow dropdown animation

    // Assert dropdown shows all options - look for them anywhere on the page
    await expect(page.getByRole('menuitem', { name: 'Edit', exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole('menuitem', { name: 'Move to...', exact: true })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: 'Detach as new Trade', exact: true })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: 'Delete', exact: true })).toBeVisible();
  });

  // ── TC-086: Detach execution decreases table row count ──
  test('TC-086 detaching execution removes row from table', async ({ page }) => {
    // Use the dedicated detach-test trade to avoid race conditions with TC-071
    await page.goto(`/dashboard/trades/${seedState.detachTestTradeId}`);

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 25_000 });

    // Wait for execution table rows
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });
    let tbodyRows = page.locator('table tbody tr');
    // Assert we have exactly 4 rows: 1 auto-created + 3 manual from seeding
    await expect(tbodyRows).toHaveCount(4, { timeout: 15_000 });

    // Set up dialog handler before clicking
    page.on('dialog', (d) => d.accept());

    // Click overflow menu button in first execution row
    tbodyRows = page.locator('table tbody tr');
    await tbodyRows.first().locator('button').last().click();

    // Click Detach as new Trade (opens confirm modal)
    await page.getByText('Detach as new Trade').click();
    await expect(page.getByRole('heading', { name: 'Detach Execution' })).toBeVisible({ timeout: 10_000 });

    // Confirm detach
    await page.getByRole('button', { name: 'Detach' }).click();

    // Wait for table to update and row count to decrease by one
    await expect(page.locator('table tbody tr')).toHaveCount(3, { timeout: 15_000 });
  });
});

test.describe('Trades List — Empty State', () => {
  // Run serially so TC-058 always precedes TC-059 and the shared page state
  // is deterministic regardless of how many Playwright workers are active.
  test.describe.configure({ mode: 'serial' });

  let emptyUserToken: string;
  // Shared browser/page — created once in beforeAll, reused by both tests.
  let sharedBrowser: import('@playwright/test').Browser;
  let sharedPage: import('@playwright/test').Page;

  test.beforeAll(async () => {
    // Register a fresh user with no trades
    const regRes = await fetch(`${API_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(EMPTY_USER),
    });
    // 201 = new user, 409 = already exists (leftover from a failed run) — both ok
    if (regRes.status !== 201 && regRes.status !== 409) {
      throw new Error(`Failed to register empty user: ${regRes.status}`);
    }

    // Brief pause so the backend's async session commit is visible to the next
    // DB connection before we immediately attempt to log in (race condition fix).
    if (regRes.status === 201) {
      await new Promise((resolve) => setTimeout(resolve, 300));
    }

    // Log in to get a token
    const loginForm = new URLSearchParams({
      username: EMPTY_USER.username,
      password: EMPTY_USER.password,
    });
    const loginRes = await fetch(`${API_URL}/api/v1/auth/token`, {
      method: 'POST',
      body: loginForm,
    });
    if (!loginRes.ok) throw new Error(`Empty user login failed: ${loginRes.status}`);
    const loginData = (await loginRes.json()) as { access_token: string };
    emptyUserToken = loginData.access_token;

    // Create a portfolio for the empty user so EmptyPortfolioGate doesn't block the trades page
    const portfolioRes = await fetch(`${API_URL}/api/v1/portfolios`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${emptyUserToken}` },
      body: JSON.stringify({ name: 'Empty Portfolio', base_currency: 'USD', color_hex: '#6366f1' }),
    });
    let emptyPortfolioId = '';
    if (portfolioRes.ok) {
      const portfolioBody = (await portfolioRes.json()) as { data: { id: string } };
      emptyPortfolioId = portfolioBody.data.id;
    }

    // Launch one shared browser + context, inject the token once.
    sharedBrowser = await chromium.launch({ headless: true });
    const context = await sharedBrowser.newContext({ baseURL: BASE_URL });
    sharedPage = await context.newPage();

    await sharedPage.goto('/dashboard/trades');
    await sharedPage.evaluate(
      ({ token, portfolioId }: { token: string; portfolioId: string }) => {
        localStorage.setItem('access_token', token);
        if (portfolioId) localStorage.setItem('active_portfolio_id', portfolioId);
      },
      { token: emptyUserToken, portfolioId: emptyPortfolioId }
    );
    await sharedPage.goto('/dashboard/trades');
  });

  test.afterAll(async () => {
    // Close the shared browser before deleting the user so no in-flight
    // requests race against the DELETE.
    if (sharedBrowser) await sharedBrowser.close();

    // Delete the empty test user and all their data
    if (emptyUserToken) {
      await fetch(`${API_URL}/api/v1/users/me`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${emptyUserToken}` },
      });
    }
  });

  test('TC-058 empty state message is shown when user has no trades', async () => {
    await expect(
      sharedPage.getByText('No trades found. Import trades to get started.').filter({ visible: true })
    ).toBeVisible({ timeout: 15_000 });
  });

  test('TC-059 pagination buttons are not shown in empty state', async () => {
    const prevBtn = sharedPage.getByRole('button', { name: 'Previous' });
    const nextBtn = sharedPage.getByRole('button', { name: 'Next', exact: true });

    await expect(prevBtn).toBeHidden({ timeout: 10_000 });
    await expect(nextBtn).toBeHidden({ timeout: 10_000 });
  });
});

tradeMobileTest.describe('@trade-mobile-layout mobile list', () => {
  tradeMobileTest.use({ viewport: { width: 375, height: 812 }, storageState: { cookies: [], origins: [] } });
  tradeMobileTest.setTimeout(90_000);

  tradeMobileTest('cards support sort, selection, live filter sheet and detail navigation', async ({ page, tradeMobile }) => {
    for (let index = 0; index < 9; index++) await tradeMobile.createTrade(`NAV${String(index).padStart(2, '0')}`);
    await page.goto('/dashboard/trades?opened_at_from=2000-01-01&limit=10&sort_by=symbol&sort_dir=asc');
    const cards = page.getByTestId('trade-card-list');
    await expect(cards.locator('article')).toHaveCount(10);
    await expect(page.locator('table')).toBeHidden();
    const sort = page.getByRole('combobox', { name: 'Sort trades' });
    await expect(sort).toHaveValue('symbol:asc');
    await expect(sort.locator('option')).toHaveCount(8);
    await expectNoTradeOverflow(page);
    await page.setViewportSize({ width: 768, height: 1024 });
    await expectNoTradeOverflow(page);
    await page.setViewportSize({ width: 375, height: 812 });

    await page.getByRole('button', { name: 'Next ›', exact: true }).click();
    await expect(page.getByText('Page 2', { exact: true }).filter({ visible: true })).toBeVisible();
    const sortedResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname.includes('/api/v1/portfolios/') && url.pathname.endsWith('/trades') &&
        url.searchParams.get('sort_by') === 'pnl' && url.searchParams.get('sort_dir') === 'desc' && !url.searchParams.has('cursor');
    });
    await sort.selectOption({ label: 'P&L: highest' });
    const response = await sortedResponse;
    expect(response.ok()).toBeTruthy();
    const sorted = z.object({ data: z.object({ items: z.array(z.object({ id: z.string(), pnl: z.string().nullable() })) }) }).parse(await response.json()).data.items;
    const pnls = sorted.flatMap((trade) => trade.pnl === null ? [] : [Number(trade.pnl)]);
    expect(pnls).toEqual([...pnls].sort((a, b) => b - a));
    await expect.poll(() => cards.getByRole('link').evaluateAll((links) => links.map((link) => link.getAttribute('href'))))
      .toEqual(sorted.map((trade) => `/dashboard/trades/${trade.id}`));
    await expect(page).toHaveURL(/sort_by=pnl&sort_dir=desc/);
    await expect(page.getByText('Page 1', { exact: true }).filter({ visible: true })).toBeVisible();
    await expect(page.getByRole('button', { name: '‹ Prev', exact: true })).toBeDisabled();

    const listUrl = page.url();
    await page.getByRole('button', { name: 'Select', exact: true }).click();
    await cards.getByRole('link').nth(0).click();
    const bar = page.getByRole('toolbar', { name: 'Selected trade actions' });
    await expect(bar.locator('p')).toHaveText('1 selected');
    await expect(bar.getByRole('button', { name: 'Merge', exact: true })).toHaveCount(0);
    await cards.getByRole('link').nth(1).click();
    await expect(bar.locator('p')).toHaveText('2 selected');
    for (const name of ['Merge', 'Playbook', 'Tags', 'Delete']) await expect(bar.getByRole('button', { name, exact: true })).toBeVisible();
    await expect(page).toHaveURL(listUrl);
    const box = await bar.boundingBox();
    if (!box) throw new Error('Mobile bulk bar is not rendered.');
    expect(box.y + box.height).toBeCloseTo(812, 0);
    expect(box.width).toBeCloseTo(375, 0);
    await bar.getByRole('button', { name: 'Playbook', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Assign Playbook', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    await page.getByRole('button', { name: 'Done', exact: true }).click();
    await expect(bar).toBeHidden();
    await expect(cards.getByRole('checkbox')).toHaveCount(0);

    await page.getByTestId('trade-mobile-filter-toolbar').getByRole('button', { name: /^Filter/ }).click();
    const sheet = page.getByRole('dialog', { name: 'Filters', exact: true });
    await sheet.getByRole('radio', { name: 'Winners', exact: true }).check();
    await expect(page).toHaveURL(/pnl_positive=true/);
    await expect(sheet.getByRole('tab', { name: 'Trade 1', exact: true })).toBeVisible();
    await sheet.getByRole('tab', { name: /^Time/ }).click();
    await expect(sheet.getByLabel('Opened From', { exact: true })).toHaveValue('2000-01-01');
    await sheet.getByRole('tab', { name: 'Journal', exact: true }).click();
    await expect(sheet.getByRole('combobox', { name: 'Playbook', exact: true })).toBeVisible();
    await sheet.getByRole('tab', { name: 'Account', exact: true }).click();
    await sheet.getByRole('button', { name: 'Account', exact: true }).click();
    await expect(sheet.getByRole('button', { name: 'Browser IBKR', exact: true })).toBeInViewport();
    await expectNoTradeOverflow(page);
    await sheet.getByRole('button', { name: 'Clear all', exact: true }).press('Enter');
    for (const name of ['Trade', 'Time', 'Journal', 'Account']) await expect(sheet.getByRole('tab', { name, exact: true })).toBeVisible();
    await expect(sheet.getByRole('button', { name: 'Save View', exact: true })).toBeVisible();
    await expect(page).not.toHaveURL(/pnl_positive=|opened_at_from=/);
    await sheet.getByRole('button', { name: 'Show results', exact: true }).click();
    await expect(sheet).toBeHidden();
    const href = await cards.getByRole('link').first().getAttribute('href');
    if (!href) throw new Error('Mobile card has no detail link.');
    await cards.locator('article').first().click();
    await expect(page).toHaveURL(href);
    await expect(page.getByRole('button', { name: 'Next trade', exact: true })).toBeVisible();
    await expectNoTradeOverflow(page);
  });
});

for (const viewport of [{ width: 375, height: 812 }, { width: 1440, height: 900 }]) {
  tradeMobileTest.describe(`@trade-mobile-layout navigation at ${viewport.width}px`, () => {
    tradeMobileTest.use({ viewport, storageState: { cookies: [], origins: [] } });
    tradeMobileTest.setTimeout(90_000);

    tradeMobileTest('crosses a page boundary and restores the filtered list', async ({ page, tradeMobile }) => {
      const trades = [...tradeMobile.trades];
      for (let index = 0; index < 9; index++) trades.push(await tradeMobile.createTrade(`NAV${String(index).padStart(2, '0')}`));
      const ordered = trades.sort((a, b) => a.symbol.localeCompare(b.symbol));
      const query = 'direction=LONG&sort_by=symbol&sort_dir=asc&limit=10';
      await page.goto(`/dashboard/trades?${query}`);
      const list = viewport.width < 1024 ? page.getByTestId('trade-card-list') : page.locator('table');
      await list.getByRole('link', { name: ordered[9].symbol, exact: true }).click();
      await expect(page.getByRole('button', { name: 'Next trade', exact: true })).toBeEnabled();
      const context: unknown = await page.evaluate(() => JSON.parse(sessionStorage.getItem('tradesensei.tradeListContext') ?? 'null'));
      const cursor = z.object({ pages: z.array(z.object({ nextCursor: z.string().nullable() })) }).parse(context).pages.at(-1)?.nextCursor;
      if (!cursor) throw new Error('Stored list context has no next-page cursor.');
      const boundaryRequest = page.waitForRequest((request) => {
        const url = new URL(request.url());
        return request.method() === 'GET' && url.pathname.includes('/api/v1/portfolios/') && url.pathname.endsWith('/trades');
      });
      if (viewport.width < 1024) await page.getByRole('button', { name: 'Next trade', exact: true }).click();
      else await page.keyboard.press('ArrowRight');
      const params = new URL((await boundaryRequest).url()).searchParams;
      expect(Object.fromEntries(['direction', 'sort_by', 'sort_dir', 'limit', 'cursor'].map((key) => [key, params.get(key)])))
        .toEqual({ direction: 'LONG', sort_by: 'symbol', sort_dir: 'asc', limit: '10', cursor });
      await expect(page).toHaveURL(`/dashboard/trades/${ordered[10].id}`);
      await expect(page.getByRole('heading', { name: ordered[10].symbol, exact: true })).toBeVisible();
      await expect(page.getByTitle(/^Position in your filtered trade list/).filter({ visible: true })).toHaveText(/^11 \/ /);
      let previousPageRequests = 0;
      page.on('request', (request) => {
        const url = new URL(request.url());
        if (url.pathname.includes('/api/v1/portfolios/') && url.pathname.endsWith('/trades')) previousPageRequests++;
      });
      await page.getByRole('button', { name: 'Previous trade', exact: true }).click();
      await expect(page).toHaveURL(`/dashboard/trades/${ordered[9].id}`);
      await expect(page.getByRole('heading', { name: ordered[9].symbol, exact: true })).toBeVisible();
      expect(previousPageRequests).toBe(0);
      await page.getByRole('link', { name: 'Back to Trades', exact: true }).click();
      await expect.poll(() => new URL(page.url()).searchParams.get('direction')).toBe('LONG');
      await expect.poll(() => new URL(page.url()).searchParams.get('sort_by')).toBe('symbol');
      await expect.poll(() => new URL(page.url()).searchParams.get('limit')).toBe('10');
      await expect(list.getByRole('link', { name: ordered[0].symbol, exact: true })).toBeVisible();

      await page.addInitScript(() => sessionStorage.removeItem('tradesensei.tradeListContext'));
      await page.goto(`/dashboard/trades/${ordered[0].id}`);
      await expect(page.getByRole('heading', { name: ordered[0].symbol, exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Next trade', exact: true })).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Previous trade', exact: true })).toHaveCount(0);
    });
  });
}
