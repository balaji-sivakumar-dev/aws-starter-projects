import { config } from "../config";
import { getAccessToken } from "../auth/auth";

export async function apiRequest(path, options = {}) {
  const token = getAccessToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const code = body?.code || "REQUEST_FAILED";
    const message = body?.message || `Request failed with status ${response.status}`;
    const error = new Error(message);
    error.code = code;
    error.requestId = body?.requestId;
    throw error;
  }

  return body;
}
