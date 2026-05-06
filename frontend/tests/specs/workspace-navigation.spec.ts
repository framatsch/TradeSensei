import { test, expect } from '@playwright/test';

test.describe('Workspace Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/workspace/overview');
    await expect(page.getByText('Portfolio Workspace', { exact: true }).first()).toBeVisible({ timeout: 15_000 });
  });

  const routes = [
    { path: '/dashboard/workspace/overview', name: 'Overview' },
    { path: '/dashboard/workspace/calendar', name: 'Calendar' },
    { path: '/dashboard/workspace/reporting', name: 'Reporting' },
    { path: '/dashboard/workspace/performance/strategy', name: 'Strategy' },
    { path: '/dashboard/workspace/performance/behavior', name: 'Behavior' }
  ];

  for (const route of routes) {
    test(`can navigate to ${route.name} and verify active state`, async ({ page }) => {
      // Click the sidebar link
      const link = page.getByRole('link', { name: route.name }).first();
      await expect(link).toBeVisible();
      await link.click();

      // Verify URL
      await expect(page).toHaveURL(new RegExp(route.path));

      // Verify active state
      await expect(link).toHaveClass(/nav-active/);
    });
  }
});
