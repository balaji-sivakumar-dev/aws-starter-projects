/**
 * Smoke tests — verify the app loads and core UI is visible.
 * Requires `make dev` to be running.
 */
import { test, expect } from "@playwright/test";

test.describe("Smoke", () => {
  test("home page loads without errors", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    expect(errors).toHaveLength(0);
  });

  test("app title is visible", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // The app renders the APP_TITLE as a heading or title
    await expect(page.locator("h1, .app-title, .brand").first()).toBeVisible();
  });

  test("API health check returns ok", async ({ request }) => {
    const resp = await request.get("http://localhost:8080/health");
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });
});
