import { api } from "./client";

export async function getMetrics(days = 7) {
  return api(`/admin/metrics?days=${days}`);
}

export async function getAuditLogs(date = "", limit = 50, nextToken = "") {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (limit) params.set("limit", String(limit));
  if (nextToken) params.set("nextToken", nextToken);
  return api(`/admin/audit?${params}`);
}

export async function listUsers() {
  return api("/admin/users");
}

export async function getUserActivity(userId, days = 7) {
  return api(`/admin/users/${userId}/activity?days=${days}`);
}

export async function adminRagStatus() {
  return api("/admin/rag/status");
}
