/**
 * Smoke test: feature-gated sidebar nav items.
 *
 * This is a lightweight sanity check that the sidebar correctly reflects
 * enabled financials feature flags. Full coverage lives in features-settings.spec.ts.
 */

import { test, expect, type Page } from '@playwright/test';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

async function getToken(page: Page): Promise<string> {
  return page.evaluate(() => localStorage.getItem('access_token') ?? '');
}

test('enabled financials flags inject Cash and Tax nav items into the sidebar', async ({ page }) => {
  await page.goto('/dashboard');

  // Enable both financials flags via API (faster than UI for a smoke test)
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

  // Reload so the fresh settings are picked up by the sidebar
  await page.reload();
  await page.waitForLoadState('networkidle');

  await expect(page.getByRole('link', { name: /Cash & Dividends/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /Cash Report/i })).toBeVisible();

  // Cleanup: disable flags again so other tests start clean
  await page.request.fetch(`${API_URL}/api/v1/users/me/settings`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    data: JSON.stringify({
      features: { cash_and_dividends: false, tax_report: false },
    }),
  });
});
