// @ts-check
import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for UI integration tests.
 *
 * Tests run against the live Docker stack (make dev).
 * Ensure `make dev` is running before running `make test-ui`.
 *
 * Run:
 *   make test-ui           # headless, all browsers
 *   make test-ui-headed    # headed (watch mode)
 *   make test-ui-report    # open HTML report after a run
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,         // run sequentially — shared local API state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3000",
    extraHTTPHeaders: {
      // Local auth bypass — all requests authenticated as dev-user
      "X-User-Id": "dev-user",
    },
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
