/**
 * Auth Setup — produces the authenticated browser state (storageState).
 *
 * This project runs as a Playwright dependency before all other test projects.
 * It navigates to the app and injects the token that was acquired in globalSetup,
 * then saves the storageState so all subsequent tests start already authenticated.
 *
 * The token is written to localStorage by globalSetup already — this file just
 * validates that the dashboard is actually reachable with that token.
 */

import { test as setup, expect } from '@playwright/test';
import path from 'path';

const AUTH_FILE = path.join(__dirname, '../.auth/user.json');

setup('authenticate', async ({ page }) => {
  // Navigate to dashboard — storageState from globalSetup has already injected
  // the access_token into localStorage, so the auth guard should pass.
  await page.goto('/dashboard');

  // Wait for the dashboard to be visible (main sidebar nav link "Overview" with exact href)
  await expect(page.getByRole('link', { name: 'Overview' }).first()).toBeVisible({ timeout: 15_000 });

  // Persist the storage state for all dependent test projects
  await page.context().storageState({ path: AUTH_FILE });
});
