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

import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for Trade Sensei integration tests.
 *
 * Requires the full stack to be running locally:
 *   docker compose up -d
 *
 * globalSetup seeds a test user + demo data via the REST API before all tests.
 * globalTeardown deletes the test user (cascade-deletes all owned data) after.
 */
export default defineConfig({
  /* Keep test imports on the root runtime when frontend dependencies are installed. */
  tsconfig: './tsconfig.playwright.json',
  testDir: './frontend/tests',
  /* Only run spec files inside the specs/ subdirectory */
  testMatch: '**/specs/**/*.spec.ts',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI; also retry once locally to handle timing flakes */
  retries: process.env.CI ? 2 : 1,
  /* Limit parallelism locally to avoid overloading the Docker stack */
  workers: process.env.CI ? 1 : 4,
  /* Reporter */
  reporter: [['html', { open: 'never' }], ['list'], ['json', { outputFile: 'test-results/results.json' }]],

  /* Global setup / teardown — seed and clean test data */
  globalSetup: './frontend/tests/global-setup.ts',
  globalTeardown: './frontend/tests/global-teardown.ts',

  use: {
    /* Base URL — local dev stack */
    baseURL: 'http://localhost:3000',
    headless: true,

    /* Reuse authenticated browser state seeded in globalSetup */
    storageState: './frontend/tests/.auth/user.json',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',
  },

  projects: [
    /* Auth setup project — runs first, produces .auth/user.json */
    {
      name: 'setup',
      testMatch: '**/auth.setup.ts',
      use: { 
        storageState: undefined,
        // Inherit baseURL from top-level use
      },
    },

    /* Main test projects — depend on setup */
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: './frontend/tests/.auth/user.json',
        // Inherit baseURL from top-level use
      },
      dependencies: ['setup'],
    },

    /* Firefox and WebKit are run in CI optionally; skip locally for speed */
    ...(process.env.CI
      ? [
          {
            name: 'firefox',
            use: { 
              ...devices['Desktop Firefox'],
              storageState: './frontend/tests/.auth/user.json',
              // Inherit baseURL from top-level use
            },
            dependencies: ['setup'],
          },
        ]
      : []),
  ],

  /* Local dev server is NOT auto-started here — run docker compose up -d manually */
});
