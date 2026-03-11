import { config } from "../config";
import { getIdToken } from "../auth/firebase";

export async function apiRequest(path, options = {}) {
  const token = await getIdToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const message = body?.message || `Request failed (${response.status})`;
    const error = new Error(message);
    error.code = body?.code;
    error.requestId = body?.requestId;
    throw error;
  }

  return body;
}
