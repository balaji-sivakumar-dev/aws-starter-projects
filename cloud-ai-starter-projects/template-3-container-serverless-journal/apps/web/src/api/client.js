import { config, isLocalMode } from "../config";
import { accessToken } from "../auth/auth";

/**
 * Thin fetch wrapper.
 *
 * Local mode  → sends X-User-Id header (API reads it as the identity).
 * Cognito mode → sends Authorization: Bearer <token>.
 */
export async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (isLocalMode()) {
    headers["X-User-Id"] = config.localUserId;
  } else {
    const token = accessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(`${config.apiBaseUrl}${path}`, { ...options, headers });
  const body = await resp.json();
  if (!resp.ok) {
    throw new Error(body?.message || body?.detail?.message || `Request failed (${resp.status})`);
  }
  return body;
}
