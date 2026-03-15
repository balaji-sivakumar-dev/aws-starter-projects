import { api } from "./client";

export async function askJournal(query, topK = 5) {
  return api("/rag/ask", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  });
}

export async function searchJournal(query, topK = 5) {
  return api("/rag/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  });
}

export async function embedEntry(entryId) {
  return api("/rag/embed", {
    method: "POST",
    body: JSON.stringify({ entryId }),
  });
}

export async function embedAllEntries() {
  return api("/rag/embed-all", { method: "POST" });
}

export async function ragStatus() {
  return api("/rag/status");
}
