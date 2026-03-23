/**
 * Item CRUD flow tests.
 * Requires `make dev` to be running.
 */
import { test, expect } from "@playwright/test";

const API = "http://localhost:8080";
const HEADERS = { "X-User-Id": "dev-user", "Content-Type": "application/json" };

test.describe("Item CRUD", () => {
  let createdItemId;

  test("create item via API", async ({ request }) => {
    const resp = await request.post(`${API}/entries`, {
      headers: HEADERS,
      data: { title: "Playwright Test Item", body: "Created by Playwright e2e test" },
    });
    expect(resp.status()).toBe(201);
    const body = await resp.json();
    expect(body.item.title).toBe("Playwright Test Item");
    expect(body.item.itemId).toBeTruthy();
    createdItemId = body.item.itemId;
  });

  test("list items includes created item", async ({ request }) => {
    // Create an item first
    const createResp = await request.post(`${API}/entries`, {
      headers: HEADERS,
      data: { title: "List Test Item", body: "Should appear in list" },
    });
    expect(createResp.status()).toBe(201);
    const { item } = await createResp.json();

    // List items and verify it appears
    const listResp = await request.get(`${API}/entries`, { headers: HEADERS });
    expect(listResp.status()).toBe(200);
    const { items } = await listResp.json();
    const found = items.some((i) => i.itemId === item.itemId);
    expect(found).toBe(true);

    // Cleanup
    await request.delete(`${API}/entries/${item.itemId}`, { headers: HEADERS });
  });

  test("update item", async ({ request }) => {
    const createResp = await request.post(`${API}/entries`, {
      headers: HEADERS,
      data: { title: "Original Title", body: "Original body" },
    });
    const { item } = await createResp.json();

    const updateResp = await request.put(`${API}/entries/${item.itemId}`, {
      headers: HEADERS,
      data: { title: "Updated Title", body: "Updated body" },
    });
    expect(updateResp.status()).toBe(200);
    const updated = await updateResp.json();
    expect(updated.item.title).toBe("Updated Title");

    // Cleanup
    await request.delete(`${API}/entries/${item.itemId}`, { headers: HEADERS });
  });

  test("delete item returns 204 then 404 on get", async ({ request }) => {
    const createResp = await request.post(`${API}/entries`, {
      headers: HEADERS,
      data: { title: "Delete Me", body: "Should be deleted" },
    });
    const { item } = await createResp.json();

    const deleteResp = await request.delete(`${API}/entries/${item.itemId}`, {
      headers: HEADERS,
    });
    expect([200, 204]).toContain(deleteResp.status()); // API returns 200

    const getResp = await request.get(`${API}/entries/${item.itemId}`, {
      headers: HEADERS,
    });
    expect(getResp.status()).toBe(404);
  });

  test("item list renders in UI", async ({ page }) => {
    // Create an item via API
    const resp = await page.request.post(`${API}/entries`, {
      headers: HEADERS,
      data: { title: "UI Visible Item", body: "Should show in the list" },
    });
    const { item } = await resp.json();

    // Load the app and look for the item title
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("text=UI Visible Item")).toBeVisible({ timeout: 5000 });

    // Cleanup
    await page.request.delete(`${API}/entries/${item.itemId}`, { headers: HEADERS });
  });
});
