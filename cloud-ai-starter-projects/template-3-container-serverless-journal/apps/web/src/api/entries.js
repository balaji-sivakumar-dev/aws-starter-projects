import { api } from "./client";

export const getMe = () => api("/me");
export const listEntries = (nextToken) => api(`/entries?limit=50${nextToken ? `&nextToken=${encodeURIComponent(nextToken)}` : ""}`);
export const getEntry = (entryId) => api(`/entries/${entryId}`);
export const createEntry = (payload) => api("/entries", { method: "POST", body: JSON.stringify(payload) });
export const updateEntry = (entryId, payload) => api(`/entries/${entryId}`, { method: "PUT", body: JSON.stringify(payload) });
export const deleteEntry = (entryId) => api(`/entries/${entryId}`, { method: "DELETE" });
export const triggerAi = (entryId, provider) =>
  api(`/entries/${entryId}/ai`, {
    method: "POST",
    headers: provider ? { "x-llm-provider": provider } : {},
  });
export const countEntries = () => api("/entries/count");
export const bulkDeleteEntries = (entryIds) =>
  api("/entries/bulk-delete", { method: "POST", body: JSON.stringify({ entryIds }) });
