import { config } from "../config";
import { accessToken } from "../auth/auth";

export async function api(path, options = {}) {
  const token = accessToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(`${config.apiBaseUrl}${path}`, { ...options, headers });
  const body = await resp.json();
  if (!resp.ok) {
    throw new Error(body?.message || `Request failed (${resp.status})`);
  }
  return body;
}
