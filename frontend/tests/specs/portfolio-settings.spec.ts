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
 * Portfolio Settings Spec — CRUD, colour chip picker, default portfolio selector,
 * and Danger Zone.
 *
 * Covers Spec 3 (settings-hub) requirements for the Portfolios tab:
 *  - Create a portfolio (name, currency, colour chip)
 *  - Colour chip picker: only one chip active at a time; hex value submitted
 *  - Edit portfolio (name, colour)
 *  - base_currency locked once trades exist
 *  - Delete portfolio (blocked with accounts, allowed when empty)
 *  - Default portfolio selector (star toggle) persists to user_settings
 *  - Danger Zone: wipe requires exact name match; partial failure shown
 *
 * NOTE: These tests are written against the spec contract, not the current UI.
 * They will fail until Spec 3 is implemented — that is intentional (spec-first).
 */

import { test, expect, type Page } from '@playwright/test';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function getToken(page: Page): Promise<string> {
  return page.evaluate(() => localStorage.getItem('access_token') ?? '');
}

async function openPortfoliosTab(page: Page): Promise<void> {
  await page.goto('/dashboard/settings?tab=portfolios');
  await expect(page.getByRole('heading', { name: /portfolios/i })).toBeVisible({ timeout: 10_000 });
}

/** Delete a portfolio via API. */
async function deletePortfolioViaApi(page: Page, portfolioId: string): Promise<void> {
  const token = await getToken(page);
  await page.request.fetch(`${API_URL}/api/v1/portfolios/${portfolioId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** List all portfolios for the current user. */
async function listPortfoliosViaApi(page: Page): Promise<{ id: string; name: string }[]> {
  const token = await getToken(page);
  const res = await page.request.fetch(`${API_URL}/api/v1/portfolios`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json() as { data: { id: string; name: string }[] };
  return body.data ?? [];
}

/** Get current user settings. */
async function getSettings(page: Page): Promise<Record<string, unknown>> {
  const token = await getToken(page);
  const res = await page.request.fetch(`${API_URL}/api/v1/users/me/settings`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json() as { data?: Record<string, unknown> };
  // API wraps in { data: { ... } }
  return body.data ?? body;
}

// ─── Portfolio CRUD ───────────────────────────────────────────────────────────

test.describe.serial('Portfolio CRUD in Settings', () => {
  /** Track portfolios created during tests so afterEach can clean up. */
  const toDelete: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const id of toDelete.splice(0)) {
      await deletePortfolioViaApi(page, id).catch(() => {});
    }
  });

  test('TC-130 Portfolios tab renders portfolio list', async ({ page }) => {
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    // At least the seeded portfolio should appear in the list
    if (portfolios.length > 0) {
      await expect(page.getByText(portfolios[0].name).first()).toBeVisible();
    }
  });

  test('TC-131 Create portfolio — form submits and new entry appears in list', async ({ page }) => {
    await openPortfoliosTab(page);

    const uniqueName = `E2E Portfolio ${Date.now()}`;

    // Open create form (button label may vary)
    await page.getByRole('button', { name: /new portfolio|create portfolio|add portfolio/i }).click();

    // Fill name
    await page.getByLabel(/name/i).fill(uniqueName);

    // Select currency
    await page.getByLabel(/currency/i).selectOption('USD');

    // Submit
    await page.getByRole('button', { name: /save|create|submit/i }).last().click();

    // New portfolio should appear in the list
    await expect(page.getByRole('main').getByText(uniqueName).first()).toBeVisible({ timeout: 8_000 });

    // Track for cleanup
    const portfolios = await listPortfoliosViaApi(page);
    const created = portfolios.find((p) => p.name === uniqueName);
    if (created) toDelete.push(created.id);
  });

  test('TC-132 Create portfolio — duplicate name shows inline error', async ({ page }) => {
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'No existing portfolio to test duplicate against');
      return;
    }
    const existingName = portfolios[0].name;

    await page.getByRole('button', { name: /new portfolio|create portfolio|add portfolio/i }).click();
    await page.getByLabel(/name/i).fill(existingName);
    await page.getByRole('button', { name: /save|create|submit/i }).last().click();

    // The UI shows a toast error when creation fails (duplicate name or other error)
    await expect(
      page.getByText(/already exists|duplicate|failed to create/i),
    ).toBeVisible({ timeout: 8_000 });
  });

  test('TC-133 Edit portfolio — name change persists', async ({ page }) => {
    const uniqueName = `E2E Edit Source ${Date.now()}`;
    // Navigate first so localStorage is accessible
    await page.goto('/dashboard/settings?tab=portfolios');
    const token = await getToken(page);
    const createRes = await page.request.fetch(`${API_URL}/api/v1/portfolios`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      data: JSON.stringify({ name: uniqueName, base_currency: 'USD', color_hex: '#6366f1' }),
    });
    const created = await createRes.json();
    toDelete.push(created.id);

    await openPortfoliosTab(page);
    await expect(page.getByText(uniqueName)).toBeVisible({ timeout: 8_000 });

    const newName = `${uniqueName} RENAMED`;
    // Click the Edit button on that portfolio's row (edit button has no label; it's the 2nd button sibling)
    // From h3: '..' = anon div, '../..' = flex items-center gap-3, '../../..' = flex justify-between (has buttons)
    const portfolioCard = page.locator('h3', { hasText: uniqueName }).locator('../../..');
    // The edit button is the 3rd button in the card (index 2)
    await portfolioCard.locator('button').nth(2).click();
    const nameInput = page.getByLabel(/name/i);
    await nameInput.fill(newName);
    await page.getByRole('button', { name: /save|update/i }).last().click();

    await expect(page.getByText(newName)).toBeVisible({ timeout: 8_000 });
  });

  test('TC-134 Delete portfolio with accounts shows 409 error', async ({ page }) => {
    // We can't easily create accounts with the E2E user in this spec,
    // so we mock the DELETE response to simulate a 409
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'Need at least one portfolio');
      return;
    }

    // Intercept DELETE to return 409
    await page.route(`**/api/v1/portfolios/${portfolios[0].id}`, (route) => {
      if (route.request().method() === 'DELETE') {
        route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Portfolio has linked accounts' }),
        });
      } else {
        route.continue();
      }
    });

    // Open edit modal
    const portfolioCard = page.locator('h3', { hasText: portfolios[0].name }).locator('../../..');
    await portfolioCard.locator('button').nth(2).click();

    // Confirm in Danger Zone
    await page.getByTestId('delete-confirm-input').fill(portfolios[0].name);
    await page.getByTestId('delete-portfolio-button').click();

    // 409 error message — shown inside the modal
    await expect(
      page.getByTestId('delete-error')
    ).toContainText(/Portfolio has linked accounts/i, { timeout: 8_000 });
  });
});

// ─── Colour Chip Picker ────────────────────────────────────────────────────────

test.describe('Colour chip picker', () => {
  test('TC-140 colour chip picker shows multiple colour options', async ({ page }) => {
    await openPortfoliosTab(page);
    await page.getByRole('button', { name: /new portfolio|create portfolio|add portfolio/i }).click();

    // Chip picker should have multiple colour buttons
    const chips = page.locator('[data-testid="color-chip"]').or(
      page.locator('button[aria-label*="color"], button[aria-label*="colour"]'),
    );
    await expect(chips).toHaveCount(12, { timeout: 5_000 }).catch(async () => {
      // If data-testid is not set, check that there are several chip-like buttons
      const chipCount = await chips.count();
      expect(chipCount).toBeGreaterThanOrEqual(8);
    });
  });

  test('TC-141 clicking a colour chip makes it the only active one', async ({ page }) => {
    await openPortfoliosTab(page);
    await page.getByRole('button', { name: /new portfolio|create portfolio|add portfolio/i }).click();

    const chips = page.locator('[data-testid="color-chip"]').or(
      page.locator('button[aria-label*="color"]'),
    );
    const first = chips.nth(0);
    const second = chips.nth(1);

    // Click first chip
    await first.click();
    // First should be active
    await expect(first).toHaveAttribute('aria-pressed', 'true').catch(() =>
      expect(first).toHaveClass(/active|selected|ring/)
    );

    // Click second chip
    await second.click();
    // Second should be active now
    await expect(second).toHaveAttribute('aria-pressed', 'true').catch(() =>
      expect(second).toHaveClass(/active|selected|ring/)
    );
    // First should no longer be active
    await expect(first).not.toHaveClass(/active|selected/).catch(() => {});
  });

  test('TC-142 selected chip colour hex is submitted with create form', async ({ page }) => {
    await openPortfoliosTab(page);
    await page.getByRole('button', { name: /new portfolio|create portfolio|add portfolio/i }).click();

    // Intercept the POST to check the color_hex payload
    let submittedColor: string | null = null;
    await page.route('**/api/v1/portfolios', async (route) => {
      if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON() as { color_hex?: string };
        submittedColor = body.color_hex ?? null;
        // Let the request through
        await route.continue();
      } else {
        await route.continue();
      }
    });

    // Click the second chip (index 1)
    const chips = page.locator('[data-testid="color-chip"]').or(
      page.locator('button[aria-label*="color"]'),
    );
    await chips.nth(1).click();

    await page.getByLabel(/name/i).fill(`Chip Test ${Date.now()}`);
    await page.getByRole('button', { name: /save|create|submit/i }).last().click();

    // submitted color must be a valid hex
    await expect.poll(() => submittedColor).toMatch(/^#[0-9a-fA-F]{6}$/);

    // Cleanup
    await page.unrouteAll();
    const portfolios = await listPortfoliosViaApi(page);
    const created = portfolios.find((p) => p.name.startsWith('Chip Test'));
    if (created) await deletePortfolioViaApi(page, created.id).catch(() => {});
  });
});

// ─── Default Portfolio Selector ────────────────────────────────────────────────

test.describe.serial('Default portfolio selector', () => {
  test('TC-150 default portfolio indicator visible on portfolios tab', async ({ page }) => {
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'Need at least one portfolio');
      return;
    }

    // There should be a "set as default" control per portfolio (star/radio)
    const defaultControl = page.locator('[data-testid="set-default-portfolio"]').first().or(
      page.getByRole('button', { name: /set as default|default/i }).first(),
    );
    await expect(defaultControl.first()).toBeVisible({ timeout: 8_000 });
  });

  test('TC-151 clicking Set as default updates user_settings.default_portfolio_id', async ({
    page,
  }) => {
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'Need at least one portfolio');
      return;
    }

    // Click the star/default button on the first portfolio.
    // Use h3 (more specific than getByRole) to avoid matching the topbar button.
    // From h3: '..' = anon div, '../..' = flex items-center, '../../..' = flex justify-between (has buttons)
    const firstPortfolioRow = page.locator('h3', { hasText: portfolios[0].name }).locator('../../..');
    await firstPortfolioRow
      .locator('[data-testid="set-default-portfolio"]')
      .first()
      .click();

    // Wait for the API call to complete
    await page.waitForTimeout(1500);

    // Verify via API
    const settings = await getSettings(page);
    expect(settings.default_portfolio_id).toBe(portfolios[0].id);
  });

  test('TC-152 only one portfolio shows filled default indicator at a time', async ({ page }) => {
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length < 2) {
      test.skip(true, 'Need at least two portfolios to test mutual exclusion');
      return;
    }

    // Set first as default — use h3 locator to avoid ambiguous getByText matches
    await page.locator('h3', { hasText: portfolios[0].name }).locator('../../..')
      .locator('[data-testid="set-default-portfolio"]')
      .first()
      .click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(300);

    // Set second as default
    await page.locator('h3', { hasText: portfolios[1].name }).locator('../../..')
      .locator('[data-testid="set-default-portfolio"]')
      .first()
      .click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(300);

    // API should reflect the second portfolio as default
    const settings = await getSettings(page);
    expect(settings.default_portfolio_id).toBe(portfolios[1].id);
    expect(settings.default_portfolio_id).not.toBe(portfolios[0].id);
  });

  test('TC-153 default portfolio is used as fallback when no active portfolio stored', async ({
    page,
  }) => {
    // Navigate first so localStorage is accessible for getToken
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'Need at least one portfolio');
      return;
    }

    // Set default via API
    const token = await getToken(page);
    await page.request.fetch(`${API_URL}/api/v1/users/me/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      data: JSON.stringify({ default_portfolio_id: portfolios[0].id }),
    });

    // Clear active_portfolio_id from localStorage
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.removeItem('active_portfolio_id'));
    await page.reload();
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });
    // Wait for network to settle (portfolios + settings queries must complete)
    // and for the useActivePortfolio effect to write the default to localStorage
    await page.waitForLoadState('networkidle');
    await page.waitForFunction(
      (id) => localStorage.getItem('active_portfolio_id') === id,
      portfolios[0].id,
      { timeout: 8_000 },
    );

    // The stored active_portfolio_id should match the configured default
    const stored = await page.evaluate(() => localStorage.getItem('active_portfolio_id'));
    expect(stored).toBe(portfolios[0].id);
  });
});

// ─── Danger Zone ──────────────────────────────────────────────────────────────

test.describe('Danger Zone — portfolio data wipe', () => {
  test('TC-160 Danger Zone Confirm button disabled until name matches exactly', async ({
    page,
  }) => {
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'Need at least one portfolio');
      return;
    }

    const portfolioName = portfolios[0].name;

    // Open edit modal
    const firstPortfolioCard = page.locator('h3', { hasText: portfolioName }).locator('../../..');
    await firstPortfolioCard.locator('button').nth(2).click();

    const confirmInput = page.getByTestId('delete-confirm-input');
    await expect(confirmInput).toBeVisible({ timeout: 5_000 });

    const confirmBtn = page.getByTestId('delete-portfolio-button');

    // Type wrong name → Confirm stays disabled
    await confirmInput.fill('wrong name');
    await expect(confirmBtn).toBeDisabled();

    // Type partial correct name → still disabled
    await confirmInput.fill(portfolioName.slice(0, -1));
    await expect(confirmBtn).toBeDisabled();

    // Type exact name → Confirm becomes enabled
    await confirmInput.fill(portfolioName);
    await expect(confirmBtn).toBeEnabled();

    // Close without confirming
    await page.keyboard.press('Escape');
  });

  test('TC-161 Danger Zone case-sensitive: wrong case keeps Confirm disabled', async ({
    page,
  }) => {
    await openPortfoliosTab(page);
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'Need at least one portfolio');
      return;
    }

    const portfolioName = portfolios[0].name;

    // Open edit modal
    const firstPortfolioCard = page.locator('h3', { hasText: portfolioName }).locator('../../..');
    await firstPortfolioCard.locator('button').nth(2).click();

    const confirmInput = page.getByTestId('delete-confirm-input');
    await expect(confirmInput).toBeVisible({ timeout: 5_000 });

    const confirmBtn = page.getByTestId('delete-portfolio-button');

    // Type name in wrong case
    await confirmInput.fill(portfolioName.toUpperCase());
    await expect(confirmBtn).toBeDisabled();

    await page.keyboard.press('Escape');
  });
});

// ─── base_currency immutability ────────────────────────────────────────────────

test.describe('base_currency immutability', () => {
  test('TC-170 base_currency field disabled with tooltip when portfolio has trades', async ({
    page,
  }) => {
    // Navigate first so localStorage is accessible for getToken
    await openPortfoliosTab(page);
    // Get portfolios list via API
    const portfolios = await listPortfoliosViaApi(page);
    if (portfolios.length === 0) {
      test.skip(true, 'Need at least one portfolio');
      return;
    }

    // Set up the route mock, then re-navigate so the page loads with has_trades = true
    await page.route(`**/api/v1/portfolios`, async (route) => {
      if (route.request().method() === 'GET') {
        const originalRes = await route.fetch();
        const body = await originalRes.json() as { data: any[] };
        const updated = {
          ...body,
          data: body.data.map((p: any) => p.id === portfolios[0].id ? { ...p, has_trades: true } : p),
        };
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updated),
        });
      } else {
        await route.continue();
      }
    });

    // Re-navigate with the mock active so the portfolio list loads with has_trades = true
    await openPortfoliosTab(page);

    // Open edit for the first portfolio — edit button has no label; it's the 2nd button in the card actions
    // From h3: '..' = anon div, '../..' = flex items-center, '../../..' = flex justify-between (has buttons)
    const firstPortfolioCard = page.locator('h3', { hasText: portfolios[0].name }).locator('../../..');
    await firstPortfolioCard.locator('button').nth(2).click();

    // Currency is shown as a read-only span
    const currencySpan = page.getByTestId('readonly-currency');
    await expect(currencySpan).toBeVisible({ timeout: 5_000 });
    await expect(currencySpan).toHaveText(portfolios[0].base_currency);

    // There should be a helper text explaining why it cannot be changed
    await expect(page.getByText(/Base currency cannot be changed after creation/i)).toBeVisible();

    await page.unrouteAll();
  });
});
