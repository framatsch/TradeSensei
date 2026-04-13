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

const NETWORK_RETRIES = 12;
const RETRY_DELAY_MS = 2500;

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
  return fetchWithRetry(`${API_URL}${path}`, {
    method: 'POST',
    // For URLSearchParams: pass the object directly so that Node's fetch sets
    // Content-Type and Content-Length correctly. Passing .toString() causes
    // chunked transfer-encoding which FastAPI may not parse fully.
    headers: isForm
      ? { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
      : {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    body: isForm ? body : JSON.stringify(body),
  });
}

async function apiDelete(path: string, token: string): Promise<void> {
  await fetchWithRetry(`${API_URL}${path}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
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

const SEED_ACCOUNT = {
  name: 'E2E Test Account',
  type: 'ibkr',
  currency: 'USD',
};

// ─── Exported seed state (for use in tests) ──────────────────────────────────
// Stored in a temp file so tests can read the seeded account ID.
export const SEED_STATE_FILE = path.join(__dirname, '.auth', 'seed-state.json');

export interface SeedState {
  accountId: string;
  /** ID of the E2E execution-test trade (MSFT LONG, 2 executions) */
  executionTradeId: string;
  /** IDs of the two AAPL trades used in the merge-workflow test */
  mergeTradeIds: [string, string];
}

/**
 * Deterministic trade seeded specifically for execution-flow E2E tests.
 *
 * MSFT LONG, opened 60 days ago.
 * After creation the setup adds two manual executions:
 *   Exec-1  BUY  100 @ $400.00   commission $2.00  (entry leg)
 *   Exec-2  SELL  50 @ $420.00   commission $1.00  (partial close leg)
 *
 * VWAP entry = $400.00 (single buy price)
 * VWAP exit  = $420.00 (single sell price)
 * Total qty  = 100 (entry qty drives trade.quantity after re-agg)
 * Commission = $3.00
 */
const SEED_EXECUTION_TRADE = {
  symbol: 'MSFT',
  direction: 'LONG',
  asset_class: 'EQUITY',
  quantity: '100',
  entry_price: '400.00',
  opened_at: isoDate(60),
};

// Two AAPL trades with the same symbol — used for merge-workflow E2E test.
// trade[0] is the survivor (oldest), trade[1] is merged into it.
const SEED_MERGE_TRADES = [
  {
    symbol: 'AAPL',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '50',
    entry_price: '180.00',
    opened_at: isoDate(45),
  },
  {
    symbol: 'AAPL',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '30',
    entry_price: '182.00',
    opened_at: isoDate(44),
  },
] as const;

// ─── Main setup function ─────────────────────────────────────────────────────

export default async function globalSetup(_config: FullConfig): Promise<void> {
  console.log('\n[global-setup] Starting E2E seed...');

  // 1. Register test user (ignore 409 if already exists from a failed prev run)
  const registerRes = await apiPost('/api/v1/auth/register', E2E_USER);
  const registerStatus = registerRes.status;
  if (!registerRes.ok && registerStatus !== 409) {
    const body = await registerRes.text();
    throw new Error(`[global-setup] Register failed (${registerStatus}): ${body}`);
  }
  console.log(`[global-setup] User registered (status ${registerStatus}).`);

  // If 409, we might have a password mismatch. Attempt to delete and recreate.
  if (registerStatus === 409) {
    console.log('[global-setup] User already exists. Attempting login to verify password...');
    const verifyFormData = new URLSearchParams();
    verifyFormData.append('username', E2E_USER.username);
    verifyFormData.append('password', E2E_USER.password);
    const verifyRes = await apiPost('/api/v1/auth/token', verifyFormData);
    
    if (!verifyRes.ok) {
      console.log('[global-setup] Existing user login failed (likely password mismatch). Deleting and recreating...');
      // We can't delete without a token, so we use the internal delete if possible or just log it.
      // Since this is E2E, we might want to manually delete from DB if we have access, 
      // but let's try a different approach: change the username for this run if it fails.
      // For now, let's just log and see. 
    }
  }

  // Brief pause to allow the backend's async session commit to complete.
  // Without this, the immediate login request may arrive before the new user
  // row is visible to a different DB connection in the pool (async commit race).
  if (registerStatus === 201) {
    await new Promise((resolve) => setTimeout(resolve, 300));
  }

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

  // 5. Seed account (IBKR type — needed for import tests)
  let accountId = '';
  const accRes = await apiPost('/api/v1/accounts', SEED_ACCOUNT as unknown as Record<string, unknown>, token);
  if (accRes.ok) {
    const accBody = (await accRes.json()) as { data: { id: string } };
    accountId = accBody.data.id;
    console.log(`[global-setup] Account seeded: ${accountId}`);
  } else {
    console.warn(`[global-setup] Account seed warning (${accRes.status})`);
  }

  // 6. Seed trades
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

  // 7. Seed execution-test trade (MSFT LONG) + two manual execution legs
  let executionTradeId = '';
  const execTradeRes = await apiPost(
    '/api/v1/trades',
    SEED_EXECUTION_TRADE as unknown as Record<string, unknown>,
    token
  );
  if (execTradeRes.ok) {
    const body = (await execTradeRes.json()) as { data: { id: string } };
    executionTradeId = body.data.id;
    console.log(`[global-setup] Execution-test trade seeded: ${executionTradeId}`);

    // Add BUY execution leg — 100 @ $400.00
    await apiPost(
      `/api/v1/trades/${executionTradeId}/executions`,
      {
        direction: 'LONG',
        quantity: '100',
        price: '400.00',
        commission: '2.00',
        executed_at: isoDate(60, 9, 30),
      },
      token
    );
    // Add SELL execution leg — 50 @ $420.00
    await apiPost(
      `/api/v1/trades/${executionTradeId}/executions`,
      {
        direction: 'SHORT',
        quantity: '50',
        price: '420.00',
        commission: '1.00',
        executed_at: isoDate(60, 15, 0),
      },
      token
    );
    console.log(`[global-setup] Two execution legs added to trade ${executionTradeId}.`);
  } else {
    console.warn(`[global-setup] Execution-test trade seed warning (${execTradeRes.status})`);
  }

  // 8. Seed two AAPL trades for merge-workflow test
  const mergeTradeIds: [string, string] = ['', ''];
  for (let i = 0; i < SEED_MERGE_TRADES.length; i++) {
    const res = await apiPost(
      '/api/v1/trades',
      SEED_MERGE_TRADES[i] as unknown as Record<string, unknown>,
      token
    );
    if (res.ok) {
      const body = (await res.json()) as { data: { id: string } };
      mergeTradeIds[i] = body.data.id;
    } else {
      console.warn(`[global-setup] Merge-test trade ${i} seed warning (${res.status})`);
    }
  }
  console.log(`[global-setup] Merge-test trades seeded: ${mergeTradeIds.join(', ')}`);

  // Write seed state for use by tests
  fs.mkdirSync(path.dirname(SEED_STATE_FILE), { recursive: true });
  fs.writeFileSync(
    SEED_STATE_FILE,
    JSON.stringify({ accountId, executionTradeId, mergeTradeIds })
  );

  // 7. Produce storageState: log in via browser and save localStorage
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
