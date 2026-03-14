const env = import.meta.env;

/**
 * AUTH_MODE controls the authentication strategy:
 *
 *   "local"   – No Cognito. The API accepts an X-User-Id header.
 *               Used when running via docker compose locally.
 *
 *   "cognito" – Full Cognito PKCE flow. Requires the cognito* vars below.
 *               Used when deployed to AWS.
 */
export const config = {
  apiBaseUrl: (env.VITE_API_BASE_URL || "").replace(/\/$/, ""),
  authMode: env.VITE_AUTH_MODE || "cognito",   // "local" | "cognito"
  localUserId: env.VITE_LOCAL_USER_ID || "dev-user",

  // Cognito – only required when authMode === "cognito"
  cognitoDomain: env.VITE_COGNITO_DOMAIN || "",
  cognitoClientId: env.VITE_COGNITO_CLIENT_ID || "",
  redirectUri: env.VITE_COGNITO_REDIRECT_URI || `${window.location.origin}/callback`,
  logoutUri: env.VITE_COGNITO_LOGOUT_URI || `${window.location.origin}/`,
  scope: "openid email profile",
};

export function isLocalMode() {
  return config.authMode === "local";
}

/** Returns missing required env vars (empty array = all good). */
export function missingConfig() {
  const missing = [];
  if (!config.apiBaseUrl) missing.push("VITE_API_BASE_URL");
  if (!isLocalMode()) {
    if (!config.cognitoDomain) missing.push("VITE_COGNITO_DOMAIN");
    if (!config.cognitoClientId) missing.push("VITE_COGNITO_CLIENT_ID");
  }
  return missing;
}
