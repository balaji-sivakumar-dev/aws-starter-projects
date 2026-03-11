import crypto from "node:crypto";

import { CloudTasksClient } from "@google-cloud/tasks";

import { requireAuth } from "./auth.js";
import { ApiError, errorPayload, jsonResponse } from "./errors.js";
import {
  createEntry,
  getEntry,
  listEntries,
  markAiQueued,
  softDeleteEntry,
  updateEntry,
} from "./repository.js";

const tasksClient = new CloudTasksClient();

function requestId(req) {
  const header = req.header("x-request-id") || req.header("x-cloud-trace-context") || "";
  if (header) return String(header).split("/")[0];
  return crypto.randomUUID();
}

function normalizePath(path) {
  const value = String(path || "/");
  return value.endsWith("/") && value.length > 1 ? value.slice(0, -1) : value;
}

function parseLimit(raw) {
  if (raw === undefined) return 20;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > 100) {
    throw new ApiError(400, "VALIDATION_ERROR", "limit must be between 1 and 100");
  }
  return value;
}

function validateCreate(payload) {
  const title = String(payload?.title || "").trim();
  const body = String(payload?.body || "").trim();
  if (!title) throw new ApiError(400, "VALIDATION_ERROR", "title is required");
  if (!body) throw new ApiError(400, "VALIDATION_ERROR", "body is required");
  return { title, body };
}

function validateUpdate(payload) {
  const updates = {};

  if (Object.prototype.hasOwnProperty.call(payload, "title")) {
    const title = String(payload.title || "").trim();
    if (!title) throw new ApiError(400, "VALIDATION_ERROR", "title cannot be empty");
    updates.title = title;
  }

  if (Object.prototype.hasOwnProperty.call(payload, "body")) {
    const body = String(payload.body || "").trim();
    if (!body) throw new ApiError(400, "VALIDATION_ERROR", "body cannot be empty");
    updates.body = body;
  }

  if (!Object.keys(updates).length) {
    throw new ApiError(400, "VALIDATION_ERROR", "nothing to update");
  }

  return updates;
}

async function enqueueAiTask({ userId, entryId, requestId: rid }) {
  const projectId = process.env.GCLOUD_PROJECT || process.env.PROJECT_ID;
  const location = process.env.AI_QUEUE_LOCATION;
  const queue = process.env.AI_QUEUE_NAME;
  const targetUrl = process.env.AI_PROCESSOR_URL;

  if (!projectId || !location || !queue || !targetUrl) {
    throw new ApiError(500, "CONFIG_ERROR", "AI queue is not fully configured");
  }

  const parent = tasksClient.queuePath(projectId, location, queue);
  const payload = Buffer.from(
    JSON.stringify({ userId, entryId, requestId: rid }),
    "utf8"
  ).toString("base64");

  await tasksClient.createTask({
    parent,
    task: {
      httpRequest: {
        httpMethod: "POST",
        url: targetUrl,
        headers: {
          "Content-Type": "application/json",
        },
        body: payload,
      },
    },
  });
}

function splitEntryPath(path) {
  const parts = path.split("/").filter(Boolean);
  if (parts.length < 2 || parts[0] !== "entries") {
    return { entryId: null, ai: false };
  }

  return {
    entryId: parts[1],
    ai: parts.length === 3 && parts[2] === "ai",
  };
}

export async function handleRequest(req, res) {
  const rid = requestId(req);

  try {
    const method = req.method.toUpperCase();
    const path = normalizePath(req.path || req.url || "/");

    if (method === "GET" && path === "/health") {
      return res.status(200).json({ status: "ok", requestId: rid });
    }

    const auth = await requireAuth(req);

    if (method === "GET" && path === "/me") {
      return res.status(200).json({ userId: auth.userId, email: auth.email, requestId: rid });
    }

    if (method === "GET" && path === "/entries") {
      const limit = parseLimit(req.query.limit);
      const data = await listEntries(auth.userId, limit, req.query.nextToken);
      return res.status(200).json({ ...data, requestId: rid });
    }

    if (method === "POST" && path === "/entries") {
      const payload = validateCreate(req.body || {});
      const item = await createEntry(auth.userId, payload);
      return res.status(201).json({ item, requestId: rid });
    }

    const parts = splitEntryPath(path);
    if (!parts.entryId) {
      throw new ApiError(404, "NOT_FOUND", "route not found");
    }

    if (method === "GET" && !parts.ai) {
      const item = await getEntry(auth.userId, parts.entryId);
      return res.status(200).json({ item, requestId: rid });
    }

    if (method === "PUT" && !parts.ai) {
      const updates = validateUpdate(req.body || {});
      const item = await updateEntry(auth.userId, parts.entryId, updates);
      return res.status(200).json({ item, requestId: rid });
    }

    if (method === "DELETE" && !parts.ai) {
      await softDeleteEntry(auth.userId, parts.entryId);
      return res.status(200).json({ deleted: true, requestId: rid });
    }

    if (method === "POST" && parts.ai) {
      await markAiQueued(auth.userId, parts.entryId);
      await enqueueAiTask({ userId: auth.userId, entryId: parts.entryId, requestId: rid });
      return res.status(202).json({ entryId: parts.entryId, aiStatus: "QUEUED", requestId: rid });
    }

    throw new ApiError(404, "NOT_FOUND", "route not found");
  } catch (err) {
    const payload = errorPayload(err, rid);
    return res.status(payload.statusCode).json(payload.body);
  }
}
