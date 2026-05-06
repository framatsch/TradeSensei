/**
 * Navigation Spec — covers sidebar nav links, active states, and logout.
 *
 * All tests run as the seeded E2E user.
 */

import { test, expect } from '@playwright/test';

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    // Wait for the layout to hydrate and the sidebar to be rendered.
    // The "Overview" link is a good proxy for the sidebar being ready.
    await expect(page.getByRole('link', { name: 'Overview' }).first()).toBeVisible({ timeout: 15_000 });
  });

  test('TC-040 sidebar shows all navigation items', async ({ page }) => {
    // Basic items should always be present in portfolio workspace context
    await expect(page.getByRole('link', { name: 'Overview' }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Home' }).filter({ hasText: 'Home' })).toBeVisible();
  });

  test('TC-041 navigates to Trades page', async ({ page }) => {
    await page.goto('/dashboard/trades');
    await expect(page).toHaveURL(/\/dashboard\/trades/);
    await expect(page.getByRole('heading', { name: 'Trades', exact: true })).toBeVisible({ timeout: 10_000 });
  });

  test('TC-044 navigates to Import page', async ({ page }) => {
    await page.goto('/dashboard/trades/import');
    await expect(page).toHaveURL(/\/dashboard\/trades\/import/);
    await expect(page.getByRole('heading', { name: 'Import Trades' })).toBeVisible({ timeout: 10_000 });
  });

  test('TC-045 Home link is active on /dashboard', async ({ page }) => {
    // The active link uses the .nav-active class
    const homeLink = page.getByRole('link', { name: 'Home' }).filter({ hasText: 'Home' });
    await expect(homeLink).toHaveClass(/nav-active/);
  });

  test('TC-046 active link updates when navigating to Overview', async ({ page }) => {
    await page.getByRole('link', { name: 'Overview' }).first().click();
    await expect(page).toHaveURL(/\/dashboard\/workspace\/overview/);

    const overviewLink = page.getByRole('link', { name: 'Overview' }).first();
    await expect(overviewLink).toHaveClass(/nav-active/);

    // Home link should no longer be active
    const homeLink = page.getByRole('link', { name: 'Home' }).first();
    await expect(homeLink).not.toHaveClass(/nav-active/);
  });

  test('TC-047 /dashboard/analytics redirects to workspace strategy', async ({ page }) => {
    await page.goto('/dashboard/analytics');
    await expect(page).toHaveURL(/\/dashboard\/workspace\/performance\/strategy/);
  });
});
