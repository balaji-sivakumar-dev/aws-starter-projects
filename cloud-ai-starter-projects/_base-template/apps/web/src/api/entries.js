import { api } from "./client";

export const getMe = () => api("/me");
export const listItems = (nextToken) => api(`/entries?limit=50${nextToken ? `&nextToken=${encodeURIComponent(nextToken)}` : ""}`);
export const getItem = (entryId) => api(`/entries/${entryId}`);
export const createItem = (payload) => api("/entries", { method: "POST", body: JSON.stringify(payload) });
export const updateItem = (entryId, payload) => api(`/entries/${entryId}`, { method: "PUT", body: JSON.stringify(payload) });
export const deleteItem = (entryId) => api(`/entries/${entryId}`, { method: "DELETE" });
export const triggerAi = (entryId, provider) =>
  api(`/entries/${entryId}/ai`, {
    method: "POST",
    headers: provider ? { "x-llm-provider": provider } : {},
  });
export const countItems = () => api("/entries/count");
export const bulkDeleteItems = (itemIds) =>
  api("/entries/bulk-delete", { method: "POST", body: JSON.stringify({ itemIds }) });
export const bulkImportItems = (entries) =>
  api("/entries/bulk-import", { method: "POST", body: JSON.stringify({ entries }) });
