import { api } from "./client";

export async function askJournal(query, topK = 5, provider = null) {
  return api("/rag/ask", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
    headers: provider ? { "x-llm-provider": provider } : {},
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

export async function clearIndex() {
  return api("/rag/vectors", { method: "DELETE" });
}

export async function listConversations() {
  return api("/rag/conversations");
}

export async function deleteConversation(convId) {
  return api(`/rag/conversations/${convId}`, { method: "DELETE" });
}
