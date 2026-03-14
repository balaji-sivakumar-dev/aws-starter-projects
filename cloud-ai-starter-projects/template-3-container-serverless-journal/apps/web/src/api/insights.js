import { api } from "./client";

export const listSummaries = () => api("/insights/summaries");
export const getSummary = (summaryId) => api(`/insights/summaries/${summaryId}`);
export const generateSummary = (payload) =>
  api("/insights/summaries", { method: "POST", body: JSON.stringify(payload) });
export const deleteSummary = (summaryId) =>
  api(`/insights/summaries/${summaryId}`, { method: "DELETE" });
export const regenerateSummary = (summaryId) =>
  api(`/insights/summaries/${summaryId}/regenerate`, { method: "POST" });
