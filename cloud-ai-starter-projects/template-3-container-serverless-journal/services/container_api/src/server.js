import crypto from "node:crypto";

import express from "express";
import { createRemoteJWKSet, jwtVerify } from "jose";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand, QueryCommand, UpdateCommand } from "@aws-sdk/lib-dynamodb";
import { SFNClient, StartExecutionCommand } from "@aws-sdk/client-sfn";

const app = express();
app.use(express.json({ limit: "256kb" }));

const TABLE_NAME = process.env.JOURNAL_TABLE_NAME;
const WORKFLOW_ARN = process.env.WORKFLOW_ARN;
const COGNITO_ISSUER = process.env.COGNITO_ISSUER;
const COGNITO_CLIENT_ID = process.env.COGNITO_CLIENT_ID;
const PORT = Number(process.env.PORT || 8080);

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const sfn = new SFNClient({});

const jwks = COGNITO_ISSUER ? createRemoteJWKSet(new URL(`${COGNITO_ISSUER}/.well-known/jwks.json`)) : null;

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function userPk(userId) {
  return `USER#${userId}`;
}

function entrySk(createdAt, entryId) {
  return `ENTRY#${createdAt}#${entryId}`;
}

function lookupSk(entryId) {
  return `ENTRYID#${entryId}`;
}

function requestId(req) {
  return req.header("x-request-id") || crypto.randomUUID();
}

function fail(res, status, code, message, rid) {
  return res.status(status).json({ code, message, requestId: rid });
}

function toEntry(item) {
  return {
    entryId: item.entryId,
    userId: item.userId,
    title: item.title,
    body: item.body,
    createdAt: item.createdAt,
    updatedAt: item.updatedAt,
    deletedAt: item.deletedAt || null,
    aiStatus: item.aiStatus || "NOT_REQUESTED",
    summary: item.summary || null,
    tags: item.tags || [],
    aiUpdatedAt: item.aiUpdatedAt || null,
    aiError: item.aiError || null,
  };
}

async function auth(req, res, next) {
  try {
    if (!jwks || !COGNITO_CLIENT_ID) {
      throw new Error("cognito verification not configured");
    }

    const header = String(req.header("authorization") || "");
    if (!header.startsWith("Bearer ")) {
      return fail(res, 401, "UNAUTHORIZED", "missing valid token", requestId(req));
    }

    const token = header.slice("Bearer ".length).trim();
    const verified = await jwtVerify(token, jwks, {
      issuer: COGNITO_ISSUER,
      audience: COGNITO_CLIENT_ID,
    });

    req.userId = verified.payload.sub;
    next();
  } catch {
    return fail(res, 401, "UNAUTHORIZED", "missing valid token", requestId(req));
  }
}

app.get("/health", (req, res) => {
  res.json({ status: "ok", requestId: requestId(req) });
});

app.get("/me", auth, (req, res) => {
  res.json({ userId: req.userId, requestId: requestId(req) });
});

app.get("/entries", auth, async (req, res) => {
  const rid = requestId(req);
  try {
    const limit = Math.max(1, Math.min(Number(req.query.limit || 20), 100));
    const result = await ddb.send(
      new QueryCommand({
        TableName: TABLE_NAME,
        KeyConditionExpression: "PK = :pk AND begins_with(SK, :sk)",
        ExpressionAttributeValues: {
          ":pk": userPk(req.userId),
          ":sk": "ENTRY#",
        },
        ScanIndexForward: false,
        Limit: limit,
      })
    );

    const items = (result.Items || []).filter((x) => !x.deletedAt).map(toEntry);
    res.json({ items, nextToken: null, requestId: rid });
  } catch {
    fail(res, 500, "INTERNAL_ERROR", "internal server error", rid);
  }
});

app.post("/entries", auth, async (req, res) => {
  const rid = requestId(req);
  try {
    const title = String(req.body?.title || "").trim();
    const body = String(req.body?.body || "").trim();
    if (!title) return fail(res, 400, "VALIDATION_ERROR", "title is required", rid);
    if (!body) return fail(res, 400, "VALIDATION_ERROR", "body is required", rid);

    const entryId = crypto.randomUUID();
    const ts = nowIso();
    const item = {
      PK: userPk(req.userId),
      SK: entrySk(ts, entryId),
      entityType: "JOURNAL_ENTRY",
      entryId,
      userId: req.userId,
      title,
      body,
      createdAt: ts,
      updatedAt: ts,
      aiStatus: "NOT_REQUESTED",
      tags: [],
    };

    await ddb.send(new PutCommand({ TableName: TABLE_NAME, Item: item }));
    await ddb.send(
      new PutCommand({
        TableName: TABLE_NAME,
        Item: {
          PK: userPk(req.userId),
          SK: lookupSk(entryId),
          entityType: "ENTRY_LOOKUP",
          entryId,
          entrySk: item.SK,
          createdAt: ts,
        },
      })
    );

    res.status(201).json({ item: toEntry(item), requestId: rid });
  } catch {
    fail(res, 500, "INTERNAL_ERROR", "internal server error", rid);
  }
});

async function resolveEntry(userId, entryId) {
  const lookup = await ddb.send(
    new GetCommand({ TableName: TABLE_NAME, Key: { PK: userPk(userId), SK: lookupSk(entryId) } })
  );
  if (!lookup.Item) return null;
  const item = await ddb.send(
    new GetCommand({ TableName: TABLE_NAME, Key: { PK: userPk(userId), SK: lookup.Item.entrySk } })
  );
  if (!item.Item || item.Item.deletedAt) return null;
  return item.Item;
}

app.get("/entries/:entryId", auth, async (req, res) => {
  const rid = requestId(req);
  try {
    const item = await resolveEntry(req.userId, req.params.entryId);
    if (!item) return fail(res, 404, "NOT_FOUND", "entry not found", rid);
    res.json({ item: toEntry(item), requestId: rid });
  } catch {
    fail(res, 500, "INTERNAL_ERROR", "internal server error", rid);
  }
});

app.put("/entries/:entryId", auth, async (req, res) => {
  const rid = requestId(req);
  try {
    const item = await resolveEntry(req.userId, req.params.entryId);
    if (!item) return fail(res, 404, "NOT_FOUND", "entry not found", rid);

    const title = req.body?.title;
    const body = req.body?.body;
    if (title !== undefined && !String(title).trim()) {
      return fail(res, 400, "VALIDATION_ERROR", "title cannot be empty", rid);
    }
    if (body !== undefined && !String(body).trim()) {
      return fail(res, 400, "VALIDATION_ERROR", "body cannot be empty", rid);
    }

    await ddb.send(
      new UpdateCommand({
        TableName: TABLE_NAME,
        Key: { PK: item.PK, SK: item.SK },
        UpdateExpression: "SET #updatedAt = :u, #title = if_not_exists(#title,:et), #body = if_not_exists(#body,:eb)",
        ExpressionAttributeNames: { "#updatedAt": "updatedAt", "#title": "title", "#body": "body" },
        ExpressionAttributeValues: {
          ":u": nowIso(),
          ":et": title !== undefined ? String(title).trim() : item.title,
          ":eb": body !== undefined ? String(body).trim() : item.body,
        },
      })
    );

    const updated = await resolveEntry(req.userId, req.params.entryId);
    res.json({ item: toEntry(updated), requestId: rid });
  } catch {
    fail(res, 500, "INTERNAL_ERROR", "internal server error", rid);
  }
});

app.delete("/entries/:entryId", auth, async (req, res) => {
  const rid = requestId(req);
  try {
    const item = await resolveEntry(req.userId, req.params.entryId);
    if (!item) return fail(res, 404, "NOT_FOUND", "entry not found", rid);

    await ddb.send(
      new UpdateCommand({
        TableName: TABLE_NAME,
        Key: { PK: item.PK, SK: item.SK },
        UpdateExpression: "SET deletedAt = :d, updatedAt = :u",
        ExpressionAttributeValues: { ":d": nowIso(), ":u": nowIso() },
      })
    );

    res.json({ deleted: true, requestId: rid });
  } catch {
    fail(res, 500, "INTERNAL_ERROR", "internal server error", rid);
  }
});

app.post("/entries/:entryId/ai", auth, async (req, res) => {
  const rid = requestId(req);
  try {
    const item = await resolveEntry(req.userId, req.params.entryId);
    if (!item) return fail(res, 404, "NOT_FOUND", "entry not found", rid);

    await ddb.send(
      new UpdateCommand({
        TableName: TABLE_NAME,
        Key: { PK: item.PK, SK: item.SK },
        UpdateExpression: "SET aiStatus = :s, aiError = :e, updatedAt = :u",
        ExpressionAttributeValues: { ":s": "QUEUED", ":e": null, ":u": nowIso() },
      })
    );

    const started = await sfn.send(
      new StartExecutionCommand({
        stateMachineArn: WORKFLOW_ARN,
        input: JSON.stringify({ userId: req.userId, entryId: req.params.entryId, requestId: rid }),
      })
    );

    res.status(202).json({ entryId: req.params.entryId, aiStatus: "QUEUED", executionArn: started.executionArn, requestId: rid });
  } catch {
    fail(res, 500, "INTERNAL_ERROR", "internal server error", rid);
  }
});

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`container api listening on ${PORT}`);
});
