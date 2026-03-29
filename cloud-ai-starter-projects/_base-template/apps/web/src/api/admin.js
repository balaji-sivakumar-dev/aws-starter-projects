import { api } from "./client";

export async function getMetrics(days = 7) {
  return api(`/admin/metrics?days=${days}`);
}

export async function getAuditLogs(date = "", userId = "", limit = 200) {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (userId) params.set("userId", userId);
  if (limit) params.set("limit", String(limit));
  return api(`/admin/audit?${params}`);
}

export async function listUsers() {
  return api("/admin/users");
}

export async function adminRagStatus() {
  return api("/admin/rag/status");
}
