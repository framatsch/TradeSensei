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
 * Playwright Global Setup — seeds the E2E test database via REST API.
 *
 * Runs once before all tests. Creates:
 *  - A dedicated E2E test user with a default portfolio
 *  - A second destructive test user used exclusively for tests that need
 *    an isolated, disposable context (e.g. EmptyPortfolioGate)
 *
 * The auth state (access_token in localStorage) is written to
 * frontend/tests/.auth/user.json so all specs can reuse it without
 * re-logging in.
 *
 * Teardown counterpart: global-teardown.ts calls DELETE /api/v1/users/me
 * which cascade-deletes all owned data in one API call.
 */

import { type FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';

const NETWORK_RETRIES = 12;
const RETRY_DELAY_MS = 2500;

export const E2E_USER = {
  username: 'e2e_testuser',
  email: 'e2e_testuser@example.com',
  password: 'E2eTestPass123!',
};

export const E2E_DESTRUCTIVE_USER = {
  username: 'e2e_destructive',
  email: 'e2e_destructive@example.com',
  password: 'E2eTestPass123!',
};

const AUTH_FILE = path.join(__dirname, '.auth', 'user.json');
const DESTRUCTIVE_AUTH_FILE = path.join(__dirname, '.auth', 'destructive-user.json');

async function apiPost(
  path: string,
  body: Record<string, unknown> | URLSearchParams,
  token?: string
): Promise<Response> {
  const isForm = body instanceof URLSearchParams;
  return fetchWithRetry(`${API_URL}${path}`, {
    method: 'POST',
    headers: isForm
      ? { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
      : {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    body: isForm ? body : JSON.stringify(body),
  });
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= NETWORK_RETRIES; attempt++) {
    try {
      return await fetch(url, init);
    } catch (error) {
      lastError = error;
      if (attempt === NETWORK_RETRIES) break;
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }
  throw lastError instanceof Error ? lastError : new Error('Network request failed');
}

function isoDate(daysAgo: number, hour = 9, minute = 30): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  d.setHours(hour, minute, 0, 0);
  return d.toISOString().replace('.000Z', 'Z');
}

function isoDateClose(daysAgo: number): string {
  return isoDate(daysAgo, 15, 45);
}

const SEED_TRADES = [
  { symbol: 'AAPL', direction: 'LONG', asset_class: 'EQUITY', quantity: '100', entry_price: '178.50', exit_price: '185.20', pnl: '670.00', commission: '1.50', opened_at: isoDate(30), closed_at: isoDateClose(29) },
  { symbol: 'TSLA', direction: 'LONG', asset_class: 'EQUITY', quantity: '50', entry_price: '245.00', exit_price: '262.80', pnl: '890.00', commission: '2.00', opened_at: isoDate(25), closed_at: isoDateClose(24) },
  { symbol: 'NVDA', direction: 'LONG', asset_class: 'EQUITY', quantity: '30', entry_price: '480.00', exit_price: '501.50', pnl: '645.00', commission: '1.80', opened_at: isoDate(20), closed_at: isoDateClose(19) },
  { symbol: 'EURUSD', direction: 'LONG', asset_class: 'FOREX', quantity: '10000', entry_price: '1.0820', exit_price: '1.0895', pnl: '750.00', commission: '5.00', opened_at: isoDate(15), closed_at: isoDateClose(14) },
  { symbol: 'ES', direction: 'LONG', asset_class: 'FUTURE', quantity: '2', entry_price: '5120.00', exit_price: '5148.50', pnl: '2850.00', commission: '8.00', opened_at: isoDate(10), closed_at: isoDateClose(9) },
  { symbol: 'META', direction: 'SHORT', asset_class: 'EQUITY', quantity: '40', entry_price: '510.00', exit_price: '525.30', pnl: '-612.00', commission: '1.60', opened_at: isoDate(28), closed_at: isoDateClose(27) },
  { symbol: 'BTCUSDT', direction: 'SHORT', asset_class: 'CRYPTO', quantity: '0.5', entry_price: '67500.00', exit_price: '69200.00', pnl: '-850.00', commission: '10.00', opened_at: isoDate(22), closed_at: isoDateClose(21) },
  { symbol: 'AAPL', direction: 'SHORT', asset_class: 'EQUITY', quantity: '75', entry_price: '190.00', exit_price: '193.50', pnl: '-262.50', commission: '1.50', opened_at: isoDate(18), closed_at: isoDateClose(17) },
  { symbol: 'GBPUSD', direction: 'SHORT', asset_class: 'FOREX', quantity: '5000', entry_price: '1.2650', exit_price: '1.2720', pnl: '-350.00', commission: '4.00', opened_at: isoDate(12), closed_at: isoDateClose(11) },
  { symbol: 'NQ', direction: 'LONG', asset_class: 'FUTURE', quantity: '1', entry_price: '18200.00', exit_price: '18145.00', pnl: '-275.00', commission: '4.00', opened_at: isoDate(5), closed_at: isoDateClose(4) },
];

const SEED_PLAYBOOKS = [
  { name: 'Breakout', description: 'Price breaks above a key resistance level.' },
  { name: 'Reversal', description: 'Counter-trend entry at key zones.' },
];

const SEED_TAXONOMIES = [
  { name: 'high-conviction', color: '#22c55e', scope: 'trades' },
  { name: 'emotional-error', color: '#ef4444', scope: 'trades' },
  { name: 'planned', color: '#3b82f6', scope: 'trades' },
  { name: 'bullish-day', color: '#22c55e', scope: 'checkins' },
  { name: 'bearish-day', color: '#ef4444', scope: 'checkins' },
];

const SEED_ANNOTATIONS = [
  { name: 'Regime', type: 'string_enum', scope: 'checkins', scale_labels: { options: ['Bull', 'Bear', 'Chop'] } },
  { name: 'Focus', type: 'int', scope: 'checkins', scale_labels: { min: 1, max: 10 } },
];

const SEED_ACCOUNT = { name: 'E2E Test Account', type: 'ibkr', currency: 'USD' };
const SEED_SCHWAB_ACCOUNT = { name: 'E2E Schwab Account', type: 'schwab', currency: 'USD' };

export const SEED_STATE_FILE = path.join(__dirname, '.auth', 'seed-state.json');

export default async function globalSetup(_config: FullConfig): Promise<void> {
  console.log('\n[global-setup] Starting E2E seed...');

  const registerRes = await apiPost('/api/v1/auth/register', E2E_USER);
  const registerStatus = registerRes.status;
  if (!registerRes.ok && registerStatus !== 409) {
    throw new Error(`[global-setup] Register failed (${registerStatus}): ${await registerRes.text()}`);
  }

  if (registerStatus === 201) await new Promise((resolve) => setTimeout(resolve, 300));

  const formData = new URLSearchParams();
  formData.append('username', E2E_USER.username);
  formData.append('password', E2E_USER.password);
  const tokenRes = await apiPost('/api/v1/auth/token', formData);
  const { access_token: token } = (await tokenRes.json()) as { access_token: string };

  let portfolioId = '';
  const listPortfoliosRes = await fetchWithRetry(`${API_URL}/api/v1/portfolios`, { headers: { Authorization: `Bearer ${token}` } });
  if (listPortfoliosRes.ok) {
    const listBody = (await listPortfoliosRes.json()) as { data: Array<{ id: string }> };
    if (listBody.data?.length > 0) portfolioId = listBody.data[0].id;
  }
  if (!portfolioId) {
    const createPortfolioRes = await apiPost('/api/v1/portfolios', { name: 'E2E Default Portfolio', base_currency: 'USD' }, token);
    const createBody = (await createPortfolioRes.json()) as { data: { id: string } };
    portfolioId = createBody.data.id;
  }

  for (const pb of SEED_PLAYBOOKS) await apiPost('/api/v1/playbooks', pb, token);
  for (const tax of SEED_TAXONOMIES) await apiPost('/api/v1/taxonomies', { name: tax.name, color_hex: tax.color, scope: tax.scope }, token);
  for (const ann of SEED_ANNOTATIONS) await apiPost('/api/v1/annotation-definitions', ann, token);

  const accRes = await apiPost(`/api/v1/portfolios/${portfolioId}/accounts`, SEED_ACCOUNT, token);
  const accountId = accRes.ok ? ((await accRes.json()) as { data: { id: string } }).data.id : '';

  const sAccRes = await apiPost(`/api/v1/portfolios/${portfolioId}/accounts`, SEED_SCHWAB_ACCOUNT, token);
  const schwabAccountId = sAccRes.ok ? ((await sAccRes.json()) as { data: { id: string } }).data.id : '';

  for (const trade of SEED_TRADES) await apiPost(`/api/v1/portfolios/${portfolioId}/trades`, { ...trade, account_id: accountId }, token);

  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  fs.writeFileSync(AUTH_FILE, JSON.stringify({
    cookies: [],
    origins: [{ origin: BASE_URL, localStorage: [
      { name: 'access_token', value: token },
      { name: 'active_portfolio_id', value: portfolioId },
      { name: 'active_app_context', value: 'portfolio' },
    ]}]
  }, null, 2));

  console.log('[global-setup] Seed complete.');

  const destructiveRegRes = await apiPost('/api/v1/auth/register', E2E_DESTRUCTIVE_USER);
  if (destructiveRegRes.status === 201) await new Promise(resolve => setTimeout(resolve, 300));
  const dFormData = new URLSearchParams();
  dFormData.append('username', E2E_DESTRUCTIVE_USER.username);
  dFormData.append('password', E2E_DESTRUCTIVE_USER.password);
  const dTokenRes = await apiPost('/api/v1/auth/token', dFormData);
  if (dTokenRes.ok) {
    const dToken = (await dTokenRes.json()).access_token;
    const dPortRes = await apiPost('/api/v1/portfolios', { name: 'E2E Destructive Portfolio', base_currency: 'USD' }, dToken);
    if (!dPortRes.ok) {
      throw new Error(`[global-setup] Destructive portfolio creation failed: ${dPortRes.status} ${dPortRes.statusText}`);
    }
    const dPortId = ((await dPortRes.json()) as { data: { id: string } }).data.id;
    fs.mkdirSync(path.dirname(DESTRUCTIVE_AUTH_FILE), { recursive: true });
    fs.writeFileSync(DESTRUCTIVE_AUTH_FILE, JSON.stringify({
      cookies: [],
      origins: [{ origin: BASE_URL, localStorage: [
        { name: 'access_token', value: dToken },
        { name: 'active_portfolio_id', value: dPortId },
        { name: 'active_app_context', value: 'portfolio' },
      ]}]
    }, null, 2));
  }
}
