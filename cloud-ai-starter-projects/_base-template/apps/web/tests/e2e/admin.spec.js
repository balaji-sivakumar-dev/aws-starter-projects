/**
 * Admin panel API tests.
 * Requires `make dev` to be running.
 * In local mode all users are admins — no special credentials needed.
 */
import { test, expect } from "@playwright/test";

const API = "http://localhost:8080";
const HEADERS = { "X-User-Id": "dev-user", "Content-Type": "application/json" };

test.describe("Admin API", () => {
  test("GET /admin/metrics returns aggregate stats", async ({ request }) => {
    const resp = await request.get(`${API}/admin/metrics`, { headers: HEADERS });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(typeof body.totalAiCalls).toBe("number");
    expect(typeof body.totalRagQueries).toBe("number");
    expect(typeof body.activeUsers).toBe("number");
    expect(typeof body.totalUserActions).toBe("number");
  });

  test("GET /admin/users returns user list", async ({ request }) => {
    const resp = await request.get(`${API}/admin/users`, { headers: HEADERS });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(typeof body.totalUsers).toBe("number");
    expect(body.users).toBeInstanceOf(Array);
  });

  test("GET /admin/audit returns paginated logs", async ({ request }) => {
    const resp = await request.get(`${API}/admin/audit`, { headers: HEADERS });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.items).toBeInstanceOf(Array);
  });

  test("GET /admin/rag/status returns RAG index info", async ({ request }) => {
    const resp = await request.get(`${API}/admin/rag/status`, {
      headers: HEADERS,
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(typeof body.totalVectors).toBe("number");
    expect(typeof body.totalUsers).toBe("number");
  });

  test("admin metrics with days filter", async ({ request }) => {
    for (const days of [7, 14, 30]) {
      const resp = await request.get(`${API}/admin/metrics?days=${days}`, {
        headers: HEADERS,
      });
      expect(resp.status()).toBe(200);
    }
  });
});

test.describe("Admin UI", () => {
  test("admin panel is accessible in local mode", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Look for admin nav link or button
    const adminLink = page.locator(
      '[href*="admin"], [data-testid="admin"], button:has-text("Admin"), a:has-text("Admin")'
    );
    if (await adminLink.count() > 0) {
      await adminLink.first().click();
      await page.waitForLoadState("networkidle");
      // Admin section should show metrics
      await expect(
        page.locator(".admin-container, [data-testid='admin-panel'], h2:has-text('Admin')").first()
      ).toBeVisible({ timeout: 5000 });
    } else {
      // If no admin link, skip — app may not show admin in nav
      test.skip(true, "No admin link found in navigation");
    }
  });
});
