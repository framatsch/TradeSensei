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
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible({ timeout: 15_000 });
  });

  test('TC-040 sidebar shows all navigation items', async ({ page }) => {
    // Basic items should always be present in portfolio workspace context
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Trades', exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('link', { name: 'Import', exact: true })).toBeVisible();
    await expect(page.locator('text=Portfolio Workspace')).toBeVisible(); // BentoMenu label proxy
  });

  test('TC-041 navigates to Trades page', async ({ page }) => {
    await page.getByRole('button', { name: 'Trades', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/trades/);
    await expect(page.getByRole('heading', { name: 'Trades', exact: true })).toBeVisible({ timeout: 10_000 });
  });

  test('TC-044 navigates to Import page', async ({ page }) => {
    await page.getByRole('link', { name: 'Import', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/import/);
    await expect(page.getByRole('heading', { name: 'Import Trades' })).toBeVisible({ timeout: 10_000 });
  });

  test('TC-045 Overview link is active on /dashboard', async ({ page }) => {
    // The active link uses the .nav-active class (Obsidian design system)
    const overviewLink = page.locator('a[href="/dashboard"]');
    await expect(overviewLink).toHaveClass(/nav-active/);
  });

  test('TC-046 active link updates when navigating to Trades', async ({ page }) => {
    await page.getByRole('button', { name: 'Trades', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/trades/);

    const tradesLink = page.getByRole('button', { name: 'Trades', exact: true });
    await expect(tradesLink).toHaveClass(/nav-active/);

    // Overview link should no longer be active
    const overviewLink = page.locator('a[href="/dashboard"]');
    await expect(overviewLink).not.toHaveClass(/nav-active/);
  });
});
