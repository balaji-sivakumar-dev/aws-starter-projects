import { apiRequest } from "./client";

export function getHealth() {
  return apiRequest("/health", { method: "GET" });
}

export function getMe() {
  return apiRequest("/me", { method: "GET" });
}

export function listEntries({ limit = 20, nextToken } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (nextToken) params.set("nextToken", nextToken);
  return apiRequest(`/entries?${params.toString()}`, { method: "GET" });
}

export function getEntry(entryId) {
  return apiRequest(`/entries/${entryId}`, { method: "GET" });
}

export function createEntry(payload) {
  return apiRequest("/entries", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateEntry(entryId, payload) {
  return apiRequest(`/entries/${entryId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteEntry(entryId) {
  return apiRequest(`/entries/${entryId}`, { method: "DELETE" });
}

export function enqueueAi(entryId) {
  return apiRequest(`/entries/${entryId}/ai`, { method: "POST" });
}
