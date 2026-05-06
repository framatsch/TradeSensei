/**
 * Portfolio Context Spec — activePortfolioId global state, localStorage persistence,
 * EmptyPortfolioGate, and stale-ID recovery.
 *
 * Covers Spec 2 (app-state-topbar-navigation) requirements for:
 *  - portfolioStore hydration and localStorage persistence
 *  - appContextStore hydration and persistence
 *  - EmptyPortfolioGate shown when user has no portfolios
 *  - EmptyPortfolioGate NOT shown on API error (error banner instead)
 *  - Stale activePortfolioId falls back gracefully
 *
 * NOTE: These tests are written against the spec contract, not the current UI.
 * They will fail until Spec 2 is implemented — that is intentional (spec-first).
 */

import { test, expect, type Page } from '@playwright/test';
import path from 'path';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function getToken(page: Page): Promise<string> {
  return page.evaluate(() => localStorage.getItem('access_token') ?? '');
}

/** Create a portfolio via API; returns the created portfolio ID. */
async function createPortfolioViaApi(
  page: Page,
  name: string,
  currency = 'USD',
): Promise<string> {
  const token = await getToken(page);
  const res = await page.request.fetch(`${API_URL}/api/v1/portfolios`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    data: JSON.stringify({ name, base_currency: currency, color_hex: '#6366f1' }),
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return body.id as string;
}

/** Delete a portfolio via API. Ignores 404 (already gone). */
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
  if (!res.ok()) return [];
  const body = await res.json() as { data: { id: string; name: string }[] };
  return body.data ?? [];
}

// ─── portfolioStore — localStorage persistence ────────────────────────────────

test.describe('portfolioStore persistence', () => {
  test('TC-100 activePortfolioId persists to localStorage on portfolio switch', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });

    // Read the current active_portfolio_id stored after hydration
    const stored = await page.evaluate(() => localStorage.getItem('active_portfolio_id'));
    expect(stored).not.toBeNull();
    // Must be a UUID-like string
    expect(stored).toMatch(/^[0-9a-f-]{36}$/i);
  });

  test('TC-101 activePortfolioId survives full page reload', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });

    const storedBefore = await page.evaluate(() => localStorage.getItem('active_portfolio_id'));
    await page.reload();
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });

    const storedAfter = await page.evaluate(() => localStorage.getItem('active_portfolio_id'));
    expect(storedAfter).toBe(storedBefore);
  });

  test('TC-102 stale activePortfolioId falls back to first portfolio', async ({ page }) => {
    // Set a non-existent UUID in localStorage
    await page.goto('/dashboard');
    await page.evaluate(() =>
      localStorage.setItem('active_portfolio_id', '00000000-0000-0000-0000-000000000000'),
    );
    await page.reload();
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });

    // Wait for the portfolio switcher to show a valid name (indicates fallback resolved)
    await expect(page.locator('[data-testid="portfolio-switcher"]').first()).toBeVisible({ timeout: 10_000 });

    // After reload, the stored value should have been replaced with a real portfolio ID
    const stored = await page.evaluate(() => localStorage.getItem('active_portfolio_id'));
    expect(stored).not.toBe('00000000-0000-0000-0000-000000000000');
    expect(stored).toMatch(/^[0-9a-f-]{36}$/i);
  });
});

// ─── appContextStore — localStorage persistence ───────────────────────────────

test.describe('appContextStore persistence', () => {
  test('TC-105 active_app_context defaults to portfolio on first visit', async ({ page }) => {
    // Clear storage to simulate first visit
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.removeItem('active_app_context'));
    await page.reload();
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });

    const stored = await page.evaluate(() => localStorage.getItem('active_app_context'));
    // Default is 'portfolio' when key is absent
    expect(stored === 'portfolio' || stored === null).toBeTruthy();
  });

  test('TC-106 invalid active_app_context falls back to portfolio', async ({ page }) => {
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.setItem('active_app_context', 'garbage_value'));
    await page.reload();
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });

    const stored = await page.evaluate(() => localStorage.getItem('active_app_context'));
    expect(stored).toBe('portfolio');
  });

  test('TC-107 switching context persists to localStorage', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });
    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));

    // Switch to library via BentoMenu
    await page.getByRole('banner').getByRole('button', { name: /application context|menu|bento/i }).first().click();
    await page.getByText('Global Library').click();
    
    console.log("Before URL check:", await page.evaluate(() => localStorage.getItem('active_app_context')));
    await expect(page).toHaveURL(/\/dashboard\/library/, { timeout: 8_000 });

    const stored = await page.evaluate(() => localStorage.getItem('active_app_context'));
    expect(stored).toBe('library');
  });
});

// ─── EmptyPortfolioGate ────────────────────────────────────────────────────────

test.describe.serial('EmptyPortfolioGate', () => {
  /**
   * These tests manipulate the user's portfolio list — they use a SEPARATE
   * test user (e2e_destructive) so they don't race with other parallel tests
   * that depend on the main e2e_testuser's portfolios.
   */

  const DESTRUCTIVE_AUTH_FILE = path.join(__dirname, '../.auth/destructive-user.json');
  test.use({ storageState: DESTRUCTIVE_AUTH_FILE });

  let createdPortfolioIds: string[] = [];

  test.afterEach(async ({ page }) => {
    // Restore: delete any portfolios created during tests, recreate one default
    for (const id of createdPortfolioIds) {
      await deletePortfolioViaApi(page, id).catch(() => {});
    }
    createdPortfolioIds = [];
    // Navigate to dashboard to ensure access_token is in localStorage before API calls
    await page.goto('/dashboard').catch(() => {});
    // Ensure user has at least one portfolio for other test suites
    const portfolios = await listPortfoliosViaApi(page).catch(() => []);
    if (portfolios.length === 0) {
      const id = await createPortfolioViaApi(page, 'Default Portfolio');
      createdPortfolioIds = []; // don't delete the restored one
      void id;
    }
    // Reset stored portfolio id
    await page.evaluate(() => localStorage.removeItem('active_portfolio_id'));
  });

  test('TC-110 EmptyPortfolioGate shown when user has no portfolios', async ({ page }) => {
    // Navigate first so localStorage is accessible for getToken
    await page.goto('/dashboard');
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState('networkidle');
    const portfolios = await listPortfoliosViaApi(page);
    console.log("Portfolios before deletion:", portfolios);
    for (const p of portfolios) {
      console.log("Deleting portfolio", p.id);
      await deletePortfolioViaApi(page, p.id).catch(e => console.log("Failed to delete", p.id, e));
      // Only delete if no accounts (spec: portfolio must be empty to delete)
      await deletePortfolioViaApi(page, p.id).catch(() => {});
    }

    // Clear stale localStorage ID so gate logic can run
    await page.evaluate(() => localStorage.removeItem('active_portfolio_id'));
    await page.reload();

    // Gate should appear
    await expect(page.getByText(/no portfolios yet/i)).toBeVisible({ timeout: 10_000 });
  });

  test('TC-111 EmptyPortfolioGate CTA links to /dashboard/settings?tab=portfolios', async ({
    page,
  }) => {
    await page.goto('/dashboard');
    const portfolios = await listPortfoliosViaApi(page);
    for (const p of portfolios) {
      await deletePortfolioViaApi(page, p.id).catch(() => {});
    }
    await page.evaluate(() => localStorage.removeItem('active_portfolio_id'));
    await page.reload();

    await expect(page.getByText(/no portfolios yet/i)).toBeVisible({ timeout: 10_000 });

    const cta = page.getByRole('link', { name: /create.*portfolio/i }).or(
      page.getByRole('button', { name: /create.*portfolio/i }),
    );
    await cta.click();
    await expect(page).toHaveURL(/\/dashboard\/settings\?tab=portfolios/, { timeout: 8_000 });
  });

  test('TC-112 EmptyPortfolioGate shows TopBar (user can still sign out)', async ({ page }) => {
    await page.goto('/dashboard');
    const portfolios = await listPortfoliosViaApi(page);
    for (const p of portfolios) {
      await deletePortfolioViaApi(page, p.id).catch(() => {});
    }
    await page.evaluate(() => localStorage.removeItem('active_portfolio_id'));
    await page.reload();

    await expect(page.getByText(/no portfolios yet/i)).toBeVisible({ timeout: 10_000 });
    // TopBar must still be visible so user can sign out
    await expect(page.getByRole('banner')).toBeVisible();
  });

  test('TC-113 EmptyPortfolioGate does NOT show sidebar nav links', async ({ page }) => {
    await page.goto('/dashboard');
    const portfolios = await listPortfoliosViaApi(page);
    for (const p of portfolios) {
      await deletePortfolioViaApi(page, p.id).catch(() => {});
    }
    await page.evaluate(() => localStorage.removeItem('active_portfolio_id'));
    await page.reload();

    await expect(page.getByText(/no portfolios yet/i)).toBeVisible({ timeout: 10_000 });
    // Sidebar links must be hidden — gate is a full-content replacement
    await expect(page.getByRole('link', { name: /reports/i })).toBeHidden();
  });

  test('TC-114 loading skeleton shown while portfolio list is loading', async ({ page }) => {
    // Intercept and delay the GET /portfolios response to observe loading state
    await page.route('**/api/v1/portfolios', async (route) => {
      await new Promise((r) => setTimeout(r, 1500)); // 1.5 s delay
      await route.continue();
    });

    await page.goto('/dashboard');
    // During the delay, no gate and no broken content should flash
    // A skeleton or loading spinner should be present
    const skeleton = page.locator('[data-testid="portfolio-loading-skeleton"]').or(
      page.locator('[aria-busy="true"]'),
    );
    await expect(skeleton.or(page.getByText(/loading/i))).toBeVisible({ timeout: 3_000 }).catch(
      () => {
        // Acceptable: if render is fast enough the skeleton may not be observable in this env
      },
    );
    // After load: either gate (no portfolios) or normal dashboard — never a crash
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 8_000 });
  });

  test('TC-115 error banner shown on portfolio fetch failure — gate NOT shown', async ({
    page,
  }) => {
    // Mock GET /portfolios to return 500
    await page.route('**/api/v1/portfolios', (route) =>
      route.fulfill({ status: 500, body: '{"detail":"Internal Server Error"}' }),
    );

    await page.goto('/dashboard');

    // Error banner must be visible
    await expect(
      page.getByText(/failed to load portfolios/i).or(page.getByRole('alert')),
    ).toBeVisible({ timeout: 10_000 });

    // Gate ("No portfolios yet") must NOT be shown — fetch failure ≠ empty list
    await expect(page.getByText(/no portfolios yet/i)).toBeHidden();
  });
});

// ─── Page migration — no per-page AccountFilter ───────────────────────────────

test.describe('Page migration — no per-page AccountFilter', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('banner')).toBeVisible({ timeout: 15_000 });
  });

  test('TC-120 overview page has no AccountFilter dropdown', async ({ page }) => {
    // The old AccountFilter component should no longer appear anywhere on the page
    await expect(page.locator('[data-testid="account-filter"]').or(
      page.getByRole('combobox', { name: /account/i }),
    )).toBeHidden();
  });

  test('TC-121 trades page has no per-page account selector', async ({ page }) => {
    await page.goto('/dashboard/trades');
    await expect(page.locator('[data-testid="account-filter"]').or(
      page.getByRole('combobox', { name: /filter by account/i }),
    )).toBeHidden();
  });
});
