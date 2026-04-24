/**
 * Navigation Spec — covers sidebar nav links, active states, and logout.
 *
 * All tests run as the seeded E2E user.
 *
 * ⚠️  MIGRATION NOTICE (Spec 2 — app-state-topbar-navigation):
 * Several tests in this file will break once Spec 2 is implemented:
 *
 *   TC-040 — Playbooks/Tags links move to Global Library context (sidebar-library),
 *             Sign Out moves to UserBadge dropdown. Update selectors accordingly.
 *   TC-042 — /dashboard/playbooks will redirect to /dashboard/library/playbooks.
 *             Test now lives in topbar-navigation.spec.ts (TC-093).
 *   TC-043 — /dashboard/tags will redirect to /dashboard/library/tags.
 *             Test now lives in topbar-navigation.spec.ts (TC-094).
 *   TC-047 — "Sign Out" button removed from sidebar; now in UserBadge dropdown.
 *             Replacement test: topbar-navigation.spec.ts TC-098.
 *   TC-048 — Same as TC-047.
 *
 * When Spec 2 is implemented, update this file:
 *   1. Remove TC-042, TC-043 (replaced by topbar-navigation.spec.ts)
 *   2. Remove TC-047, TC-048 (replaced by topbar-navigation.spec.ts)
 *   3. In TC-040: remove Playbooks/Tags/Sign Out assertions; add BentoMenu assertion
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
    // ⚠️  SPEC 2 MIGRATION: Remove the assertions below once Spec 2 is implemented.
    // Playbooks/Tags move to Global Library context; Sign Out moves to UserBadge dropdown.
    await expect(page.getByRole('link', { name: 'Playbooks', exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Tags', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign Out' })).toBeVisible();
  });

  test('TC-041 navigates to Trades page', async ({ page }) => {
    await page.getByRole('button', { name: 'Trades', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/trades/);
    await expect(page.getByRole('heading', { name: 'Trades', exact: true })).toBeVisible({ timeout: 10_000 });
  });

  // ⚠️  SPEC 2 MIGRATION: TC-042 and TC-043 will break once Spec 2 is implemented.
  // /dashboard/playbooks → redirects to /dashboard/library/playbooks
  // /dashboard/tags      → redirects to /dashboard/library/tags
  // Replacement tests live in topbar-navigation.spec.ts (TC-093, TC-094).
  // These tests should be DELETED after Spec 2 is merged.

  test('TC-042 navigates to Playbooks page', async ({ page }) => {
    await page.getByRole('link', { name: 'Playbooks', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/playbooks/);
    await expect(page.getByRole('heading', { name: 'Playbooks', exact: true })).toBeVisible({ timeout: 10_000 });
  });

  test('TC-043 navigates to Tags page', async ({ page }) => {
    await page.getByRole('link', { name: 'Tags', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/tags/);
    await expect(page.getByRole('heading', { name: 'Tags', exact: true })).toBeVisible({ timeout: 10_000 });
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

  // ⚠️  SPEC 2 MIGRATION: TC-047 and TC-048 will break once Spec 2 is implemented.
  // "Sign Out" button moves from sidebar to the UserBadge dropdown in the TopBar.
  // Replacement test: topbar-navigation.spec.ts TC-098.
  // These tests should be DELETED after Spec 2 is merged.

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
