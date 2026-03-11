import { config } from "../config";
import { challengeFromVerifier, randomVerifier } from "./pkce";

const TOKEN_KEY = "journal.tokens";
const VERIFIER_KEY = "journal.pkce.verifier";

function tokenEndpoint() {
  return `https://${config.cognitoDomain}/oauth2/token`;
}

function authorizeEndpoint() {
  return `https://${config.cognitoDomain}/oauth2/authorize`;
}

function logoutEndpoint() {
  return `https://${config.cognitoDomain}/logout`;
}

export async function loginWithHostedUi() {
  const verifier = randomVerifier();
  const challenge = await challengeFromVerifier(verifier);
  sessionStorage.setItem(VERIFIER_KEY, verifier);

  const url = new URL(authorizeEndpoint());
  url.searchParams.set("client_id", config.cognitoClientId);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", config.scope);
  url.searchParams.set("redirect_uri", config.redirectUri);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", challenge);

  window.location.assign(url.toString());
}

export async function handleAuthCallback() {
  const url = new URL(window.location.href);
  const code = url.searchParams.get("code");
  if (!code) {
    throw new Error("Missing authorization code");
  }

  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!verifier) {
    throw new Error("Missing PKCE verifier");
  }

  const body = new URLSearchParams();
  body.set("grant_type", "authorization_code");
  body.set("client_id", config.cognitoClientId);
  body.set("code", code);
  body.set("redirect_uri", config.redirectUri);
  body.set("code_verifier", verifier);

  const response = await fetch(tokenEndpoint(), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  if (!response.ok) {
    throw new Error("Token exchange failed");
  }

  const tokens = await response.json();
  const expiresAt = Date.now() + (Number(tokens.expires_in || 3600) * 1000);
  localStorage.setItem(TOKEN_KEY, JSON.stringify({ ...tokens, expiresAt }));
  sessionStorage.removeItem(VERIFIER_KEY);

  window.history.replaceState({}, document.title, "/");
}

export function getTokens() {
  const raw = localStorage.getItem(TOKEN_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed.access_token || !parsed.expiresAt || Date.now() >= parsed.expiresAt) {
      localStorage.removeItem(TOKEN_KEY);
      return null;
    }
    return parsed;
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    return null;
  }
}

export function getAccessToken() {
  const tokens = getTokens();
  return tokens ? tokens.access_token : null;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  const url = new URL(logoutEndpoint());
  url.searchParams.set("client_id", config.cognitoClientId);
  url.searchParams.set("logout_uri", config.logoutUri);
  window.location.assign(url.toString());
}

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

function decodeJwtPart(part) {
  const normalized = part.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  return JSON.parse(atob(padded));
}

export function getIdProfile() {
  const tokens = getTokens();
  if (!tokens || !tokens.id_token) return null;
  const parts = tokens.id_token.split(".");
  if (parts.length < 2) return null;
  try {
    return decodeJwtPart(parts[1]);
  } catch {
    return null;
  }
}
