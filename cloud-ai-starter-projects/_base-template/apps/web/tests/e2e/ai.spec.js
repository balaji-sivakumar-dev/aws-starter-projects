/**
 * AI enrichment + RAG endpoint tests.
 * Requires `make dev` to be running (Ollama models must be loaded).
 * Note: AI calls can take 10-60s depending on model size.
 */
import { test, expect } from "@playwright/test";

const API = "http://localhost:8080";
const HEADERS = { "X-User-Id": "dev-user", "Content-Type": "application/json" };

test.describe("AI Enrichment", () => {
  test("config/providers lists available providers", async ({ request }) => {
    const resp = await request.get(`${API}/config/providers`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.providers).toBeInstanceOf(Array);
    expect(body.providers.length).toBeGreaterThan(0);
    // Ollama should always be listed when running locally
    const names = body.providers.map((p) => p.name);
    expect(names).toContain("ollama");
  });

  test(
    "AI enrichment returns aiStatus DONE",
    async ({ request }) => {
      // Create item
      const createResp = await request.post(`${API}/entries`, {
        headers: HEADERS,
        data: {
          title: "AI Enrichment Test",
          body: "Testing that Ollama can enrich this entry with tags and summary",
        },
      });
      expect(createResp.status()).toBe(201);
      const { item } = await createResp.json();

      // Trigger AI enrichment
      const aiResp = await request.post(`${API}/entries/${item.itemId}/ai`, {
        headers: HEADERS,
      });
      expect([200, 202]).toContain(aiResp.status()); // 202 = async accepted
      const result = await aiResp.json();
      expect(result.aiStatus).toBe("DONE");
      expect(result.summary).toBeTruthy();
      expect(result.tags).toBeInstanceOf(Array);

      // Cleanup
      await request.delete(`${API}/entries/${item.itemId}`, { headers: HEADERS });
    },
    { timeout: 90_000 } // Ollama can take up to 90s
  );
});

test.describe("RAG", () => {
  test("RAG status returns vector count", async ({ request }) => {
    const resp = await request.get(`${API}/rag/status`, { headers: HEADERS });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(typeof body.totalVectors).toBe("number");
  });

  test(
    "RAG ask returns an answer",
    async ({ request }) => {
      // Create + embed an item first
      const createResp = await request.post(`${API}/entries`, {
        headers: HEADERS,
        data: {
          title: "RAG Test Entry",
          body: "The capital of France is Paris. This is used for RAG testing.",
        },
      });
      const { item } = await createResp.json();

      // Embed it
      await request.post(`${API}/rag/embed`, {
        headers: HEADERS,
        data: { entryId: item.itemId },
      });

      // Ask a question
      const askResp = await request.post(`${API}/rag/ask`, {
        headers: HEADERS,
        data: { query: "What is the capital of France?", top_k: 3 },
      });
      expect(askResp.status()).toBe(200);
      const answer = await askResp.json();
      expect(answer.answer).toBeTruthy();

      // Cleanup
      await request.delete(`${API}/entries/${item.itemId}`, { headers: HEADERS });
    },
    { timeout: 90_000 }
  );
});
