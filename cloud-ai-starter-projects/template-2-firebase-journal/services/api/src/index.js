import { onRequest } from "firebase-functions/v2/https";
import { setGlobalOptions } from "firebase-functions/v2";

import { initAdmin } from "./auth.js";
import { handleRequest } from "./routes.js";

initAdmin();

setGlobalOptions({
  region: process.env.FUNCTION_REGION || "us-central1",
  maxInstances: 20,
});

export const api = onRequest(async (req, res) => {
  res.set("Access-Control-Allow-Origin", "*");
  res.set("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Request-Id");
  res.set("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");

  if (req.method === "OPTIONS") {
    return res.status(204).send("");
  }

  return handleRequest(req, res);
});
