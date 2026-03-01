import admin from "firebase-admin";

import { ApiError } from "./errors.js";

const { FieldValue, Timestamp } = admin.firestore;

function entriesCollection(userId) {
  return admin.firestore().collection("users").doc(userId).collection("entries");
}

function toIso(value) {
  if (!value) return null;
  if (value instanceof Timestamp) {
    return value.toDate().toISOString();
  }
  return null;
}

function encodeNextToken(createdAt) {
  const ms = createdAt.toMillis();
  return Buffer.from(JSON.stringify({ createdAtMs: ms }), "utf8").toString("base64url");
}

function decodeNextToken(nextToken) {
  try {
    const parsed = JSON.parse(Buffer.from(nextToken, "base64url").toString("utf8"));
    const createdAtMs = Number(parsed.createdAtMs);
    if (Number.isNaN(createdAtMs)) throw new Error("invalid token data");
    return Timestamp.fromMillis(createdAtMs);
  } catch {
    throw new ApiError(400, "VALIDATION_ERROR", "invalid nextToken");
  }
}

function mapEntry(doc) {
  const data = doc.data();
  return {
    entryId: doc.id,
    userId: data.userId,
    title: data.title,
    body: data.body,
    createdAt: toIso(data.createdAt),
    updatedAt: toIso(data.updatedAt),
    deletedAt: toIso(data.deletedAt),
    aiStatus: data.aiStatus || "NOT_REQUESTED",
    summary: data.summary || null,
    tags: Array.isArray(data.tags) ? data.tags : [],
    aiUpdatedAt: toIso(data.aiUpdatedAt),
    aiError: data.aiError || null,
  };
}

export async function createEntry(userId, input) {
  const now = FieldValue.serverTimestamp();
  const ref = entriesCollection(userId).doc();

  await ref.set({
    entryId: ref.id,
    userId,
    title: input.title,
    body: input.body,
    createdAt: now,
    updatedAt: now,
    deletedAt: null,
    aiStatus: "NOT_REQUESTED",
    summary: null,
    tags: [],
    aiUpdatedAt: null,
    aiError: null,
  });

  const snap = await ref.get();
  return mapEntry(snap);
}

export async function getEntry(userId, entryId, includeDeleted = false) {
  const snap = await entriesCollection(userId).doc(entryId).get();
  if (!snap.exists) {
    throw new ApiError(404, "NOT_FOUND", "entry not found");
  }

  const entry = mapEntry(snap);
  if (!includeDeleted && entry.deletedAt) {
    throw new ApiError(404, "NOT_FOUND", "entry not found");
  }

  return entry;
}

export async function updateEntry(userId, entryId, updates) {
  const ref = entriesCollection(userId).doc(entryId);
  await getEntry(userId, entryId);

  const patch = {
    updatedAt: FieldValue.serverTimestamp(),
  };

  if (Object.prototype.hasOwnProperty.call(updates, "title")) {
    patch.title = updates.title;
  }
  if (Object.prototype.hasOwnProperty.call(updates, "body")) {
    patch.body = updates.body;
  }

  await ref.update(patch);
  const updated = await ref.get();
  return mapEntry(updated);
}

export async function softDeleteEntry(userId, entryId) {
  const ref = entriesCollection(userId).doc(entryId);
  await getEntry(userId, entryId, true);

  await ref.update({
    deletedAt: FieldValue.serverTimestamp(),
    updatedAt: FieldValue.serverTimestamp(),
  });
}

export async function listEntries(userId, limit, nextToken) {
  let query = entriesCollection(userId)
    .where("deletedAt", "==", null)
    .orderBy("createdAt", "desc")
    .limit(limit);

  if (nextToken) {
    const cursor = decodeNextToken(nextToken);
    query = query.startAfter(cursor);
  }

  const snap = await query.get();
  const items = snap.docs.map(mapEntry);
  const tail = snap.docs.length ? snap.docs[snap.docs.length - 1] : null;

  return {
    items,
    nextToken: tail ? encodeNextToken(tail.get("createdAt")) : null,
  };
}

export async function markAiQueued(userId, entryId) {
  const ref = entriesCollection(userId).doc(entryId);
  await getEntry(userId, entryId);

  await ref.update({
    aiStatus: "QUEUED",
    aiError: null,
    updatedAt: FieldValue.serverTimestamp(),
  });

  const snap = await ref.get();
  return mapEntry(snap);
}
