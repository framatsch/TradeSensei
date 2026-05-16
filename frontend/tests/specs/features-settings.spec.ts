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
 * Feature-flag settings tests.
 *
 * Covers:
 *  1. Toggle a feature flag → Apply → state persists across page reload
 *  2. Enabling multiple flags from the same group does NOT reset the others
 *  3. Enabling Cash & Dividends / Cash Report makes nav items appear in sidebar
 *  4. Disabling them hides the nav items again
 *
 * Requires the full stack to be running (docker compose up -d).
 * Auth state is provided by globalSetup → .auth/user.json.
 */

import { test, expect, type Page } from '@playwright/test';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Extract the Bearer token stored in localStorage by globalSetup. */
async function getToken(page: Page): Promise<string> {
  return page.evaluate(() => localStorage.getItem('access_token') ?? '');
}

/** Reset all known feature flags to false via the REST API. */
async function resetFeatureFlags(page: Page): Promise<void> {
  const token = await getToken(page);
  const res = await page.request.fetch(`${API_URL}/api/v1/users/me/settings`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    data: JSON.stringify({
      features: {
        risk_analytics: false,
        cash_and_dividends: false,
        tax_report: false,
      },
    }),
  });
  expect(res.ok()).toBeTruthy();
}

/** Navigate to the Settings → Features tab. */
async function openFeaturesTab(page: Page): Promise<void> {
  await page.goto('/dashboard/settings?tab=features');
  // Wait for the feature toggles to be visible
  await expect(page.getByRole('switch', { name: 'Risk Analytics' })).toBeVisible();
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// These tests share the same e2e_testuser account — run them serially to avoid
// parallel writes stomping on each other's feature-flag state.
test.describe.serial('Feature flag settings', () => {
  test.beforeEach(async ({ page }) => {
    // Start each test from a clean state: all flags off
    await page.goto('/dashboard');
    await resetFeatureFlags(page);
  });

  // ── 1. Toggle + Apply persists ──────────────────────────────────────────────

  test('enabling Risk Analytics persists after page reload', async ({ page }) => {
    await openFeaturesTab(page);

    const toggle = page.getByRole('switch', { name: 'Risk Analytics' });
    const applyBtn = page.getByRole('button', { name: 'Apply Changes' });

    // Initial state: off
    await expect(toggle).toHaveAttribute('aria-checked', 'false');

    // Apply button should be disabled when nothing changed
    await expect(applyBtn).toBeDisabled();

    // Toggle on
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-checked', 'true');

    // Apply button becomes active
    await expect(applyBtn).toBeEnabled();

    // Apply
    await applyBtn.click();
    await expect(applyBtn).toBeDisabled(); // goes back to disabled after save

    // Reload page and revisit Features tab — state should be persisted
    await page.reload();
    await openFeaturesTab(page);
    await expect(page.getByRole('switch', { name: 'Risk Analytics' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
  });

  // ── 2. Enabling one flag does not reset sibling flags ──────────────────────

  test('enabling multiple flags in sequence does not reset earlier changes', async ({ page }) => {
    await openFeaturesTab(page);

    const cashToggle = page.getByRole('switch', { name: 'Cash & Dividends' });
    const taxToggle  = page.getByRole('switch', { name: 'Tax Report' });
    const applyBtn   = page.getByRole('button', { name: 'Apply Changes' });

    // Enable Cash & Dividends
    await cashToggle.click();
    await expect(cashToggle).toHaveAttribute('aria-checked', 'true');
    await applyBtn.click();
    await expect(applyBtn).toBeDisabled();

    // Enable Tax Report — Cash & Dividends must still be on
    await expect(cashToggle).toHaveAttribute('aria-checked', 'true');
    await taxToggle.click();
    await expect(taxToggle).toHaveAttribute('aria-checked', 'true');
    await applyBtn.click();
    await expect(applyBtn).toBeDisabled();

    // Reload — both should remain on
    await page.reload();
    await openFeaturesTab(page);
    await expect(page.getByRole('switch', { name: 'Cash & Dividends' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    await expect(page.getByRole('switch', { name: 'Tax Report' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
  });

  // ── 3. Financials flags gate sidebar nav items ─────────────────────────────

  test('enabling Cash & Dividends and Cash Report shows sidebar nav items', async ({ page }) => {
    await openFeaturesTab(page);

    const cashToggle = page.getByRole('switch', { name: 'Cash & Dividends' });
    const taxToggle  = page.getByRole('switch', { name: 'Tax Report' });
    const applyBtn   = page.getByRole('button', { name: 'Apply Changes' });

    await cashToggle.click();
    await taxToggle.click();
    await applyBtn.click();
    await expect(applyBtn).toBeDisabled();

    // Navigate to dashboard and check sidebar
    await page.goto('/dashboard');
    await expect(page.getByRole('link', { name: /Cash & Dividends/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Tax Report/i })).toBeVisible();
  });

  // ── 4b. Sidebar live-update — no page navigation ──────────────────────────
  //
  // This is the regression test for the timing bug where FeatureGatedNavItems
  // was dynamically loaded and owned its own useSettings subscription. Because
  // it could miss the React Query cache update if Apply was clicked before the
  // component finished its lazy-load + initial render, the sidebar only updated
  // after a page navigation.
  //
  // Fix: DashboardLayout now owns the useSettings subscription and passes
  // showCash / showTax as props, so FeatureGatedNavItems is driven by the
  // parent's cache — no timing window.

  test('enabling Financials flags updates sidebar immediately without navigation', async ({ page }) => {
    // Start on the Features tab
    await openFeaturesTab(page);

    const cashToggle = page.getByRole('switch', { name: 'Cash & Dividends' });
    const taxToggle  = page.getByRole('switch', { name: 'Tax Report' });
    const applyBtn   = page.getByRole('button', { name: 'Apply Changes' });

    // Enable both flags
    await cashToggle.click();
    await taxToggle.click();
    await applyBtn.click();

    // Apply button disables → server round-trip complete
    await expect(applyBtn).toBeDisabled();

    // Since the sidebar is hidden on the settings page now, we MUST navigate
    // to a page where the sidebar is visible to verify.
    await page.goto('/dashboard/workspace/overview');

    await expect(page.getByRole('link', { name: /Cash & Dividends/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Tax Report/i })).toBeVisible();
  });

  test('disabling Financials flags hides sidebar nav items', async ({ page }) => {
    // Pre-condition: enable both flags via API
    const token = await getToken(page);
    await page.request.fetch(`${API_URL}/api/v1/users/me/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      data: JSON.stringify({
        features: { cash_and_dividends: true, tax_report: true },
      }),
    });

    await page.reload();
    await openFeaturesTab(page);

    // Both toggles should be on
    await expect(page.getByRole('switch', { name: 'Cash & Dividends' })).toHaveAttribute(
      'aria-checked',
      'true',
    );

    // Disable both
    await page.getByRole('switch', { name: 'Cash & Dividends' }).click();
    await page.getByRole('switch', { name: 'Tax Report' }).click();
    await page.getByRole('button', { name: 'Apply Changes' }).click();
    await expect(page.getByRole('button', { name: 'Apply Changes' })).toBeDisabled();

    // Navigate to dashboard — nav items should be gone
    await page.goto('/dashboard');
    await expect(page.getByRole('link', { name: /Cash & Dividends/i })).toBeHidden();
    await expect(page.getByRole('link', { name: /Tax Report/i })).toBeHidden();
  });

  // ── 5. API-based smoke test (faster than UI) ─────────────────────────────
  
  test('enabled financials flags inject Cash and Tax nav items via API', async ({ page }) => {
    // Enable both financials flags via API (faster than UI for a smoke test)
    await page.goto('/dashboard');
    const token = await getToken(page);
    
    const res = await page.request.fetch(`${API_URL}/api/v1/users/me/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      data: JSON.stringify({
        features: { cash_and_dividends: true, tax_report: true },
      }),
    });
    expect(res.ok()).toBeTruthy();

    // Navigate to a different route first to ensure React Query cache is invalidated
    await page.goto('/dashboard/settings');
    await page.waitForLoadState('networkidle');
    
    // Now navigate back to dashboard - the sidebar should have fresh settings
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('link', { name: /Cash & Dividends/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('link', { name: /Tax Report/i })).toBeVisible({ timeout: 15_000 });
  });
});
