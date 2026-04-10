/**
 * Trades Spec — covers the trade list page (table rendering, pagination,
 * column headers, empty state, and trade detail navigation).
 *
 * All tests run as the seeded E2E user. globalSetup has inserted 10 trades,
 * plus special seeded trades for execution and merge workflow tests.
 */

import { test, expect, chromium } from '@playwright/test';
import seedState from '../.auth/seed-state.json';

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
      'Quantity',
      'Broker',
      'Entry Price',
      'Exit Price',
      'PnL',
      'Opened At',
      'Closed At',
      'Tags',
      'Notes',
    ];
    // Wait for table to be fully loaded
    await page.waitForSelector('thead th', { timeout: 15_000 });
    
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

  test('TC-056 pagination Next button reflects whether more pages exist', async ({
    page,
  }) => {
    // The Next button state depends on whether there are more trades than fit on one page.
    // Because import tests run in parallel and may add trades to the same user,
    // we just verify that the button exists and has a consistent state.
    // When rows visible < 20 (page size), Next must be disabled.
    const nextBtn = page.getByRole('button', { name: 'Next', exact: true });
    await expect(nextBtn).toBeVisible({ timeout: 10_000 });

    const rows = page.locator('tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });
    const count = await rows.count();

    if (count < 20) {
      // All trades fit on one page — Next should be disabled
      await expect(nextBtn).toBeDisabled();
    } else {
      // There are multiple pages — Next may or may not be enabled depending on cursor
      // Just verify the button is present and we can interact with the table
      await expect(nextBtn).toBeVisible();
    }
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
    await page.waitForLoadState('networkidle');

    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Assert main is visible
    await expect(page.locator('main')).toBeVisible();
    // Assert at least one direction badge (LONG or SHORT) is visible
    await expect(
      page.getByText('LONG').or(page.getByText('SHORT')).first()
    ).toBeVisible();
  });

  // ── TC-061: Execution Summary Card content ──
  test('TC-061 execution summary card shows VWAP entry, quantity, total commission', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Assert Execution Summary heading visible
    await expect(page.getByText('Execution Summary')).toBeVisible();
    // Assert VWAP Entry label visible
    await expect(page.getByText('VWAP Entry')).toBeVisible();
    // Assert the entry price ($400.00) appears in the card
    await expect(page.getByText('$400.00')).toBeVisible();
    // Assert Total Quantity label visible
    await expect(page.getByText('Total Quantity')).toBeVisible();
    // Assert total commission ($3.00) visible
    await expect(page.getByText('$3.00')).toBeVisible();
  });

  // ── TC-062: Execution table renders with correct direction badges ──
  test('TC-062 execution table has 2 rows with LONG and SHORT badges', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    // Assert execution table has exactly 2 rows
    const tbodyRows = page.locator('table tbody tr');
    await expect(tbodyRows).toHaveCount(2, { timeout: 10_000 });

    // Assert first row contains LONG badge
    const firstRow = tbodyRows.first();
    await expect(firstRow.getByText('LONG')).toBeVisible();

    // Assert second row contains SHORT badge
    const secondRow = tbodyRows.nth(1);
    await expect(secondRow.getByText('SHORT')).toBeVisible();
  });

  // ── TC-063: Execution dates are in chronological order ──
  test('TC-063 execution dates are in chronological order', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    const tbodyRows = page.locator('table tbody tr');
    await expect(tbodyRows).toHaveCount(2, { timeout: 10_000 });

    // Get date from first row's first cell
    const firstRowDateCell = tbodyRows.first().locator('td').first();
    const firstRowDateText = await firstRowDateCell.textContent();

    // Get date from second row's first cell
    const secondRowDateCell = tbodyRows.nth(1).locator('td').first();
    const secondRowDateText = await secondRowDateCell.textContent();

    // Parse and compare dates
    const d1 = new Date(firstRowDateText || '');
    const d2 = new Date(secondRowDateText || '');
    expect(d1.getTime()).toBeLessThan(d2.getTime());
  });

  // ── TC-064: Add Execution button is visible ──
  test('TC-064 add execution button is visible', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('button', { name: 'Add Execution' })).toBeVisible();
  });

  // ── TC-065: Sidebar performance labels are visible ──
  test('TC-065 sidebar labels gross p&l, net p&l, return %, holding period are visible', async ({ page }) => {
    // Navigate via list
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Assert all four labels visible
    await expect(page.getByText('Gross P&L')).toBeVisible();
    await expect(page.getByText('Net P&L')).toBeVisible();
    await expect(page.getByText('Return %')).toBeVisible();
    await expect(page.getByText('Holding Period')).toBeVisible();
  });

  // ── TC-066: Trade actions menu ──
  test('TC-066 trade actions dropdown shows correct menu items', async ({ page }) => {
    // Navigate via list
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

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
    // Navigate via list to a non-conflicting trade (first row is fine)
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Assert Position Conflict is NOT visible
    await expect(page.getByText('Position Conflict')).not.toBeVisible();
  });
});

test.describe('Add Execution Modal', () => {
  // ── TC-070: Add Execution modal opens with BUY/SELL toggles ──
  test('TC-070 add execution modal opens with toggle and datetime input', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Click the Add Execution button to open modal
    await page.getByRole('button', { name: 'Add Execution' }).click();

    // Assert modal heading visible
    await expect(page.getByRole('heading', { name: 'Add Execution' })).toBeVisible();
    // Assert BUY toggle visible
    await expect(page.getByRole('button', { name: 'BUY' })).toBeVisible();
    // Assert SELL toggle visible
    await expect(page.getByRole('button', { name: 'SELL' })).toBeVisible();
    // Assert datetime-local input visible
    await expect(page.locator('input[type="datetime-local"]')).toBeVisible();
  });

  // ── TC-071: Successfully add execution increases table row count ──
  test('TC-071 adding execution with quantity and price increases table rows', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    // Get initial row count
    let tbodyRows = page.locator('table tbody tr');
    const initialCount = await tbodyRows.count();
    expect(initialCount).toBe(2); // Should be 2 from seeding

    // Click Add Execution button
    await page.getByRole('button', { name: 'Add Execution' }).click();

    // Wait for modal to appear
    await expect(page.getByRole('heading', { name: 'Add Execution' })).toBeVisible({ timeout: 10_000 });

    // Fill in quantity field
    await page.locator('input[type="number"]').first().fill('10');
    // Fill in price field (assuming second number input or a dedicated price input)
    const numberInputs = page.locator('input[type="number"]');
    await numberInputs.nth(1).fill('410.00');

    // Click submit button in modal (use .last() to get the submit button, not the trigger)
    await page.getByRole('button', { name: 'Add Execution' }).last().click();

    // Wait for modal to close
    await expect(page.getByRole('heading', { name: 'Add Execution' })).not.toBeVisible({ timeout: 10_000 });

    // Wait for table to update
    await page.waitForTimeout(1000);

    // Assert row count increased to 3
    tbodyRows = page.locator('table tbody tr');
    await expect(tbodyRows).toHaveCount(3, { timeout: 10_000 });
  });

  // ── TC-072: Validation error on quantity 0 ──
  test('TC-072 validation error shown when quantity is 0', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Wait for execution table to load
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });

    // Click Add Execution button
    await page.getByRole('button', { name: 'Add Execution' }).click();

    // Wait for modal to appear
    await expect(page.getByRole('heading', { name: 'Add Execution' })).toBeVisible({ timeout: 10_000 });

    // Set quantity to 0
    const quantityInput = page.locator('input[type="number"]').first();
    await quantityInput.fill('0');

    // Click submit button
    await page.getByRole('button', { name: 'Add Execution' }).last().click();

    // Assert error message visible
    await expect(page.getByText('Quantity must be greater than 0.')).toBeVisible({ timeout: 10_000 });
    // Assert modal is still open
    await expect(page.getByRole('heading', { name: 'Add Execution' })).toBeVisible();
  });
});

test.describe('Inline Sidebar Editing', () => {
  // ── TC-075: Inline edit Stop Loss ──
  test('TC-075 inline edit stop loss value', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Find Stop Loss section and click the value button to enter edit mode
    const stopLossLabel = page.getByText('Stop Loss');
    const stopLossContainer = stopLossLabel.locator('..');

    // Click on the value area to enter edit mode
    await stopLossContainer.locator('button').first().click();

    // Wait for input to appear
    const numberInput = page.locator('input[type="number"]').first();
    await expect(numberInput).toBeVisible({ timeout: 10_000 });

    // Type the new value
    await numberInput.fill('150.00');

    // Click save button
    await page.locator('button[title="Save"]').first().click();

    // Wait for input to disappear and value to appear
    await expect(numberInput).not.toBeVisible();

    // Assert the new value appears in Stop Loss area
    await expect(page.getByText('$150.00')).toBeVisible();
  });

  // ── TC-076: Inline edit Playbook ──
  test('TC-076 inline edit playbook field', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Click on playbook field (has title "Click to change playbook")
    await page.getByTitle('Click to change playbook').click();

    // Wait for dropdown to appear
    await expect(page.getByText('Breakout')).toBeVisible();

    // Click Breakout option
    await page.getByText('Breakout').click();

    // Assert the field now shows Breakout
    await expect(page.getByTitle('Click to change playbook')).toContainText('Breakout');
  });

  // ── TC-077: Inline edit Tags ──
  test('TC-077 inline edit tags in playbook psychology card', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Find Tags section in PlaybookPsychologyCard and click to open tag picker
    const tagsLabel = page.getByText('Tags');
    const tagsContainer = tagsLabel.locator('..');

    // Click on tags edit area
    await tagsContainer.click();

    // Wait for tag picker with high-conviction tag
    await expect(page.getByText('high-conviction')).toBeVisible({ timeout: 10_000 });

    // Click the high-conviction tag
    await page.getByText('high-conviction').click();

    // Assert the tag appears as selected (visible in the card)
    await expect(page.getByText('high-conviction')).toBeVisible();
  });
});

test.describe('Merge Workflow', () => {
  // ── TC-080: Select two trades and Merge button appears ──
  test('TC-080 selecting two trades shows merge button in toolbar', async ({ page }) => {
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

    // Wait for table rows to load
    await page.waitForSelector('tbody tr', { timeout: 15_000 });

    const [tradeId1, tradeId2] = seedState.mergeTradeIds;

    // Find and check checkbox for first merge trade
    const checkbox1 = page.locator(`tr:has-text("${tradeId1}") input[type="checkbox"]`);
    await expect(checkbox1).toBeVisible({ timeout: 10_000 });
    await checkbox1.click();

    // Find and check checkbox for second merge trade
    const checkbox2 = page.locator(`tr:has-text("${tradeId2}") input[type="checkbox"]`);
    await expect(checkbox2).toBeVisible({ timeout: 10_000 });
    await checkbox2.click();

    // Assert Merge button appears in toolbar
    await expect(page.getByRole('button', { name: 'Merge' })).toBeVisible({ timeout: 10_000 });
  });

  // ── TC-081: Merge button opens preview modal ──
  test('TC-081 merge button opens preview modal with combined info', async ({ page }) => {
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

    // Wait for table rows to load
    await page.waitForSelector('tbody tr', { timeout: 15_000 });

    const [tradeId1, tradeId2] = seedState.mergeTradeIds;

    // Check both trade checkboxes
    const checkbox1 = page.locator(`tr:has-text("${tradeId1}") input[type="checkbox"]`);
    await expect(checkbox1).toBeVisible({ timeout: 10_000 });
    await checkbox1.click();

    const checkbox2 = page.locator(`tr:has-text("${tradeId2}") input[type="checkbox"]`);
    await expect(checkbox2).toBeVisible({ timeout: 10_000 });
    await checkbox2.click();

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
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

    // Wait for table rows to load
    await page.waitForSelector('tbody tr', { timeout: 15_000 });

    const [tradeId1, tradeId2] = seedState.mergeTradeIds;

    // Check both trade checkboxes
    const checkbox1 = page.locator(`tr:has-text("${tradeId1}") input[type="checkbox"]`);
    await expect(checkbox1).toBeVisible({ timeout: 10_000 });
    await checkbox1.click();

    const checkbox2 = page.locator(`tr:has-text("${tradeId2}") input[type="checkbox"]`);
    await expect(checkbox2).toBeVisible({ timeout: 10_000 });
    await checkbox2.click();

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
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Wait for execution table rows
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });
    const tbodyRows = page.locator('table tbody tr');
    await expect(tbodyRows.first()).toBeVisible({ timeout: 10_000 });

    // Click overflow menu button in first execution row
    await tbodyRows.first().locator('button').last().click();

    // Assert dropdown shows all options
    await expect(page.getByText('Edit')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Move to...')).toBeVisible();
    await expect(page.getByText('Detach as new Trade')).toBeVisible();
    await expect(page.getByText('Delete')).toBeVisible();
  });

  // ── TC-086: Detach execution decreases table row count ──
  test('TC-086 detaching execution removes row from table', async ({ page }) => {
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');

    // Wait for Execution Summary Card to appear first (indicates page is loaded)
    await expect(page.getByText('Execution Summary')).toBeVisible({ timeout: 15_000 });

    // Wait for execution table rows
    await page.waitForSelector('table tbody tr', { timeout: 15_000 });
    let tbodyRows = page.locator('table tbody tr');
    await expect(tbodyRows.first()).toBeVisible({ timeout: 10_000 });
    const initialCount = await tbodyRows.count();

    // Set up dialog handler before clicking
    page.on('dialog', (d) => d.accept());

    // Click overflow menu button in first execution row
    tbodyRows = page.locator('table tbody tr');
    await tbodyRows.first().locator('button').last().click();

    // Click Detach as new Trade
    await page.getByText('Detach as new Trade').click();

    // Wait for confirmation dialog to be handled and table to update
    await page.waitForTimeout(1000);

    // Assert table row count decreased by 1
    tbodyRows = page.locator('table tbody tr');
    await expect(tbodyRows).toHaveCount(initialCount - 1, { timeout: 10_000 });
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

    // Launch one shared browser + context, inject the token once.
    sharedBrowser = await chromium.launch({ headless: true });
    const context = await sharedBrowser.newContext({ baseURL: BASE_URL });
    sharedPage = await context.newPage();

    await sharedPage.goto('/dashboard/trades');
    await sharedPage.evaluate(
      (token) => localStorage.setItem('access_token', token),
      emptyUserToken
    );
    await sharedPage.goto('/dashboard/trades');
    await sharedPage.waitForLoadState('networkidle');
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
      sharedPage.getByText('No trades found. Import trades to get started.')
    ).toBeVisible({ timeout: 15_000 });
  });

  test('TC-059 pagination buttons are both disabled in empty state', async () => {
    const prevBtn = sharedPage.getByRole('button', { name: 'Previous' });
    const nextBtn = sharedPage.getByRole('button', { name: 'Next', exact: true });

    await expect(prevBtn).toBeVisible({ timeout: 10_000 });
    await expect(nextBtn).toBeVisible({ timeout: 10_000 });
    await expect(prevBtn).toBeDisabled();
    await expect(nextBtn).toBeDisabled();
  });
});
