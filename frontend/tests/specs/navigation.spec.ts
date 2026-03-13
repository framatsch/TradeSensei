/**
 * Navigation Spec — covers sidebar nav links, active states, and logout.
 *
 * All tests run as the seeded E2E user.
 */

import { test, expect } from '@playwright/test';

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    // Wait for sidebar to be rendered
    await expect(page.getByRole('link', { name: 'Overview' })).toBeVisible({ timeout: 10_000 });
  });

  test('TC-040 sidebar shows all navigation items', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Overview' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Trades' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Playbooks' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Tags' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Import' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign Out' })).toBeVisible();
  });

  test('TC-041 navigates to Trades page', async ({ page }) => {
    await page.getByRole('link', { name: 'Trades' }).click();
    await expect(page).toHaveURL(/\/dashboard\/trades/);
    await expect(page.getByRole('heading', { name: 'Trades' })).toBeVisible({ timeout: 8_000 });
  });

  test('TC-042 navigates to Playbooks page', async ({ page }) => {
    await page.getByRole('link', { name: 'Playbooks' }).click();
    await expect(page).toHaveURL(/\/dashboard\/playbooks/);
    await expect(page.getByRole('heading', { name: 'Playbooks' })).toBeVisible({ timeout: 8_000 });
  });

  test('TC-043 navigates to Tags page', async ({ page }) => {
    await page.getByRole('link', { name: 'Tags' }).click();
    await expect(page).toHaveURL(/\/dashboard\/tags/);
    await expect(page.getByRole('heading', { name: 'Tags', exact: true })).toBeVisible({ timeout: 8_000 });
  });

  test('TC-044 navigates to Import page', async ({ page }) => {
    await page.getByRole('link', { name: 'Import' }).click();
    await expect(page).toHaveURL(/\/dashboard\/import/);
    await expect(page.getByRole('heading', { name: 'Import Trades' })).toBeVisible({ timeout: 8_000 });
  });

  test('TC-045 Overview link is active on /dashboard', async ({ page }) => {
    // The active link has the blue-600/20 background class applied
    const overviewLink = page.getByRole('link', { name: 'Overview' });
    await expect(overviewLink).toHaveClass(/text-blue-400/);
  });

  test('TC-046 active link updates when navigating to Trades', async ({ page }) => {
    await page.getByRole('link', { name: 'Trades' }).click();
    await expect(page).toHaveURL(/\/dashboard\/trades/);

    const tradesLink = page.getByRole('link', { name: 'Trades' });
    await expect(tradesLink).toHaveClass(/text-blue-400/);

    // Overview link should no longer be active
    const overviewLink = page.getByRole('link', { name: 'Overview' });
    await expect(overviewLink).not.toHaveClass(/text-blue-400/);
  });

  test('TC-047 Sign Out button logs out and redirects to /login', async ({ page }) => {
    await page.getByRole('button', { name: 'Sign Out' }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    // localStorage access_token should be cleared
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

  test('TC-048 after logout, /dashboard redirects to /login', async ({ page }) => {
    await page.getByRole('button', { name: 'Sign Out' }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });

    // Try to access dashboard directly
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/, { timeout: 8_000 });
  });
});
