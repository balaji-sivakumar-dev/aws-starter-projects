export class ApiError extends Error {
  constructor(statusCode, code, message) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
  }
}

export function jsonResponse(statusCode, body) {
  return {
    statusCode,
    body,
  };
}

export function toHttp(res, payload) {
  res.status(payload.statusCode).json(payload.body);
}

export function errorPayload(err, requestId) {
  if (err instanceof ApiError) {
    return jsonResponse(err.statusCode, {
      code: err.code,
      message: err.message,
      requestId,
    });
  }

  return jsonResponse(500, {
    code: "INTERNAL_ERROR",
    message: "internal server error",
    requestId,
  });
}
