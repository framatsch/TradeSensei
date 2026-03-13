/**
 * Playwright Global Setup — seeds the E2E test database via REST API.
 *
 * Runs once before all tests. Creates:
 *  - A dedicated E2E test user
 *  - 10 demo trades (5 winning LONG + 5 losing SHORT across multiple symbols)
 *  - 2 playbooks
 *  - 3 tags
 *
 * The auth state (access_token in localStorage) is written to
 * frontend/tests/.auth/user.json so all specs can reuse it without re-logging in.
 *
 * Teardown counterpart: global-teardown.ts calls DELETE /api/v1/users/me
 * which cascade-deletes all owned data in one API call.
 */

import { chromium, type FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';

export const E2E_USER = {
  username: 'e2e_testuser',
  email: 'e2e_testuser@example.com',
  password: 'E2eTestPass123!',
};

const AUTH_FILE = path.join(__dirname, '.auth', 'user.json');

// ─── REST API helpers ────────────────────────────────────────────────────────

async function apiPost(
  path: string,
  body: Record<string, unknown> | URLSearchParams,
  token?: string
): Promise<Response> {
  const isForm = body instanceof URLSearchParams;
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': isForm
        ? 'application/x-www-form-urlencoded'
        : 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: isForm ? body.toString() : JSON.stringify(body),
  });
  return res;
}

async function apiDelete(path: string, token: string): Promise<void> {
  await fetch(`${API_URL}${path}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ─── Seed helpers ────────────────────────────────────────────────────────────

function isoDate(daysAgo: number, hour = 9, minute = 30): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  d.setHours(hour, minute, 0, 0);
  return d.toISOString().replace('.000Z', 'Z');
}

function isoDateClose(daysAgo: number): string {
  return isoDate(daysAgo, 15, 45);
}

// 10 realistic trades: 5 winners (LONG equity), 5 losers (SHORT/LONG mixed)
const SEED_TRADES = [
  // ── Winning trades ──────────────────────────────────────────────────────
  {
    symbol: 'AAPL',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '100',
    entry_price: '178.50',
    exit_price: '185.20',
    pnl: '670.00',
    commission: '1.50',
    opened_at: isoDate(30),
    closed_at: isoDateClose(29),
    notes: 'Breakout above 50-day MA. Strong volume confirmation.',
  },
  {
    symbol: 'TSLA',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '50',
    entry_price: '245.00',
    exit_price: '262.80',
    pnl: '890.00',
    commission: '2.00',
    opened_at: isoDate(25),
    closed_at: isoDateClose(24),
    notes: 'Earnings play. Held overnight.',
  },
  {
    symbol: 'NVDA',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '30',
    entry_price: '480.00',
    exit_price: '501.50',
    pnl: '645.00',
    commission: '1.80',
    opened_at: isoDate(20),
    closed_at: isoDateClose(19),
  },
  {
    symbol: 'EURUSD',
    direction: 'LONG',
    asset_class: 'FOREX',
    quantity: '10000',
    entry_price: '1.0820',
    exit_price: '1.0895',
    pnl: '750.00',
    commission: '5.00',
    opened_at: isoDate(15),
    closed_at: isoDateClose(14),
    notes: 'Trend continuation. Clean structure.',
  },
  {
    symbol: 'ES',
    direction: 'LONG',
    asset_class: 'FUTURE',
    quantity: '2',
    entry_price: '5120.00',
    exit_price: '5148.50',
    pnl: '2850.00',
    commission: '8.00',
    opened_at: isoDate(10),
    closed_at: isoDateClose(9),
  },
  // ── Losing trades ───────────────────────────────────────────────────────
  {
    symbol: 'META',
    direction: 'SHORT',
    asset_class: 'EQUITY',
    quantity: '40',
    entry_price: '510.00',
    exit_price: '525.30',
    pnl: '-612.00',
    commission: '1.60',
    opened_at: isoDate(28),
    closed_at: isoDateClose(27),
    notes: 'Stopped out. Trend was stronger than expected.',
  },
  {
    symbol: 'BTCUSDT',
    direction: 'SHORT',
    asset_class: 'CRYPTO',
    quantity: '0.5',
    entry_price: '67500.00',
    exit_price: '69200.00',
    pnl: '-850.00',
    commission: '10.00',
    opened_at: isoDate(22),
    closed_at: isoDateClose(21),
    notes: 'Emotional trade. Should not have taken it.',
  },
  {
    symbol: 'AAPL',
    direction: 'SHORT',
    asset_class: 'EQUITY',
    quantity: '75',
    entry_price: '190.00',
    exit_price: '193.50',
    pnl: '-262.50',
    commission: '1.50',
    opened_at: isoDate(18),
    closed_at: isoDateClose(17),
  },
  {
    symbol: 'GBPUSD',
    direction: 'SHORT',
    asset_class: 'FOREX',
    quantity: '5000',
    entry_price: '1.2650',
    exit_price: '1.2720',
    pnl: '-350.00',
    commission: '4.00',
    opened_at: isoDate(12),
    closed_at: isoDateClose(11),
    notes: 'News spike. Unexpected BoE comment.',
  },
  {
    symbol: 'NQ',
    direction: 'LONG',
    asset_class: 'FUTURE',
    quantity: '1',
    entry_price: '18200.00',
    exit_price: '18145.00',
    pnl: '-275.00',
    commission: '4.00',
    opened_at: isoDate(5),
    closed_at: isoDateClose(4),
  },
];

const SEED_PLAYBOOKS = [
  {
    name: 'Breakout',
    description: 'Price breaks above a key resistance level with strong volume.',
  },
  {
    name: 'Reversal',
    description: 'Counter-trend entry at key support/resistance zones.',
  },
];

const SEED_TAGS = [
  { name: 'high-conviction', color: '#22c55e' },
  { name: 'emotional-error', color: '#ef4444' },
  { name: 'planned', color: '#3b82f6' },
];

// ─── Main setup function ─────────────────────────────────────────────────────

export default async function globalSetup(_config: FullConfig): Promise<void> {
  console.log('\n[global-setup] Starting E2E seed...');

  // 1. Register test user (ignore 409 if already exists from a failed prev run)
  const registerRes = await apiPost('/api/v1/auth/register', E2E_USER);
  if (!registerRes.ok && registerRes.status !== 409) {
    const body = await registerRes.text();
    throw new Error(`[global-setup] Register failed (${registerRes.status}): ${body}`);
  }
  console.log('[global-setup] User registered (or already exists).');

  // 2. Login to get access token
  const formData = new URLSearchParams();
  formData.append('username', E2E_USER.username);
  formData.append('password', E2E_USER.password);
  const tokenRes = await apiPost('/api/v1/auth/token', formData);
  if (!tokenRes.ok) {
    const body = await tokenRes.text();
    throw new Error(`[global-setup] Login failed (${tokenRes.status}): ${body}`);
  }
  const { access_token: token } = (await tokenRes.json()) as { access_token: string };
  console.log('[global-setup] Login successful. Token acquired.');

  // 3. Seed playbooks
  for (const pb of SEED_PLAYBOOKS) {
    const res = await apiPost('/api/v1/playbooks', pb, token);
    if (!res.ok && res.status !== 409) {
      console.warn(`[global-setup] Playbook seed warning (${res.status}): ${pb.name}`);
    }
  }
  console.log('[global-setup] Playbooks seeded.');

  // 4. Seed tags
  for (const tag of SEED_TAGS) {
    const res = await apiPost('/api/v1/tags', tag, token);
    if (!res.ok && res.status !== 409) {
      console.warn(`[global-setup] Tag seed warning (${res.status}): ${tag.name}`);
    }
  }
  console.log('[global-setup] Tags seeded.');

  // 5. Seed trades
  let tradeCount = 0;
  for (const trade of SEED_TRADES) {
    const res = await apiPost('/api/v1/trades', trade as unknown as Record<string, unknown>, token);
    if (res.ok) {
      tradeCount++;
    } else {
      const body = await res.text();
      console.warn(`[global-setup] Trade seed warning (${res.status}): ${body}`);
    }
  }
  console.log(`[global-setup] ${tradeCount}/${SEED_TRADES.length} trades seeded.`);

  // 6. Produce storageState: log in via browser and save localStorage
  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL: BASE_URL });
  const page = await context.newPage();

  // Inject token directly into localStorage (avoids UI login in every test)
  await page.goto(BASE_URL);
  await page.evaluate((t: string) => {
    localStorage.setItem('access_token', t);
  }, token);

  // Save storage state
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  await context.storageState({ path: AUTH_FILE });
  await browser.close();

  console.log(`[global-setup] Auth state saved to ${AUTH_FILE}`);
  console.log('[global-setup] Seed complete.\n');
}
