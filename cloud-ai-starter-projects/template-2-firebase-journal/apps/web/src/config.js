const env = import.meta.env;

export const config = {
  firebase: {
    apiKey: env.VITE_FIREBASE_API_KEY || "",
    authDomain: env.VITE_FIREBASE_AUTH_DOMAIN || "",
    projectId: env.VITE_FIREBASE_PROJECT_ID || "",
    appId: env.VITE_FIREBASE_APP_ID || "",
  },
  apiBaseUrl: (env.VITE_API_BASE_URL || "").replace(/\/$/, ""),
};

export function missingConfig() {
  const missing = [];
  if (!config.firebase.apiKey) missing.push("VITE_FIREBASE_API_KEY");
  if (!config.firebase.authDomain) missing.push("VITE_FIREBASE_AUTH_DOMAIN");
  if (!config.firebase.projectId) missing.push("VITE_FIREBASE_PROJECT_ID");
  if (!config.firebase.appId) missing.push("VITE_FIREBASE_APP_ID");
  if (!config.apiBaseUrl) missing.push("VITE_API_BASE_URL");
  return missing;
}
