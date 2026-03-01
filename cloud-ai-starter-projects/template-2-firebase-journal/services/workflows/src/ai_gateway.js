import { GoogleAuth } from "google-auth-library";

const auth = new GoogleAuth({
  scopes: ["https://www.googleapis.com/auth/cloud-platform"],
});

function toInt(raw, fallback) {
  const value = Number(raw);
  return Number.isFinite(value) ? Math.floor(value) : fallback;
}

function cleanSummary(value) {
  const summary = String(value || "").trim();
  return summary.length > 240 ? summary.slice(0, 240).trim() : summary;
}

function cleanTags(value) {
  if (!Array.isArray(value)) return [];
  const tags = [];
  for (const raw of value.slice(0, 5)) {
    const tag = String(raw || "")
      .toLowerCase()
      .replace(/[^a-z0-9\-\s]/g, "")
      .trim()
      .replace(/\s+/g, "-")
      .slice(0, 24);
    if (tag && !tags.includes(tag)) tags.push(tag);
  }
  return tags;
}

function parseJsonResponse(text) {
  const raw = String(text || "").trim();
  if (!raw) throw new Error("model returned empty response");

  try {
    const parsed = JSON.parse(raw);
    return parsed;
  } catch {
    const match = raw.match(/\{[\s\S]*\}/);
    if (!match) throw new Error("model response is not valid JSON");
    return JSON.parse(match[0]);
  }
}

export async function generateSummaryAndTags({ title, body }) {
  const maxInputChars = toInt(process.env.AI_MAX_INPUT_CHARS, 8000);
  const maxOutputTokens = toInt(process.env.AI_MAX_OUTPUT_TOKENS, 256);
  const location = process.env.VERTEX_AI_LOCATION || "us-central1";
  const projectId = process.env.GCLOUD_PROJECT || process.env.PROJECT_ID;
  const model = process.env.VERTEX_AI_MODEL || "gemini-2.0-flash-lite";

  if (!projectId) throw new Error("PROJECT_ID is required for Vertex AI calls");
  if (String(body || "").length > maxInputChars) {
    throw new Error(`body exceeds max input size (${maxInputChars})`);
  }

  const prompt = [
    "Return only minified JSON with keys summary and tags.",
    "summary must be <= 240 chars.",
    "tags must be 1-5 short lowercase tags.",
    `title: ${String(title || "")}`,
    `body: ${String(body || "")}`,
  ].join("\n");

  const client = await auth.getClient();
  const token = await client.getAccessToken();
  const accessToken = token?.token;
  if (!accessToken) throw new Error("failed to obtain access token");

  const url = `https://${location}-aiplatform.googleapis.com/v1/projects/${projectId}/locations/${location}/publishers/google/models/${model}:generateContent`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      contents: [
        {
          role: "user",
          parts: [{ text: prompt }],
        },
      ],
      generationConfig: {
        maxOutputTokens: maxOutputTokens,
        temperature: 0.2,
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`vertex ai call failed: ${response.status} ${text.slice(0, 180)}`);
  }

  const payload = await response.json();
  const text =
    payload?.candidates?.[0]?.content?.parts?.[0]?.text ||
    payload?.predictions?.[0]?.content ||
    "";

  const parsed = parseJsonResponse(text);
  const summary = cleanSummary(parsed.summary);
  const tags = cleanTags(parsed.tags);

  if (!summary) throw new Error("model returned empty summary");

  return {
    summary,
    tags: tags.length ? tags : ["journal"],
  };
}
