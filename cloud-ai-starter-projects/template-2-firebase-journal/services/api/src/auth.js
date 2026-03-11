import admin from "firebase-admin";

import { ApiError } from "./errors.js";

export function initAdmin() {
  if (!admin.apps.length) {
    admin.initializeApp();
  }
  return admin;
}

export async function requireAuth(req) {
  const header = String(req.headers.authorization || "");
  if (!header.startsWith("Bearer ")) {
    throw new ApiError(401, "UNAUTHORIZED", "missing valid token");
  }

  const token = header.slice("Bearer ".length).trim();
  if (!token) {
    throw new ApiError(401, "UNAUTHORIZED", "missing valid token");
  }

  const decoded = await admin.auth().verifyIdToken(token);
  return {
    userId: decoded.uid,
    email: decoded.email || null,
    claims: decoded,
  };
}
