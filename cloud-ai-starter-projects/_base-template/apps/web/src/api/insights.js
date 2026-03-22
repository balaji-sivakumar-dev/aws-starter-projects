import { api } from "./client";

export const listSummaries = () => api("/insights/summaries");
export const getSummary = (summaryId) => api(`/insights/summaries/${summaryId}`);
export const generateSummary = (payload, provider) =>
  api("/insights/summaries", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: provider ? { "x-llm-provider": provider } : {},
  });
export const deleteSummary = (summaryId) =>
  api(`/insights/summaries/${summaryId}`, { method: "DELETE" });
export const regenerateSummary = (summaryId, provider) =>
  api(`/insights/summaries/${summaryId}/regenerate`, {
    method: "POST",
    headers: provider ? { "x-llm-provider": provider } : {},
  });
