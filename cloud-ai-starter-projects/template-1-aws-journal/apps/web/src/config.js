const env = import.meta.env;

export const config = {
  apiBaseUrl: (env.VITE_API_BASE_URL || "").replace(/\/$/, ""),
  cognitoDomain: env.VITE_COGNITO_DOMAIN || "",
  cognitoClientId: env.VITE_COGNITO_CLIENT_ID || "",
  redirectUri: env.VITE_COGNITO_REDIRECT_URI || `${window.location.origin}/callback`,
  logoutUri: env.VITE_COGNITO_LOGOUT_URI || `${window.location.origin}/`,
  scope: "openid email profile",
};

export function validateConfig() {
  const missing = [];
  if (!config.apiBaseUrl) missing.push("VITE_API_BASE_URL");
  if (!config.cognitoDomain) missing.push("VITE_COGNITO_DOMAIN");
  if (!config.cognitoClientId) missing.push("VITE_COGNITO_CLIENT_ID");
  return missing;
}
