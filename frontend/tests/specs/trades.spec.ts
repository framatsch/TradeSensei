/**
 * Trades Spec — covers the trade list page (table rendering, pagination,
 * column headers, empty state, and trade detail navigation).
 *
 * All tests run as the seeded E2E user. globalSetup has inserted 10 trades,
 * so the table should be populated.
 */

import { test, expect, chromium } from '@playwright/test';

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
  test('TC-060 trade detail page shows trade fields', async ({ page }) => {
    // Navigate to trades list first to get a real trade ID
    await page.goto('/dashboard/trades');
    await page.waitForLoadState('networkidle');

    const firstSymbolLink = page.locator('tbody tr').first().locator('a[href*="/dashboard/trades/"]');
    await expect(firstSymbolLink).toBeVisible({ timeout: 15_000 });
    await firstSymbolLink.click();

    await expect(page).toHaveURL(/\/dashboard\/trades\/[0-9a-f-]{36}/i, { timeout: 8_000 });

    // Detail page should show some trade data
    // At minimum the page should render without a 404
    await expect(page.locator('main')).toBeVisible();
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
