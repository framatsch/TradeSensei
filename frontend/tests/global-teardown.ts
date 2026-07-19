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
 * Playwright Global Teardown — cleans up E2E test data after all tests.
 *
 * Calls DELETE /api/v1/users/me which cascade-deletes the test user and
 * ALL owned data (trades, playbooks, tags, accounts) in a single API call.
 *
 * This leaves the database in a clean state for the next run.
 */

import type { FullConfig } from '@playwright/test';
import { E2E_USER, E2E_DESTRUCTIVE_USER } from './global-setup';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
const NETWORK_RETRIES = 6;
const RETRY_DELAY_MS = 2000;

export default async function globalTeardown(_config: FullConfig): Promise<void> {
  console.log('\n[global-teardown] Cleaning up E2E test data...');

  try {
    // Re-authenticate to get a fresh token
    const formData = new URLSearchParams();
    formData.append('username', E2E_USER.username);
    formData.append('password', E2E_USER.password);

    const tokenRes = await fetchWithRetry(`${API_URL}/api/v1/auth/token`, {
      method: 'POST',
      body: formData,
    });

    if (tokenRes.ok) {
      const { access_token: token } = (await tokenRes.json()) as { access_token: string };

      // DELETE /api/v1/users/me — cascades to all owned data
      const deleteRes = await fetchWithRetry(`${API_URL}/api/v1/users/me`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (deleteRes.status === 204) {
        console.log('[global-teardown] Test user and all data deleted successfully.');
      } else {
        console.warn(`[global-teardown] Delete returned unexpected status: ${deleteRes.status}`);
      }
    } else {
      console.log('[global-teardown] Could not authenticate for teardown. Skipping main user.');
    }
  } catch (err) {
    // Teardown failures should not block CI reports
    console.warn('[global-teardown] Teardown error (non-fatal):', err);
  }

  // Also delete the destructive test user
  try {
    const dFormData = new URLSearchParams();
    dFormData.append('username', E2E_DESTRUCTIVE_USER.username);
    dFormData.append('password', E2E_DESTRUCTIVE_USER.password);
    const dTokenRes = await fetchWithRetry(`${API_URL}/api/v1/auth/token`, {
      method: 'POST',
      body: dFormData,
    });
    if (dTokenRes.ok) {
      const { access_token: dToken } = (await dTokenRes.json()) as { access_token: string };
      await fetchWithRetry(`${API_URL}/api/v1/users/me`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${dToken}` },
      });
      console.log('[global-teardown] Destructive test user deleted.');
    }
  } catch {
    // Non-fatal
  }

  console.log('[global-teardown] Done.\n');
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= NETWORK_RETRIES; attempt++) {
    try {
      return await fetch(url, init);
    } catch (error) {
      lastError = error;
      if (attempt === NETWORK_RETRIES) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Network request failed');
}
