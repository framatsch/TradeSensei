import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for Trade Journal integration tests.
 *
 * Requires the full stack to be running locally:
 *   docker compose up -d
 *
 * globalSetup seeds a test user + demo data via the REST API before all tests.
 * globalTeardown deletes the test user (cascade-deletes all owned data) after.
 */
export default defineConfig({
  testDir: './frontend/tests',
  /* Only run spec files inside the specs/ subdirectory */
  testMatch: '**/specs/**/*.spec.ts',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter */
  reporter: [['html'], ['list']],

  /* Global setup / teardown — seed and clean test data */
  globalSetup: './frontend/tests/global-setup.ts',
  globalTeardown: './frontend/tests/global-teardown.ts',

  use: {
    /* Base URL — local dev stack */
    baseURL: 'http://localhost:3000',

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
