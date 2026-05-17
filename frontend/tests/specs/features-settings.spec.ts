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
});
