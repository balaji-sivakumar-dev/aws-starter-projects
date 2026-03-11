import admin from "firebase-admin";

import { generateSummaryAndTags } from "./ai_gateway.js";

if (!admin.apps.length) {
  admin.initializeApp();
}

const db = admin.firestore();

function nowTs() {
  return admin.firestore.FieldValue.serverTimestamp();
}

function toInt(raw, fallback) {
  const value = Number(raw);
  return Number.isFinite(value) ? Math.floor(value) : fallback;
}

function shortError(err) {
  const text = String(err?.message || err || "unknown error");
  return text.slice(0, 180);
}

async function checkRateLimit(userId) {
  const maxRequests = toInt(process.env.AI_RATE_LIMIT_MAX_REQUESTS, 5);
  const windowSeconds = toInt(process.env.AI_RATE_LIMIT_WINDOW_SECONDS, 60);

  if (maxRequests <= 0 || windowSeconds <= 0) return;

  const epoch = Math.floor(Date.now() / 1000);
  const bucket = Math.floor(epoch / windowSeconds);
  const ref = db.collection("users").doc(userId).collection("meta").doc(`ai-rate-${bucket}`);

  await db.runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const count = Number(snap.get("count") || 0);
    if (count >= maxRequests) {
      throw new Error("rate limit exceeded");
    }

    tx.set(
      ref,
      {
        count: count + 1,
        expiresAtEpoch: epoch + windowSeconds * 2,
        updatedAt: nowTs(),
      },
      { merge: true }
    );
  });
}

export async function processEntryAi({ userId, entryId, requestId }) {
  if (!userId || !entryId || !requestId) {
    throw new Error("userId, entryId, requestId are required");
  }

  await checkRateLimit(userId);

  const ref = db.collection("users").doc(userId).collection("entries").doc(entryId);
  const snap = await ref.get();
  if (!snap.exists) throw new Error("entry not found");

  const data = snap.data() || {};
  if (data.deletedAt) throw new Error("entry not found");

  await ref.update({
    aiStatus: "PROCESSING",
    aiError: null,
    updatedAt: nowTs(),
  });

  try {
    const generated = await generateSummaryAndTags({
      title: data.title,
      body: data.body,
    });

    await ref.update({
      aiStatus: "COMPLETE",
      summary: generated.summary,
      tags: generated.tags,
      aiUpdatedAt: nowTs(),
      aiError: null,
      updatedAt: nowTs(),
    });

    return {
      ok: true,
      userId,
      entryId,
      requestId,
      aiStatus: "COMPLETE",
    };
  } catch (err) {
    await ref.update({
      aiStatus: "FAILED",
      aiError: shortError(err),
      updatedAt: nowTs(),
    });
    throw err;
  }
}

export async function handleProcessorHttp(req, res) {
  try {
    const { userId, entryId, requestId } = req.body || {};
    const result = await processEntryAi({ userId, entryId, requestId });
    return res.status(200).json(result);
  } catch (err) {
    return res.status(500).json({
      code: "PROCESSOR_ERROR",
      message: shortError(err),
      requestId: req.body?.requestId || "unknown-request-id",
    });
  }
}
