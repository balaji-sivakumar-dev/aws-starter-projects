/**
 * Auth helpers — dual-mode: local (no-op) or Cognito PKCE.
 *
 * Local mode  → isAuthed() always returns true; no redirects happen.
 * Cognito mode → standard PKCE flow against the Cognito hosted UI.
 */

import { config, isLocalMode } from "../config";
import { challenge, verifier } from "./pkce";

const TOKEN_KEY = "t3.tokens";
const VERIFIER_KEY = "t3.pkce.verifier";

// ── URL helpers ───────────────────────────────────────────────────────────────

function authorizeUrl() {
  return `https://${config.cognitoDomain}/oauth2/authorize`;
}

function tokenUrl() {
  return `https://${config.cognitoDomain}/oauth2/token`;
}

function logoutUrl() {
  return `https://${config.cognitoDomain}/logout`;
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function login() {
  if (isLocalMode()) return; // nothing to do in local mode

  const v = verifier();
  const c = await challenge(v);
  sessionStorage.setItem(VERIFIER_KEY, v);

  const url = new URL(authorizeUrl());
  url.searchParams.set("client_id", config.cognitoClientId);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", config.scope);
  url.searchParams.set("redirect_uri", config.redirectUri);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", c);

  window.location.assign(url.toString());
}

export async function handleCallback() {
  if (isLocalMode()) return;

  const url = new URL(window.location.href);
  const code = url.searchParams.get("code");
  if (!code) throw new Error("Missing authorization code");

  const v = sessionStorage.getItem(VERIFIER_KEY);
  if (!v) throw new Error("Missing PKCE verifier");

  const body = new URLSearchParams();
  body.set("grant_type", "authorization_code");
  body.set("client_id", config.cognitoClientId);
  body.set("code", code);
  body.set("redirect_uri", config.redirectUri);
  body.set("code_verifier", v);

  const resp = await fetch(tokenUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) throw new Error("Token exchange failed");

  const tokens = await resp.json();
  localStorage.setItem(
    TOKEN_KEY,
    JSON.stringify({
      ...tokens,
      expiresAt: Date.now() + Number(tokens.expires_in || 3600) * 1000,
    })
  );
  sessionStorage.removeItem(VERIFIER_KEY);
  window.history.replaceState({}, document.title, "/");
}

export function accessToken() {
  if (isLocalMode()) return null; // API uses X-User-Id header instead

  const raw = localStorage.getItem(TOKEN_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed.access_token || Date.now() >= Number(parsed.expiresAt || 0)) {
      localStorage.removeItem(TOKEN_KEY);
      return null;
    }
    return parsed.access_token;
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    return null;
  }
}

export function logout() {
  if (isLocalMode()) return;

  localStorage.removeItem(TOKEN_KEY);
  const url = new URL(logoutUrl());
  url.searchParams.set("client_id", config.cognitoClientId);
  url.searchParams.set("logout_uri", config.logoutUri);
  window.location.assign(url.toString());
}

export function isAuthed() {
  if (isLocalMode()) return true; // always signed-in locally
  return Boolean(accessToken());
}
