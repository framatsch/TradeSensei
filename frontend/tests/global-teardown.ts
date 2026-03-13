/**
 * Playwright Global Teardown — cleans up E2E test data after all tests.
 *
 * Calls DELETE /api/v1/users/me which cascade-deletes the test user and
 * ALL owned data (trades, playbooks, tags, accounts) in a single API call.
 *
 * This leaves the database in a clean state for the next run.
 */

import type { FullConfig } from '@playwright/test';
import { E2E_USER } from './global-setup';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

export default async function globalTeardown(_config: FullConfig): Promise<void> {
  console.log('\n[global-teardown] Cleaning up E2E test data...');

  try {
    // Re-authenticate to get a fresh token
    const formData = new URLSearchParams();
    formData.append('username', E2E_USER.username);
    formData.append('password', E2E_USER.password);

    const tokenRes = await fetch(`${API_URL}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!tokenRes.ok) {
      // User may have already been deleted or never created — not an error
      console.log('[global-teardown] Could not authenticate for teardown. Skipping.');
      return;
    }

    const { access_token: token } = (await tokenRes.json()) as { access_token: string };

    // DELETE /api/v1/users/me — cascades to all owned data
    const deleteRes = await fetch(`${API_URL}/api/v1/users/me`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });

    if (deleteRes.status === 204) {
      console.log('[global-teardown] Test user and all data deleted successfully.');
    } else {
      console.warn(
        `[global-teardown] Delete returned unexpected status: ${deleteRes.status}`
      );
    }
  } catch (err) {
    // Teardown failures should not block CI reports
    console.warn('[global-teardown] Teardown error (non-fatal):', err);
  }

  console.log('[global-teardown] Done.\n');
}
